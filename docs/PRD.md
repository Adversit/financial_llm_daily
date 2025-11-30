# 金融情报日报系统 · PRD（v4）

**日期**：2025-11-05  
**时区**：Asia/Shanghai（统一内容时间归一；调度亦使用该时区）  
**目标环境**：开发期 WSL（Windows 上的 WSL）；生产期腾讯云 Linux（2C/2G）  
**数据库/缓存**：PostgreSQL（Docker 启动）、Redis（调度/队列）  
**后端/前端**：FastAPI（异步）+ Jinja2 SSR（阶段二实现）  
**容器化**：阶段三 docker-compose

---

## 1. 背景与目标

- 面向管理者和业务团队，**每天 06:00** 自动完成“采集→处理→成稿→邮件投递”的闭环，产出**国内/国外 ×（政治/经济/金融大模型技术/金融科技）**结构化日报。
    
- 确保**事实可追溯、观点可分离**；正文精选、附件全量；点击可直达信息源。
    
- 成本与性能在资源受限（2C/2G）环境下可控；后续具备平滑演进前端、RAG/DeepSearch 与容器化的能力。
    

---

## 2. 范围（Scope）

### 2.1 包含

- **信息源采集**：
    
    - RSS（微信公众号，首批示例：新智元、BigQuant；后续 ≥30 个）。
        
    - 网站采集：**静态（requests/Scrapy）优先**，检测到强依赖 JS 时自动回退 **Playwright** 动态渲染。
        
- **信息处理（LLM）**：DeepSeek Chat 为主，Qwen（Max/Plus）为备；保留 OpenRouter 适配位。
    
- **抽取与打标**：对每篇文章抽取**客观事实（必选）**与**观点（可选）**，并判定 `region{国内/国外}` 与 `layer{政治/经济/金融大模型技术/金融科技}`。
    
- **日报成稿**：
    
    - **邮件正文 HTML**：模板化分区卡片，TopN（默认 5），阈值筛选。
        
    - **HTML 附件**：**全量事实与观点**，每条含**原文链接**。
        
- **邮件投递（网易邮箱）**：支持多收件人分批发送、失败重试与发送日志。
    
- **前端管理台（阶段二）**：登录（白名单+邮箱验证码）、管理员能力、报告浏览与下载、词云（日/周/月）、定制化提示词。
    
- **容器化（阶段三）**：docker-compose 一键部署。
    
- **sys 模块**：启动自检、健康检查、配置一致性与队列水位可视化。
    

### 2.2 不包含（首版）

- 采集**需登录/付费墙**内容（待合规评估）。
    
- 外部 IM 告警（首版仅管理台查看）。
    
- SPF/DKIM/DMARC 落地（可后续补充文档）。
    
- 主题聚类与多源合并（**暂不启用**）。
    

---

## 3. 角色与权限

- **管理员（admin）**：默认账号/密码：`xtyydsf / xtyydsf`（邮箱同样支持 `xtyydsf@system.local`，**不强制首次改密**）。
    
    - 能力：增删收件人、增删白名单邮箱、启停信息源（含并发/超时）、系统参数设置、查看操作审计、查看系统状态。
        
- **普通用户（user）**：邮箱白名单 + 邮箱验证码登录；可浏览/下载报告、设置当日全局/单篇提示词与个人偏好模板（≤5）。
    

---

## 4. 关键需求（Functional Requirements）

### FR-1 信息源采集

- **RSS**：示例
    
    - 新智元：`http://101.42.187.241:8001/feed/MP_WXS_3271041950.rss`
        
    - BigQuant：`http://101.42.187.241:8001/feed/MP_WXS_3282383876.rss`
        
    - 并发：**10**（可配置；保留通用模板并发=2）。后续 RSS 源拓展至 **≥30**。
        
- **网站**：OpenAI/Google/Anthropic/xAI/NVIDIA/Microsoft/Finextra/Savanta/IDC 等。
    
    - **静态优先**, 动态（Playwright）兜底。
        
- **抓取范围**：**仅过去 24 小时**。
    
- **调度时间**：每日 **06:00**；当日失败自动补抓 2 轮（退避）。
    
