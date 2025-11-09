# 金融情报日报系统 · 技术设计文档（TDD · 阶段一｜MVP）

**版本**：v1.0  
**日期**：2025-11-05（Asia/Shanghai）  
**适用范围**：**阶段一**——打通“采集 → 处理（LLM）→ 成稿 → 邮件发送”的最小可用闭环；**模块完成即测试、测试通过再进入下一模块**。  
**参考文档**：PRD v1（已定稿）

---

## 1. 总体架构

### 1.1 目标环境

- **开发**：Windows WSL
  
- **生产**：腾讯云 Linux（2C/2G）
  
- **数据库**：PostgreSQL（阶段一用 Docker 单容器）
  
- **队列/调度**：Celery + Redis（06:00 定时）
  
- **后端**：FastAPI（阶段一仅健康检查/CLI；管理台在阶段二）
  

### 1.2 组件与职责

- **Ingestion（采集）**：RSS（优先）、静态 HTML、动态渲染（Playwright 兜底）
  
- **Processing（LLM 抽取）**：DeepSeek Chat 主；Qwen（Max/Plus）备；OpenRouter 适配位保留（禁用）
  
- **Composer（成稿）**：根据 PRD 模板生成 **邮件正文 HTML（TopN+阈值）** 与 **附件 HTML（全量）**
  
- **Mailer（投递）**：网易 SMTP（SSL 465）；To/BCC 分批；1封/秒；06:05-06:20 窗口
  
- **Persistence**：PostgreSQL 实体表（见 §4）
  
- **Orchestrator**：Celery 任务编排与重试
  
- **Sys 模块**：启动自检、健康检查、基础指标
  

### 1.3 端到端数据流（阶段一）

```
sources → crawl(RSS/Static/Dynamic) → parse/clean → dedup
      → articles + extraction_queue(queued)
      → extract_llm(DeepSeek→Qwen, 90s, retries=2)
      → extraction_items
      → compose_report(TopN+阈值；全量附件)
      → reports
      → send_email(SMTP; 分批/节流)
      → delivery_log
```

---

## 2. 模块设计（阶段一）

> 开发顺序与验收：**A 采集** → **B 抽取** → **C 成稿** → **D 邮件**。**每模块完成即测**，通过后进入下一模块。

### 2.1 模块 A：信息源获取（Ingestion）

**目标**：获取“过去 24h”内文章；清洗正文；去重；写入 `articles`；并写 `extraction_queue`。

**输入**

- `sources`：`type ∈ {rss, static, dynamic}`
  
- 时间窗口：过去 24h
  

**处理**

1. **RSS**：读取 feed → 解析项 → 去 HTML → 规范字段
   
2. **静态**：requests 获取 HTML → trafilatura 主抽取 → 回退 readability/XPath
   
3. **动态**：检测纯静态失败时，用 Playwright 渲染（超时 25s，滚动≤3）
   
4. **去重**：
   
    - 一级：`canonical_url` 或（标准化URL + 标题 + 发布时间近似）
      
    - 二级：SimHash 近重复（汉明距离 ≤3，可配）
    
5. **落库**：写 `articles`；写 `extraction_queue(status=queued)`
   

**输出**

- `articles` 新增记录
  
- `extraction_queue` 入队记录
  
- 采集日志计数（成功/失败/重试）
  

**关键接口（设计约定）**

- `fetch_rss(feed_url:str, since:datetime) -> list[Item]`
  
- `fetch_html(url:str, timeout:int) -> str`
  
- `fetch_rendered_html(url:str, timeout:int, scrolls:int=3) -> str`
  
- `extract_main_text(html:str, url:str) -> str`（trafilatura→readability 回退）
  
- `compute_simhash(text:str) -> int` / `is_near_dup(a:int,b:int,th:int=3)->bool`
  

**并发**

- 开发（WSL）：RSS 可高并发（默认=10）
  
- 生产（2C/2G）：整体并发≈2（通过配置下调）
  

**错误与重试**

- HTTP/解析错误：重试 3 次（指数退避）
  
- 动态渲染失败：降级为静态或丢弃并告警（日志）
  

**完成判定（验收）**

- 写入 `articles ≥ 10`（样本日）
  
- `extraction_queue` 入队与去重规则生效
  
- 失败不阻塞其它源；日志可见
  

---

### 2.2 模块 B：信息处理（LLM 抽取）— 补充与修订

## B.0 目标与约束（新增）

- **长文适配**：对超长文章进行**分段+重叠**；尽量减少分段次数，降低调用成本与合并复杂度。
  
- **条件并行**：**仅当**允许并发同时处理多篇文章时启用（受配置与 Provider 速率/资源约束）；**否则保持串行**。生产（2C/2G）默认关闭并行。
  

---

## B.1 分段与重叠策略（细化）

### B.1.1 预算与上限

- `MODEL_INPUT_LIMIT_TOKENS`：每 Provider/模型的**输入上限**（配置提供，不做硬编码）。
  
- `LLM_CHUNK_BUDGET=0.7`：**单段 token 预算占比**（默认 70% 上限，留余量给系统/提示词）。
  
- `LLM_CHUNK_OVERLAP_CHARS=200`：**字符重叠**（默认 200 中文字符）。
  
- `LLM_MAX_CHUNKS_PER_ARTICLE=8`：**单文分段上限**（超出触发降级策略，见下）。
  

> 令 `target_tokens = floor(MODEL_INPUT_LIMIT_TOKENS * LLM_CHUNK_BUDGET)`。

### B.1.2 Token 估算

- 首选：可插拔 **tokenizer 估算器**（优先使用与模型兼容的 tokenizer；不可用时退化为**字符基准估算**）。
  
- 退化估算（近似）：
  
    - 中文文本：`tokens ≈ ceil(char_len * 1.0)`
      
    - 混合文本：`tokens ≈ ceil(char_len * 1.2)`
    
- 估算器接口：
  

`def estimate_tokens(text: str, lang_hint: str | None = "zh") -> int: ...`

### B.1.3 语义打包切分

- 先按**段落**（空行/换段符）划分，再按**句子**（`。！？!?` 与英文句号/分号）微切。
  
- 使用 **“句子装箱”** 逼近 `target_tokens`：逐句累加，超过阈值则回退上一个句子作为段落边界。
  
- 段与段之间追加 `LLM_CHUNK_OVERLAP_CHARS` 的**尾段重叠**。
  
- 伪代码：
  

`chunks = [] buf = [] for sent in sentences:   if tokens(buf + [sent]) <= target_tokens: buf += [sent]   else:     chunks += [concat(buf)]     buf = tail(buf, overlap_by_chars) + [sent] if buf: chunks += [concat(buf)]`

### B.1.4 过长降级（防止分段爆炸）

- 若 `len(chunks) > LLM_MAX_CHUNKS_PER_ARTICLE`：启用**降级**
  
    1. **粗提要路径**：先对全文做一次“重点提要”（提取关键段/核心事实），再按提要分段继续抽取；
       
    2. **硬降级路径**：仅对**前 N 段**（N=`LLM_MAX_CHUNKS_PER_ARTICLE`）抽取 + 对全文做 1 次“总括事实/观点”补充，标注 `processing_status=partial` 与 `truncate_reason=excess_chunks`。
    
- 降级选择由 `LLM_LONGFORM_STRATEGY ∈ {summary_then_extract, headN_plus_overall}`（默认：`summary_then_extract`）控制。
  

---

## B.2 抽取调用与合并

### B.2.1 调用顺序与回退

- 每段调用：**DeepSeek Chat** → 失败/超时（90s、重试 2 次）→ **Qwen（Max/Plus）**。
  
- 统一中文展示：非中文即翻译为中文输出（保留原文片段字段供溯源）。
  
- 每段输出 **严格 JSON**（Schema 同原 TDD）。
  

### B.2.2 合并与去重

- 合并所有段落的 `items`：
  
    - **事实归一化**：去空白、半角/全角统一、标点清洗、数字标准化（中文数字→阿拉伯）
      
    - **近似去重**：对 `fact` 文本做 SimHash 或简单**编辑距离 ≤2** 去重，保留**置信度更高**的条目；
      
    - `region/layer` 冲突：以**频次多数**为先，置信度为次；打分相等取首个出现。
    
- 产出**文章级 items** 与 `processing_status ∈ {ok, partial, failed}`。
  

---

## B.3 条件并行（多篇文章同时处理）

> **前提**：Provider 与环境允许一定并发；否则保持串行。

### B.3.1 配置开关（新增）

- `LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING`：默认 **false**（生产关闭；开发可开）。
  
- `LLM_MAX_PARALLEL_ARTICLES`：并行处理的**最大文章数**（开发建议 2–4；生产 ≤2）。
  