- **robots.txt**：可开关（默认关）；公开页面优先；随机 UA、指数退避、最多重试 3 次；代理池可开关（默认关）。
    
- **正文抽取**：RSS 去 HTML 保留纯文本；网站优先通用正文抽取，必要时回退 XPath/CSS。
    
- **去重**：
    
    - 一级：`canonical URL`；缺失则（标准化 URL + 标题 + 发布时间近似）。
        
    - 二级：**SimHash** 近重复（可选 MinHash+LSH 扩展）。
        
    - 保留策略：保留发布时间更早或来源更权威者。
        
- **落库**：`sources / articles / extraction_queue`（`snapshots` 默认关闭，可后续开）。
    

### FR-2 信息处理（LLM 抽取）

- **Provider 优先级**：DeepSeek Chat → Qwen（Max/Plus）；OpenRouter 适配位保留。
    
- **分块策略**：估算可用输入上限的 **70%** 为单块上限，**尽量少块**；块间重叠约 200 字；只做一轮合并总结合。
    
- **统一中文展示**：**开启**（非中文来源翻译为中文用于展示；保留原文片段字段用于溯源）。
    
- **超时/重试/回退**：**90s** 超时，重试 2 次，失败回退至下一个 Provider；文章级 `processing_status ∈ {ok, partial, failed}`。
    
- **抽取结构（入库 `extraction_items`）**：
    
    ```json
    {
      "article_id": "...",
      "items": [
        {
          "fact": "…",                   // 必选
          "opinion": "…(可为空)",        // 信息源观点
          "region": "国内|国外|未知",
          "layer": "政治|经济|金融大模型技术|金融科技|未知",
          "evidence_span": "原文句段/段落索引",
          "confidence": 0.0
        }
      ]
    }
    ```
    
- **上限功能**：保留但默认**关闭**（如事实≤8、观点≤5 可在后台开启）。
    

### FR-3 日报成稿（正文 + 附件）

- **正文 HTML（邮件体）**：
    
    - 结构：抬头（项目名+日期）→ 总览摘要（150–250字）→ 目录锚点 → 分区卡片。
        
    - 分区：**国内/国外 ×（政治/经济/金融大模型技术/金融科技）**。
        
    - 每区 TopN = **5**（可配置）；卡片含：标题（原文链接）、1–2 句干货摘要、标签（region/layer）、来源名+发布时间。
        
    - **筛选阈值**：`confidence ≥ 0.6` + 去水限（正文 < 120 字或抽取失败剔除）。
        
    - 排序：综合分 `score = 0.5*影响力 + 0.3*新近度 + 0.2*来源权威`（后台可调权重）。
        
- **HTML 附件**：`daily-report-YYYY-MM-DD.html`
    
    - **全量**事实与观点（不做主题合并）；每条含**原文链接**；按来源/时间排序；不内嵌图片。
        

### FR-4 邮件投递（网易）

- **SMTP**：SSL `smtp.163.com:465`；授权码登录；UTF-8。
    
- **收件策略**：`To`=核心名单，`BCC`=扩展名单；单封最多 50 人，自动分批。
    
- **窗口与节流**：**06:05–06:20** 完成；**1 封/秒**节流。
    
- **失败与退信**：失败重试 2 次；硬退信（用户不存在）自动入黑名单；全部写入 `delivery_log`；支持“发送测试”和“重新投递”。
    
- **主题**：`金融情报日报 - YYYY-MM-DD`（支持“[测试]”前缀开关）。
    
- **退订**：页尾提示“如需退订请联系管理员邮箱”。
    

### FR-5 前端（阶段二）

- **登录与角色**：白名单 + 邮箱验证码；`admin/user`；JWT（HttpOnly, SameSite=Lax, 7 天）。
    
- **管理员**：收件人与白名单管理、启停信息源（并发/超时）、系统参数设置（TopN、阈值、分块、并发、预算、主题色等）、操作审计、系统状态面板。
    
- **用户**：报告浏览与下载、关键词/标签检索、词云（日/周/月）与基础统计、单篇与当日全局提示词、个人偏好模板（≤5）。
    