- `LLM_MAX_INFLIGHT_CALLS`：**单 Provider**最大**并发中的调用**数（避免 429），默认 2。
  

### B.3.2 实现路径

- **Celery 组任务**（推荐）：
  
    - 将待处理文章按 `LLM_MAX_PARALLEL_ARTICLES` 切片，使用 **group/chord** 并发派发 `extract_article_task(article_id)`；
      
    - 由 **Provider 适配层**控制每 Provider 的**并发阀**（信号量/令牌桶），确保`≤ LLM_MAX_INFLIGHT_CALLS`；
      
    - 若 `LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING=false`，则串行提交 group（单次一个）。
    
- **单进程 async gather**（可选）：
  
    - 若 Provider 客户端支持 asyncio，亦可在单任务内使用 `asyncio.Semaphore(LLM_MAX_INFLIGHT_CALLS)` 并发段内/文间调用。
      
    - 资源紧张（2C/2G）时**禁用**此路径，仅走 Celery 任务并发。
      

> **不支持**或**限制严格**的 Provider：将 `LLM_MAX_INFLIGHT_CALLS=1`，等同串行。

### B.3.3 回退与保护

- 出现 429/速率错误：记录 Provider 速率异常，触发**指数冷却**并自动将并发阀减半（最小=1）。
  
- 连续失败达到阈值：关闭并行开关（进程级 fall-back），切回串行并打告警日志。
  

---

## B.4 接口与伪代码（补充）

`# nlp/chunking.py def plan_chunks(text: str, lang_hint: str, model_input_limit: int,                 budget: float = 0.7, overlap_chars: int = 200,                 max_chunks: int = 8, strategy: str = "summary_then_extract") -> list[str] | ChunkPlan:     """     返回分段文本列表或包含降级策略说明的 ChunkPlan。     """  # nlp/extractor.py def extract_article(article_id: int, provider_router: ProviderRouter) -> ExtractResult:     """     读取文章→分段→逐段调用→合并去重→写 extraction_items→返回结果（ok/partial/failed）。     """  # tasks/extract_tasks.py def run_extraction(parallel_articles: int | None = None) -> None:     """     若 LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING: group/chord 并发派发；     否则按队列顺序逐篇处理。     """`

---

## B.5 配置项（新增/调整）

`# 分段 LLM_CHUNK_BUDGET=0.7 LLM_CHUNK_OVERLAP_CHARS=200 LLM_MAX_CHUNKS_PER_ARTICLE=8 LLM_LONGFORM_STRATEGY=summary_then_extract   # 或 headN_plus_overall  # 条件并行 LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING=false  # 生产默认 false LLM_MAX_PARALLEL_ARTICLES=2                  # 开发期可 2–4 LLM_MAX_INFLIGHT_CALLS=2                     # 每 Provider 并发阀`

> **生产建议**：保持 `LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING=false`；仅在 WSL 调试或资源充足时打开。

---

## B.6 日志、监控与错误处理（扩充）

- **分段统计**：`{article_id, chunks, used_strategy, truncated, est_tokens}`
  
- **Provider 并发**：记录 `inflight_calls`、429 次数、回退动作（阀值调整/冷却时长）
  
- **段级失败**：保留 `chunk_index`、失败类型（超时/429/5xx/解析），允许**跳过个别段**并继续其他段
  
- **文章级状态**：`processing_status`、`truncate_reason`（如 `excess_chunks`）、`fallback_provider`
  
- **指标**：提取平均用时、段均 tokens、失败率（总体/Provider）
  

---

## B.7 测试与验收（补充）

### 单元测试

1. **长文分段**：给定 10k 中文字符文本→`plan_chunks` 生成 ≤8 段；相邻段重叠≈200 字；不跨句截断。
   
2. **降级策略**：设置 `LLM_MAX_CHUNKS_PER_ARTICLE=2` → 触发 `summary_then_extract`；返回 `used_strategy=summary_then_extract`。
   
3. **去重合并**：两段输出事实近似（编辑距≤2）→合并保高置信版本。
   

### 集成测试（Mock Provider）

1. **串行路径**：`LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING=false` → 10 篇文章按队列逐篇处理；断言入库与顺序。
   
2. **并行路径**：开启并发（`true`，`LLM_MAX_PARALLEL_ARTICLES=3`、`LLM_MAX_INFLIGHT_CALLS=2`）→模拟 429 → 观察并发阀减半与冷却回退，最终全部完成（部分 `partial` 可接受）。
   

### 冒烟（WSL）

`# 串行 python -m src.cli.run_once --step extract  # 条件并行（仅开发） export LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING=true export LLM_MAX_PARALLEL_ARTICLES=3 python -m src.cli.run_once --step extract`

### 验收（模块 B Done · 修订口径）

- **长文**均能被分段+重叠处理；**过长**触发降级且状态标注清晰；
  
- 串行模式稳定通过；并行模式在开发机可开启并**可被自动限速回退**（出现 429/失败时）；
  
- 总体 `extraction_items ≥ 20`，Schema 全通过。
  


---

### 2.3 模块 C：报告生成（Composer）

**目标**：按 PRD 模板生成**邮件正文 HTML**（TopN & 阈值）与**附件 HTML**（全量，含原文链接），写入 `reports`。

**输入**

- 当日 `extraction_items`
  
- 系统参数：`REPORT_TOPN=5`、`CONFIDENCE_THRESHOLD=0.6`、`MIN_CONTENT_LEN=120`
  

**处理**

1. 过滤：仅正文部分应用阈值（`confidence≥0.6`，内容≥120字）
   
2. 分区：国内/国外 ×（政治/经济/金融大模型技术/金融科技）
   
3. 排序：`score = 0.5*影响力 + 0.3*新近度 + 0.2*来源权威`
   
4. 渲染：
   
    - **邮件正文 HTML**：分区卡片，TopN
      
    - **附件 HTML**：全量 facts/opinions（evidence 不显示），原文链接可点击
    
5. 落库：`reports(html_body, html_attachment, sections_json, build_meta)`
   

**输出**

- `reports`（当天 1 条）
  

**完成判定（验收）**

- `reports` 成功写入；正文含目录锚点与 TopN；附件为全量且链接可用
  

---

### 2.4 模块 D：邮件发送（Mailer）

**目标**：通过网易 SMTP 发送当日报告；分批/节流；写 `delivery_log`。

**输入**

- `reports`（当日）
  
- 收件人：`report_recipients(type='recipient' AND enabled)`；白名单 `type='whitelist'` 不参与投递
  

**处理**

1. 组装主题：`金融情报日报 - YYYY-MM-DD`（可加“[测试]”前缀开关）
   
2. 正文：使用 C 的 **邮件正文 HTML**
   
3. 附件：HTML 文件 `daily-report-YYYY-MM-DD.html`
   
4. 分批与节流：最多 **50**/封，**1封/秒**
   
5. 窗口：**06:05–06:20** 完成
   
6. 错误与重试：失败重试 **2**；硬退信（用户不存在）加入黑名单；写 `delivery_log`
   

**输出**

- `delivery_log` 批次记录与状态
  

**完成判定（验收）**

- 至少 1 封真实邮件投递成功；`delivery_log` 记录完整
  

---

## 3. 任务编排（Celery · 阶段一）

- **Beat 计划**（Asia/Shanghai）
  
    - 06:00　`crawl_rss`（并发=配置）、`crawl_static`、必要时 `crawl_dynamic`
      
    - 06:05　`run_extraction`
      
    - 06:10　`build_report`
      
    - 06:12　`send_report_for_date`（窗口内完成）
    
- **任务重试**
  
    - 采集：3 次（指数退避）
      
    - LLM：2 次（90s 超时）
      
    - 邮件：2 次
    
- **CLI 冒烟**
  
    - `run_once --step {crawl|extract|compose|send|all}`
      

---

## 4. 数据模型（阶段一实现口径）

> 概要字段（类型与索引在实现中细化）；枚举见 PRD。

- **sources**：`id, name, type{rss,static,dynamic}, url, enabled, concurrency, timeout_sec, parser, region_hint{国内/国外/未知}, created_at, updated_at`
  
- **articles**：`id, source_id, title, url(unique), published_at, fetched_at, content_text, section, region_tag{国内/国外/未知}, lang, simhash, canonical_url, dedup_key, processing_status{raw,queued,done,failed}`
  
- **extraction_queue**：`id, article_id, provider_hint, priority, attempts, status{queued,running,done,failed}, last_error, created_at, updated_at`
  
- **extraction_items**：`id, article_id, fact, opinion(null), region{国内,国外,未知}, layer{政治,经济,金融大模型技术,金融科技,未知}, evidence_span, confidence, created_at`
  
- **reports**：`id, report_date, version, overview_summary, sections_json, html_body, html_attachment, build_meta, build_ms, created_at`
  