- **部门内功能**：关注清单置顶、禁止词/来源黑名单、一键导出选区为 Markdown、运营备注。
    
- **美化**：深浅双主题，品牌色可配（默认蓝）。
    
- **安全**：首版**不启用**接口限流与 CSRF（可后续开启）。
    

### FR-6 容器化（阶段三）

- `web(FastAPI)`、`worker(Celery)`、`beat(Celery Beat)`、`redis`、`postgres(可外部)`；
    
- `.env` 注入机密；`/var/data/reports` 卷（附件备份，可选）；健康检查 `/healthz` 与队列深度。
    

### FR-7 sys 模块与可观测性

- 启动自检：依赖/DB/Redis/Provider 鉴权/DDL 校验；
    
- 运行心跳：`/healthz`；队列水位、错误率/超时、平均处理时延面板；
    
- 配置一致性：关键参数哈希校验与一键导出；
    
- Token/费用统计：按 Provider/模型/日期聚合（`provider_usage`）。
    

---

## 5. 数据模型（PRD 级）

> 用于需求落地与 TDD 生成，非最终 SQL。

- **`sources`**：`id, name, type{rss,static,dynamic}, url, enabled, concurrency, timeout_sec, parser, region_hint{国内/国外/未知}, created_at, updated_at`
    
- **`articles`**：`id, source_id, title, url(unique), published_at, fetched_at, content_text, section, region_tag{国内/国外/未知}, lang, simhash, canonical_url, dedup_key, processing_status{raw,queued,done,failed}`
    
- **`snapshots`**（默认关闭）：`id, article_id, html_blob, screenshot_url, headers_json, created_at`
    
- **`extraction_queue`**：`id, article_id, provider_hint, priority, attempts, status{queued,running,done,failed}, last_error, created_at, updated_at`
    
- **`extraction_items`**：`id, article_id, fact, opinion(nullable), region{国内,国外,未知}, layer{政治,经济,金融大模型技术,金融科技,未知}, evidence_span, confidence, created_at`
    
- **`reports`**：`id, report_date, version, overview_summary, sections_json, html_body, html_attachment, build_meta, build_ms, created_at`
    
- **`report_recipients`**：`id, email, display_name, type{whitelist,recipient}, enabled, created_at, updated_at`
    
- **`delivery_log`**：`id, report_id, batch_no, recipients_snapshot, message_id, status{ok,failed,partial}, error_code, error_message, sent_at, duration_ms`
    
- **`users`**：`id, email, role{admin,user}, is_active, otp_last_sent_at, created_at, updated_at`
    
- **`system_settings`**：`id, key, value_json, updated_at`
    
- **`provider_usage`**：`id, provider, model, date, prompt_tokens, completion_tokens, total_cost, currency`
    
- **`admin_audit_log`**：`id, admin_email, action, before_json, after_json, created_at`
    

**保留期**：`articles/extraction_items ≥180 天`；`delivery_log/provider_usage ≥365 天`。  
**分区**：建议按月分区。  
**枚举**：`region/layer` 使用 Postgres enum，并预留 `未知`。

---

## 6. 任务编排与并发

- **队列/调度**：Celery + Redis（Beat 定时 06:00）；CLI 支持手动 `run_once`。
    
- **核心任务**：`crawl_rss` → `crawl_static/dynamic` → `extract_llm` → `compose_report` → `send_report` → `stats_rollup`。
    
- **并发策略**：
    
    - **开发期（WSL）**：并发可调高用于压测。
        
    - **生产期（2C/2G）**：整体并发上限约 **2**；优先异步 IO；避免模型侧过度并行。
        
- **时效目标**：**06:20 前**完成邮件发送（窗口 06:05–06:20）。
    

---

## 7. 配置与环境（关键变量）

- `DATABASE_URL`（PostgreSQL；阶段一由 Docker 单容器提供）
    
- `REDIS_URL`
    
- `SMTP_HOST/PORT/USER/PASS`（网易授权码）
    
- `TZ=Asia/Shanghai`
    
- `PROVIDER_DEEPSEEK_{BASE_URL,API_KEY,MODEL}`
    