- **report_recipients**：`id, email, display_name, type{whitelist,recipient}, enabled, created_at, updated_at`
  
- **delivery_log**：`id, report_id, batch_no, recipients_snapshot, message_id, status{ok,failed,partial}, error_code, error_message, sent_at, duration_ms`
  

---

## 5. 配置项（阶段一 · 环境变量）

- 核心：`DATABASE_URL`, `REDIS_URL`, `TZ=Asia/Shanghai`
  
- 采集：`CRAWL_CONCURRENCY_RSS=10`（Dev 高 / Prod=2）, `CRAWL_CONCURRENCY_WEB=2`
  
- LLM：`PROVIDER_DEEPSEEK_*`, `PROVIDER_QWEN_*`, `LLM_TIMEOUT_SEC=90`, `LLM_RETRIES=2`
  
- 报告：`REPORT_TOPN=5`, `CONFIDENCE_THRESHOLD=0.6`, `MIN_CONTENT_LEN=120`
  
- 邮件：`SMTP_HOST=smtp.163.com`, `SMTP_PORT=465`, `SMTP_USER`, `SMTP_PASS`, `MAIL_BATCH_LIMIT=50`, `MAIL_RATE_LIMIT_PER_SEC=1`, `MAIL_WINDOW_START=06:05`, `MAIL_WINDOW_END=06:20`
  

---

## 6. 错误处理与可观测性

- **分类**：采集（网络/结构/渲染）、LLM（超时/429/解析）、成稿（模板/缺数据）、邮件（鉴权/网关/退信）
  
- **日志**：结构化行日志（含 trace_id、source_id、article_id、task、latency、retries、error）
  
- **队列状态**：`extraction_queue.status` + `attempts`
  
- **健康检查**：`/healthz`（DB/Redis/Provider 连通）
  
- **统计**：按 Provider/模型/日期聚合 token/费用（阶段一可留空实现，仅埋点）
  

---

## 7. 测试策略（**模块完成即测**）

### 7.1 单元测试

- 采集：正文抽取正确性（长度阈值/噪声比）、去重（SimHash≤3）
  
- 抽取：分块策略（尽量少块）、JSON Schema 校验
  
- 成稿：模板渲染 snapshot 比对（锚点、TopN、链接）
  
- 邮件：分批与节流逻辑
  

### 7.2 集成测试

- 伪造 RSS/HTML 样本；模拟 Provider（返回固定 JSON）；本地 SMTP（MailHog）收信验证
  

### 7.3 冒烟与验收

- CLI：`run_once --step crawl|extract|compose|send|all`
  
- **验收门槛**（样本日）：
  
    - A：`articles ≥ 10`，队列入库与去重有效
      
    - B：`extraction_items ≥ 20`，回退记录清晰
      
    - C：`reports = 1`，正文 TopN+附件全量
      
    - D：至少 1 封真实发信成功；`delivery_log` 完整
      

---

## 8. 性能与容量（阶段一）

- **生产并发**：总并发≈2（2C/2G），优先异步 IO，避免 LLM 侧过度并行
  
- **时效目标**：06:00 启动 → **06:20 前**完成发送
  
- **附件体量**：1–3 MB/日（HTML）
  
- **保留**：阶段一定义即可（分区与长期策略到阶段二/三完善）
  

---

## 9. 安全与合规（阶段一）

- **管理员固定密码**：`xtyydsf / xtyydsf`（按 PRD；外网部署建议内控访问）
  
- **数据来源**：仅公开网页/RSS；robots 可开关（默认关）
  
- **邮件**：授权码登录；不内嵌图片（降低拦截率）
  
- **可审计**：任务日志、delivery_log、失败样本保留
  

---

## 10. 里程碑与退出标准（阶段一）

- **M1 模块 A 通过**：采集/去重/入队完成
  
- **M2 模块 B 通过**：结构化抽取完成（≥20 条）
  
- **M3 模块 C 通过**：当日报告写入 `reports`，正文+附件就绪
  
- **M4 模块 D 通过**：真实投递成功，`delivery_log` 记录完整
  
- **阶段一完成**：`run_once --step all` 在 WSL 一次跑通；采集→处理→成稿→邮件闭环；06:20 前可完成
  

---

> 本 TDD 针对**阶段一**（MVP）实现提供可执行的技术约束与测试口径；阶段二（管理台/词云/统计）与阶段三（容器化）将在后续 TDD 增量文档中扩展。