- `PROVIDER_QWEN_{BASE_URL,API_KEY,MODEL}`
    
- `CRAWL_CONCURRENCY_RSS`（Dev 高、Prod 2）
    
- `CRAWL_CONCURRENCY_WEB`（默认 2）
    
- `LLM_TIMEOUT_SEC=90`、`LLM_RETRIES=2`
    
- `REPORT_TOPN=5`、`CONFIDENCE_THRESHOLD=0.6`、`MIN_CONTENT_LEN=120`
    
- `MAIL_BATCH_LIMIT=50`、`MAIL_RATE_LIMIT=1/sec`、`MAIL_WINDOW="06:05-06:20"`
    

---

## 8. 非功能性与指标（NFR）

- **稳定性**：06:00 例行任务失败率 < 5%，可在当日补抓成功。
    
- **性能**：2C/2G 环境下，日均 30–80 篇文章场景满足窗口内完成。
    
- **可观测性**：关键指标（队列水位、错误率、平均处理时延、token/费用）可视。
    
- **成本**：实时统计 token 并按 Provider 单价估算费用；支持日/周/月报表。
    
- **安全**：JWT（HttpOnly）；管理员固定密码由你方自控（**见风险**）。
    
- **合规**：仅采集公开信息；robots 可开关（默认关）。
    

---

## 9. 分阶段计划与验收

### 阶段一：**最小 MVP（采集→处理→成稿→邮件）**

- **交付**：
    
    - 打通 RSS（2 源起步，可扩）与 2–3 个代表性网站（静态优先、动态兜底）。
        
    - LLM 抽取入库 `extraction_items`；分块/回退与 90s 超时生效。
        
    - 生成**邮件正文 HTML**（阈值筛选）与**附件 HTML**（全量）；发送日志可见。
        
    - Postgres/Redis 运行；06:00 定时与 CLI 均可触发。
        
- **验收**：
    
    - 当日 **06:20 前**收件箱收到报告（正文+附件）。
        
    - `articles ≥ 10`、`extraction_items ≥ 20`、`reports = 1`、`delivery_log ≥ 1`。
        
    - 失败可在界面或日志定位并复跑。
        

### 阶段二：**前端管理台与可视化**

- 登录/白名单/验证码；管理员能力、系统参数设置、操作审计；
    
- 报告浏览/下载、检索；词云（日/周/月）与基础统计、PNG 下载；
    
- 用户提示词定制与偏好模板。
    
- **验收**：管理员新增/停用源与收件人后生效；用户可浏览/下载任意日报；词云与审计正常。
    

### 阶段三：**容器化**

- `web/worker/beat/redis/postgres` compose；`.env` 注入与健康检查；一键启动可达阶段一能力。
    
- **验收**：`docker compose up -d` 后 06:00 正常跑完并发信。
    

---

## 10. 风险与对策

- **固定管理员密码（xtyydsf/xtyydsf）**：存在安全风险。
    
    - _对策_：在外网部署时建议更改；或仅内网可达；同时限制登录 IP。
        
- **2C/2G 资源受限**：并发受限、模型调用超时概率提升。
    
    - _对策_：严格控制并发（Prod=2）、采用少分块策略、必要时降低 TopN 或仅摘要模式。
        
- **源站策略变化/反爬**：页面结构/速率限制变更导致抓取失败。
    
    - _对策_：日志与失败面板可视；保留 XPath 定制兜底；支持代理池开关。
        
- **成本波动**：高当日量导致 token/费用上升。
    
    - _对策_：面板展示与预算阈值（可后续开启降级策略）。
        

---

## 11. 验收清单（一次性）

1. 06:00 任务自动触发，**06:20 前**完成并发信；
    
2. 邮件**正文**符合模板、含 TopN 与锚点；**附件**为全量事实与观点，原文链接可用；
    
3. 数据落库完整：`sources/articles/extraction_queue/extraction_items/reports/report_recipients/delivery_log`；
    
4. 失败重试与日志可追溯；
    
5. Provider token/费用统计可查看；
    
6. sys 自检与 `/healthz` 正常；
    
7. 配置项可通过 `.env` 与管理后台（阶段二）调整。
    
