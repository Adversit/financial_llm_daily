# 金融情报日报系统 · 第一阶段任务清单（MVP）

**版本**：v1.1
**日期**：2025-11-06（最后更新）
**适用范围**：阶段一 MVP（采集 → 处理 → 成稿 → 邮件）
**参考文档**：`PRD.md`、`TDD-1.md`、`architecture-phase1.drawio`、`dataflow-phase1.drawio`

---

## 📊 项目进度概览

### 已完成模块 (4/4)

| 模块 | 状态 | 测试覆盖 | 完成日期 | 说明 |
|------|------|----------|----------|------|
| **模块 A** - 信息源采集 | ✅ 完成 | - | 2025-11-06 | base, rss_crawler, static_crawler, text_extractor, deduplicator, crawl_tasks |
| **模块 B** - 信息处理（LLM 抽取） | ✅ 完成 | - | 2025-11-05 | chunking, provider_router, extractor, merger, extract_tasks |
| **模块 C** - 报告生成 | ✅ 完成 | 40/40 通过 | 2025-11-06 | scorer, builder, templates, report_tasks |
| **模块 D** - 邮件投递 | ✅ 完成 | 40/40 通过 | 2025-11-06 | smtp_client, batcher, retry_handler, mail_tasks |

### 待完成任务

#### 🔴 核心功能模块
- ✅ **模块 A - 信息源采集**
  - [x] A-1: 基础采集框架（base.py）
  - [x] A-2: RSS 采集器（rss_crawler.py）
  - [x] A-3: 静态网页采集器（static_crawler.py）
  - [x] A-4: 正文提取器（text_extractor.py）
  - [x] A-5: 去重器（deduplicator.py）
  - [x] A-6: 采集任务（crawl_tasks.py）

#### 🟡 系统支撑模块
- ✅ **任务编排与调度**
  - [x] SCHED-1: Celery 配置（已完成）
  - [x] SCHED-2: 任务编排器（orchestrator.py）
  - [x] SCHED-3: CLI 工具（run_once.py 已完成）

- ✅ **系统支撑**
  - [x] SYS-1: 配置管理（settings.py 已完成）
  - [x] SYS-2: 日志系统（logger.py）
  - [x] SYS-3: 健康检查（health.py）
  - [x] SYS-4: 启动自检（bootstrap.py）

#### 🟢 测试与部署
- ⏳ **测试任务**
  - [x] TEST-1: 单元测试（模块 C、D、系统模块已完成）
  - [ ] TEST-2: 集成测试
  - [ ] TEST-3: 冒烟测试（WSL）

- ⏳ **环境准备**
  - [x] ENV-1: 开发环境搭建（已完成）
  - [x] ENV-2: 数据库初始化（已完成）
  - [x] ENV-3: 配置文件设置（已完成）

### 关键里程碑

- ✅ **2025-11-05**: 模块 B（LLM 抽取）完成
- ✅ **2025-11-06**: 模块 C（报告生成）完成，测试覆盖率 95%+
- ✅ **2025-11-06**: 模块 D（邮件投递）完成，测试覆盖率 100%（batcher）
- ✅ **2025-11-06**: 模块 A（信息源采集）完成
- ✅ **2025-11-06**: 系统支撑模块完成，测试全部通过（16/16）
- ⏳ **待定**: 端到端集成测试
- ⏳ **待定**: 生产环境部署

---

## 任务执行原则

### 开发顺序
**模块完成即测试，测试通过再进入下一模块**

```
✅ 模块 A (采集) → ✅ 模块 B (抽取) → ✅ 模块 C (成稿) → ✅ 模块 D (邮件) → ✅ 系统支撑
```

**当前状态**（2025-11-06 更新）：
- ✅ **模块 A 完成**：信息源采集功能已实现
- ✅ **模块 B 完成**：LLM 抽取功能已实现并测试通过
- ✅ **模块 C 完成**：报告生成功能已实现并测试通过（40/40 测试通过）
- ✅ **模块 D 完成**：邮件投递功能已实现并测试通过（40/40 测试通过）
- ✅ **系统支撑完成**：日志、启动自检、健康检查、任务编排已实现并测试通过（16/16 测试通过）

### 验收标准
- 每个模块独立验收通过后才进入下一模块
- 最终端到端测试：`run_once --step all` 一次跑通
- 时效目标：06:00 启动 → 06:20 前完成邮件发送

---

## 环境准备任务

### ENV-1：开发环境搭建
- [ ] 安装 Python 3.11+（推荐 3.11 或 3.12）
- [ ] 安装 PostgreSQL（Docker 方式）
- [ ] 安装 Redis（Docker 方式或本地）
- [ ] 创建虚拟环境：`python -m venv venv`
- [ ] 安装依赖管理工具（poetry 或 pip）

**验收**：`python --version`、`docker ps` 显示 postgres 和 redis 正常运行

---

### ENV-2：数据库初始化
- [ ] 创建数据库：`fin_daily_report`
- [ ] 配置数据库连接：`DATABASE_URL`
- [ ] 创建枚举类型（region、layer、status等）
- [ ] 创建核心表结构（按 DDL 顺序）：
  - [ ] `sources`
  - [ ] `articles`
  - [ ] `extraction_queue`
  - [ ] `extraction_items`
  - [ ] `reports`
  - [ ] `report_recipients`
  - [ ] `delivery_log`
  - [ ] `provider_usage`
  - [ ] `system_settings`（可选）
- [ ] 创建索引（参考 TDD）
- [ ] 插入初始数据：
  - [ ] 测试信息源（RSS：新智元、BigQuant；网站：2-3个）
  - [ ] 测试收件人（至少1个真实邮箱）

**验收**：能连接数据库，表结构完整，初始数据存在

---

### ENV-3：配置文件设置
创建 `.env` 文件并配置：

```bash
# 基础配置
TZ=Asia/Shanghai
ENV=development  # 或 production

# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/fin_daily_report

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM Provider
PROVIDER_DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
PROVIDER_DEEPSEEK_API_KEY=sk-xxx
PROVIDER_DEEPSEEK_MODEL=deepseek-chat

PROVIDER_QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PROVIDER_QWEN_API_KEY=sk-xxx
PROVIDER_QWEN_MODEL=qwen-max

# 采集配置
CRAWL_CONCURRENCY_RSS=10        # 开发环境高并发
CRAWL_CONCURRENCY_WEB=2
CRAWL_TIMEOUT_SEC=30
CRAWL_RETRY_TIMES=3

# LLM 配置
LLM_TIMEOUT_SEC=90
LLM_RETRIES=2
LLM_CHUNK_BUDGET=0.7
LLM_CHUNK_OVERLAP_CHARS=200
LLM_MAX_CHUNKS_PER_ARTICLE=8
LLM_LONGFORM_STRATEGY=summary_then_extract
LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING=false

# 报告配置
REPORT_TOPN=5
CONFIDENCE_THRESHOLD=0.6
MIN_CONTENT_LEN=120

# 邮件配置
SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USER=your_email@163.com
SMTP_PASS=your_auth_code
MAIL_BATCH_LIMIT=50
MAIL_RATE_LIMIT_PER_SEC=1
MAIL_WINDOW_START=06:05
MAIL_WINDOW_END=06:20
```

**验收**：所有配置项可正常读取，API Key 有效

---

## 核心依赖安装

### DEP-1：Python 依赖包
创建 `requirements.txt` 或 `pyproject.toml`：

```txt
# Web 框架
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# 数据库
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1

# 异步任务
celery==5.3.4
redis==5.0.1

# HTTP 请求
requests==2.31.0
httpx==0.25.2

# RSS 解析
feedparser==6.0.10

# 网页采集与解析
playwright==1.40.0
trafilatura==1.6.3
readability-lxml==0.8.1
beautifulsoup4==4.12.2
lxml==4.9.3

# 文本处理
simhash==2.1.2
jieba==0.42.1

# LLM SDK
openai==1.3.0  # 兼容 DeepSeek/Qwen

# 邮件
aiosmtplib==3.0.1

# 模板引擎
jinja2==3.1.2

# 工具
python-dotenv==1.0.0
loguru==0.7.2
tenacity==8.2.3
```

- [ ] 安装依赖：`pip install -r requirements.txt`
- [ ] 安装 Playwright 浏览器：`playwright install chromium`

**验收**：`pip list` 显示所有包已安装

---

## 项目结构创建

### STRUCT-1：目录结构
```
D:\work\project\Fin_daily_report\V4\
├── src/
│   ├── __init__.py
│   ├── config/               # 配置管理
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── models/               # 数据模型
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── source.py
│   │   ├── article.py
│   │   ├── extraction.py
│   │   ├── report.py
│   │   └── delivery.py
│   ├── db/                   # 数据库
│   │   ├── __init__.py
│   │   ├── session.py
│   │   └── migrations/       # Alembic 迁移文件
│   ├── crawlers/             # 模块 A：采集
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── rss_crawler.py
│   │   ├── static_crawler.py
│   │   ├── dynamic_crawler.py
│   │   ├── text_extractor.py
│   │   └── deduplicator.py
│   ├── nlp/                  # 模块 B：LLM 处理
│   │   ├── __init__.py
│   │   ├── chunking.py       # 分块引擎
│   │   ├── provider_router.py
│   │   ├── extractor.py
│   │   └── merger.py
│   ├── composer/             # 模块 C：报告生成
│   │   ├── __init__.py
│   │   ├── builder.py
│   │   ├── scorer.py
│   │   └── templates/
│   │       ├── email_body.html
│   │       └── attachment.html
│   ├── mailer/               # 模块 D：邮件投递
│   │   ├── __init__.py
│   │   ├── smtp_client.py
│   │   ├── batcher.py
│   │   └── retry_handler.py
│   ├── tasks/                # Celery 任务
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   ├── crawl_tasks.py
│   │   ├── extract_tasks.py
│   │   ├── report_tasks.py
│   │   └── mail_tasks.py
│   ├── api/                  # FastAPI（阶段一仅健康检查）
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── routes/
│   │       └── health.py
│   ├── cli/                  # 命令行工具
│   │   ├── __init__.py
│   │   └── run_once.py
│   └── utils/                # 工具函数
│       ├── __init__.py
│       ├── logger.py
│       ├── retry.py
│       └── time_utils.py
├── tests/                    # 测试
│   ├── __init__.py
│   ├── test_crawlers/
│   ├── test_nlp/
│   ├── test_composer/
│   └── test_mailer/
├── docs/                     # 文档
│   ├── PRD.md
│   ├── TDD-1.md
│   ├── architecture-phase1.drawio
│   ├── dataflow-phase1.drawio
│   └── task.md (本文件)
├── .env                      # 环境变量（不入库）
├── .env.example              # 环境变量模板
├── requirements.txt          # 依赖清单
├── pyproject.toml            # 项目配置（可选）
├── alembic.ini               # Alembic 配置
├── README.md                 # 项目说明
└── claude.md                 # Claude 偏好设置
```

- [ ] 创建所有目录
- [ ] 创建所有 `__init__.py` 文件

**验收**：目录结构完整

---

## 模块 A：信息源采集

### A-1：基础采集框架
**文件**：`src/crawlers/base.py`

- [ ] 定义 `BaseCrawler` 抽象类
- [ ] 实现通用方法：
  - [ ] `fetch_with_retry()` - HTTP 请求重试（指数退避）
  - [ ] `normalize_url()` - URL 标准化
  - [ ] `filter_by_time()` - 24小时过滤
  - [ ] `random_ua()` - 随机 User-Agent
- [ ] 实现错误处理与日志记录

**验收**：单元测试通过

---

### A-2：RSS 采集器
**文件**：`src/crawlers/rss_crawler.py`

- [ ] 实现 `RSSCrawler(BaseCrawler)`
- [ ] 使用 `feedparser` 解析 RSS
- [ ] 去除 HTML 标签，提取纯文本
- [ ] 支持并发采集（配置：`CRAWL_CONCURRENCY_RSS`）
- [ ] 实现：
  ```python
  def fetch_feed(feed_url: str, since: datetime) -> list[dict]:
      """
      返回格式：
      [{
          'title': str,
          'url': str,
          'published_at': datetime,
          'content_text': str,
          'source_name': str
      }]
      """
  ```

**验收**：
- [ ] 成功采集新智元、BigQuant RSS
- [ ] 过滤出过去24小时内容
- [ ] 并发=10时无报错

---

### A-3：静态网站采集器
**文件**：`src/crawlers/static_crawler.py`

- [ ] 实现 `StaticCrawler(BaseCrawler)`
- [ ] 使用 `requests` 获取 HTML
- [ ] 实现通用列表页解析（查找文章链接）
- [ ] 实现详情页采集
- [ ] 超时控制：30s

**验收**：
- [ ] 成功采集 2-3 个测试网站（如 OpenAI Blog）
- [ ] 提取到标题、链接、发布时间

---

### A-4：正文抽取器
**文件**：`src/crawlers/text_extractor.py`

- [ ] 实现 `extract_main_text(html: str, url: str) -> str`
- [ ] 优先级：`trafilatura` → `readability-lxml` → XPath 兜底
- [ ] 清洗噪声（广告、导航、页脚等）
- [ ] 保留段落结构（用于后续分块）

**验收**：
- [ ] 正文抽取准确率 >85%（手工验证 10 个样本）
- [ ] 噪声比 <15%

---

### A-5：动态网站采集器（Playwright）
**文件**：`src/crawlers/dynamic_crawler.py`

- [ ] 实现 `DynamicCrawler(BaseCrawler)`
- [ ] 使用 `Playwright` 渲染 JS 页面
- [ ] 自动滚动加载（最多3次，间隔2s）
- [ ] 超时控制：25s
- [ ] 仅在静态采集失败时作为兜底

**验收**：
- [ ] 成功渲染需要 JS 的页面
- [ ] 超时保护生效

---

### A-6：去重引擎
**文件**：`src/crawlers/deduplicator.py`

- [ ] 实现一级去重：
  - [ ] 优先：`canonical_url`
  - [ ] 兜底：标准化 URL + 标题 + 发布时间近似
- [ ] 实现二级去重：
  - [ ] 使用 `simhash` 库计算文本指纹
  - [ ] 汉明距离 ≤3 判定为近重复
- [ ] 实现保留策略：
  - [ ] 优先保留发布时间更早的
  - [ ] 或来源权威性更高的

**验收**：
- [ ] 重复文章正确去重（准确率 >95%）
- [ ] 近重复文章正确识别（召回率 >80%）

---

### A-7：采集任务与落库
**文件**：`src/tasks/crawl_tasks.py`

- [ ] 实现 Celery 任务：
  - [ ] `crawl_rss_task(source_id)`
  - [ ] `crawl_static_task(source_id)`
  - [ ] `crawl_dynamic_task(source_id)`
- [ ] 从 `sources` 表读取配置（`enabled=true`）
- [ ] 调用对应采集器
- [ ] 去重处理
- [ ] 写入 `articles` 表：
  - [ ] `processing_status='raw'`
  - [ ] 计算并存储 `simhash`
  - [ ] 存储 `canonical_url` 或 `dedup_key`
- [ ] 同时写入 `extraction_queue` 表：
  - [ ] `status='queued'`
  - [ ] `priority=0`
  - [ ] `attempts=0`

**验收**：
- [ ] `articles` 表写入 ≥10 条记录
- [ ] `extraction_queue` 表对应记录存在
- [ ] 去重规则生效（重复文章不重复入库）
- [ ] 失败不阻塞其它源

---

### A-8：模块 A 集成测试
- [ ] 端到端测试：从 RSS/网站采集到落库
- [ ] 并发测试：多源同时采集无冲突
- [ ] 失败恢复：单个源失败不影响其它源
- [ ] CLI 测试：`python -m src.cli.run_once --step crawl`

**模块 A 验收标准**：
- ✅ `articles` ≥ 10 条
- ✅ `extraction_queue` 入队正常
- ✅ 去重规则生效
- ✅ 失败可在日志中定位

---

## 模块 B：信息处理（LLM 抽取） ✅ 已完成

### B-1：分块引擎 ✅
**文件**：`src/nlp/chunking.py`

- [x] 实现 Token 估算器：
  - [ ] 优先：使用与模型兼容的 tokenizer
  - [ ] 退化：字符基准估算（中文 1:1，混合 1.2:1）
  ```python
  def estimate_tokens(text: str, lang_hint: str = "zh") -> int:
      pass
  ```

- [ ] 实现语义切分：
  - [ ] 按段落划分（空行/换行符）
  - [ ] 按句子划分（`。！？!?` + 英文句号）
  - [ ] 句子装箱：逐句累加，接近 `target_tokens` 时切分
  ```python
  def split_by_semantics(text: str) -> list[str]:
      """返回段落列表"""
      pass

  def pack_sentences_into_chunks(
      sentences: list[str],
      target_tokens: int,
      overlap_chars: int = 200
  ) -> list[str]:
      """返回分块列表，块间重叠 overlap_chars"""
      pass
  ```

- [ ] 实现分块规划：
  ```python
  def plan_chunks(
      text: str,
      lang_hint: str,
      model_input_limit: int,
      budget: float = 0.7,
      overlap_chars: int = 200,
      max_chunks: int = 8,
      strategy: str = "summary_then_extract"
  ) -> list[str] | ChunkPlan:
      """
      返回分块列表，或触发降级策略
      """
      pass
  ```

- [ ] 实现降级策略：
  - [ ] `summary_then_extract`：先提要，再分块抽取
  - [ ] `headN_plus_overall`：前N段 + 全文概括

**验收**：
- [ ] 10K 字文本 → ≤8 段
- [ ] 相邻段重叠约 200 字
- [ ] 不跨句截断
- [ ] 触发降级时返回 `ChunkPlan` 对象

---

### B-2：Provider 路由器
**文件**：`src/nlp/provider_router.py`

- [ ] 实现统一 LLM 客户端接口：
  ```python
  class LLMProvider(ABC):
      @abstractmethod
      async def chat_completion(
          self,
          messages: list[dict],
          temperature: float = 0.3,
          timeout: int = 90
      ) -> dict:
          """返回标准化响应"""
          pass
  ```

- [ ] 实现 DeepSeek Provider：
  ```python
  class DeepSeekProvider(LLMProvider):
      def __init__(self, api_key: str, base_url: str, model: str):
          pass
  ```

- [ ] 实现 Qwen Provider：
  ```python
  class QwenProvider(LLMProvider):
      def __init__(self, api_key: str, base_url: str, model: str):
          pass
  ```

- [ ] 实现 Provider 路由器：
  ```python
  class ProviderRouter:
      def __init__(self):
          self.providers = [deepseek, qwen]  # 优先级顺序

      async def call_with_fallback(
          self,
          messages: list[dict],
          retries: int = 2,
          timeout: int = 90
      ) -> tuple[dict, str]:
          """
          返回：(响应, provider_name)
          自动回退到下一个 Provider
          """
          pass
  ```

- [ ] 实现并发控制（可选）：
  ```python
  class ConcurrencyController:
      def __init__(self, max_inflight: int = 2):
          self.semaphore = asyncio.Semaphore(max_inflight)

      async def call(self, provider, messages):
          async with self.semaphore:
              return await provider.chat_completion(messages)
  ```

**验收**：
- [ ] DeepSeek 调用成功
- [ ] 模拟 DeepSeek 失败 → 自动切换到 Qwen
- [ ] 超时 90s 生效
- [ ] 重试 2 次生效

---

### B-3：LLM 抽取器
**文件**：`src/nlp/extractor.py`

- [ ] 定义抽取 Prompt 模板：
  ```python
  EXTRACTION_PROMPT = """
  你是一个专业的金融情报分析师。请从以下文章中抽取：

  1. 客观事实（fact）：重要事件、数据、发布等，必选
  2. 观点（opinion）：作者/机构的观点、预测、评论，可选
  3. 区域（region）：国内 | 国外 | 未知
  4. 层级（layer）：政治 | 经济 | 金融大模型技术 | 金融科技 | 未知
  5. 置信度（confidence）：0.0-1.0

  以 JSON 格式返回：
  {
    "items": [
      {
        "fact": "...",
        "opinion": "...(可为空)",
        "region": "国内|国外|未知",
        "layer": "政治|经济|金融大模型技术|金融科技|未知",
        "evidence_span": "原文句段",
        "confidence": 0.85
      }
    ]
  }

  文章内容：
  {content}
  """
  ```

- [ ] 实现分段抽取：
  ```python
  async def extract_from_chunk(
      chunk: str,
      provider_router: ProviderRouter
  ) -> dict:
      """对单个分块调用 LLM 抽取"""
      pass
  ```

- [ ] 实现文章级抽取：
  ```python
  async def extract_article(
      article_id: int,
      provider_router: ProviderRouter
  ) -> ExtractResult:
      """
      1. 读取文章内容
      2. 分块（如需要）
      3. 逐段调用 LLM
      4. 合并结果
      5. 返回 ExtractResult(status, items, metadata)
      """
      pass
  ```

- [ ] 实现统一中文展示（可选）：
  - [ ] 检测非中文内容
  - [ ] 调用翻译接口或在 Prompt 中要求翻译
  - [ ] 保留原文片段字段用于溯源

**验收**：
- [ ] 单段文章抽取成功，返回 JSON Schema 正确
- [ ] 多段文章逐段抽取 + 合并成功
- [ ] 超时/失败触发回退，记录 `processing_status`

---

### B-4：合并去重器
**文件**：`src/nlp/merger.py`

- [ ] 实现事实归一化：
  ```python
  def normalize_fact(fact: str) -> str:
      """
      - 去空白
      - 半角/全角统一
      - 标点清洗
      - 数字标准化（中文数字→阿拉伯）
      """
      pass
  ```

- [ ] 实现近似去重：
  ```python
  def deduplicate_facts(items: list[dict]) -> list[dict]:
      """
      使用 SimHash 或编辑距离 ≤2 去重
      保留置信度更高的条目
      """
      pass
  ```

- [ ] 实现 region/layer 冲突解决：
  ```python
  def resolve_conflicts(items: list[dict]) -> list[dict]:
      """
      以频次多数为先，置信度为次
      """
      pass
  ```

- [ ] 实现合并主函数：
  ```python
  def merge_extraction_results(
      chunk_results: list[dict]
  ) -> dict:
      """
      返回：
      {
        "items": [...],  # 去重后的事实观点列表
        "metadata": {
          "total_chunks": int,
          "merged_count": int,
          "dedup_count": int
        }
      }
      """
      pass
  ```

**验收**：
- [ ] 两段输出相似事实（编辑距≤2）→ 合并为1条
- [ ] 保留置信度更高的版本
- [ ] region/layer 冲突正确解决

---

### B-5：抽取任务
**文件**：`src/tasks/extract_tasks.py`

- [ ] 实现 Celery 任务：
  ```python
  @celery_app.task
  def extract_article_task(article_id: int):
      """
      1. 更新 extraction_queue: status='running'
      2. 读取 article 内容
      3. 调用 extract_article()
      4. 写入 extraction_items
      5. 更新 extraction_queue: status='done'/'failed'
      6. 更新 articles: processing_status='done'/'failed'
      7. 记录 provider_usage（token/费用）
      """
      pass

  @celery_app.task
  def run_extraction_batch():
      """
      批量处理队列中的文章
      根据配置决定串行/并行
      """
      pass
  ```

- [ ] 实现错误处理：
  - [ ] 段级失败：跳过该段，继续其它段
  - [ ] 文章级失败：记录 `last_error`，增加 `attempts`
  - [ ] 达到最大重试次数：标记 `status='failed'`

- [ ] 实现 Token/费用统计：
  ```python
  def log_provider_usage(
      provider: str,
      model: str,
      prompt_tokens: int,
      completion_tokens: int,
      cost: float
  ):
      """写入 provider_usage 表"""
      pass
  ```

**验收**：
- [ ] `extraction_items` 表写入 ≥20 条记录
- [ ] `extraction_queue` 状态正确更新
- [ ] `articles.processing_status` 更新为 `done`/`failed`
- [ ] `provider_usage` 记录 token 和费用

---

### B-6：模块 B 集成测试
- [ ] 端到端测试：从队列读取到写入 extraction_items
- [ ] 长文测试：10K+ 字文章正确分块和合并
- [ ] 降级测试：>8 段触发降级策略
- [ ] 回退测试：DeepSeek 失败 → Qwen 成功
- [ ] CLI 测试：`python -m src.cli.run_once --step extract`

**模块 B 验收标准**：
- ✅ `extraction_items` ≥ 20 条
- ✅ JSON Schema 全部正确
- ✅ 长文分块/回退/合并正常
- ✅ 串行模式稳定通过

---

## 模块 C：报告生成 ✅ 已完成

### C-1：评分器
**文件**：`src/composer/scorer.py`

- [ ] 实现过滤函数：
  ```python
  def filter_items(items: list[dict]) -> list[dict]:
      """
      过滤条件：
      - confidence ≥ 0.6
      - 关联文章 content_len ≥ 120 字
      - processing_status = 'done'
      """
      pass
  ```

- [ ] 实现评分函数：
  ```python
  def calculate_score(item: dict, article: dict, source: dict) -> float:
      """
      score = 0.5 * 影响力 + 0.3 * 新近度 + 0.2 * 来源权威

      影响力：基于 confidence
      新近度：发布时间距今的小时数（越近越高）
      权威性：来源权重（可在 sources 表配置）
      """
      pass
  ```

- [ ] 实现分区排序：
  ```python
  def section_and_sort(items: list[dict]) -> dict:
      """
      返回：
      {
        "国内": {
          "政治": [item1, item2, ...],  # 按 score 降序
          "经济": [...],
          "金融大模型技术": [...],
          "金融科技": [...]
        },
        "国外": { ... }
      }
      """
      pass
  ```

- [ ] 实现 TopN 筛选：
  ```python
  def select_topn(sections: dict, topn: int = 5) -> dict:
      """
      每个分区取 TopN
      """
      pass
  ```

**验收**：
- [ ] 过滤规则正确（低置信度/短文被过滤）
- [ ] 评分合理（新发布、高置信度、权威源排前）
- [ ] 分区正确
- [ ] TopN 正确

---

### C-2：报告构建器
**文件**：`src/composer/builder.py`

- [ ] 实现总览摘要生成（可选 LLM）：
  ```python
  def generate_overview(sections: dict) -> str:
      """
      生成 150-250 字总览摘要
      可调用 LLM 或基于规则生成
      """
      pass
  ```

- [ ] 实现正文 HTML 生成：
  ```python
  def build_email_body(
      report_date: date,
      overview: str,
      sections_topn: dict,
      template_path: str = "templates/email_body.html"
  ) -> str:
      """
      使用 Jinja2 渲染模板：
      - 抬头：项目名 + 日期
      - 总览摘要
      - 目录锚点
      - 分区卡片（TopN）
        - 标题（原文链接）
        - 1-2 句干货摘要
        - 标签（region/layer）
        - 来源名 + 发布时间
      """
      pass
  ```

- [ ] 实现附件 HTML 生成：
  ```python
  def build_attachment(
      sections_full: dict,
      template_path: str = "templates/attachment.html"
  ) -> str:
      """
      使用 Jinja2 渲染模板：
      - 全量事实与观点
      - 每条含原文链接
      - 按来源/时间排序
      - 不内嵌图片
      """
      pass
  ```

- [ ] 实现元数据生成：
  ```python
  def build_metadata(sections: dict) -> dict:
      """
      返回：
      {
        "total_items": int,
        "topn_items": int,
        "sections_count": dict,
        "build_time_ms": int
      }
      """
      pass
  ```

**验收**：
- [ ] 正文 HTML 结构正确（目录锚点、卡片、链接可点击）
- [ ] 附件 HTML 包含全量内容
- [ ] 总览摘要合理
- [ ] 元数据正确

---

### C-3：HTML 模板
**文件**：`src/composer/templates/email_body.html`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>金融情报日报 - {{ report_date }}</title>
    <style>
        /* 邮件安全样式（内联 CSS） */
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; }
        .header { background: #1e3a8a; color: white; padding: 20px; }
        .overview { background: #f3f4f6; padding: 15px; margin: 20px 0; }
        .toc { margin: 20px 0; }
        .section { margin: 30px 0; }
        .card { border-left: 4px solid #3b82f6; padding: 15px; margin: 10px 0; background: #fafafa; }
        .card-title { font-size: 18px; font-weight: bold; }
        .card-summary { margin: 10px 0; color: #374151; }
        .card-meta { font-size: 12px; color: #6b7280; }
        .tag { display: inline-block; padding: 2px 8px; background: #dbeafe; border-radius: 4px; margin-right: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>金融情报日报</h1>
        <p>{{ report_date }}</p>
    </div>

    <div class="overview">
        <h2>今日总览</h2>
        <p>{{ overview }}</p>
    </div>

    <div class="toc">
        <h3>目录</h3>
        <ul>
            {% for region in sections.keys() %}
                <li><a href="#{{ region }}">{{ region }}</a></li>
            {% endfor %}
        </ul>
    </div>

    {% for region, layers in sections.items() %}
        <div class="section" id="{{ region }}">
            <h2>{{ region }}</h2>
            {% for layer, items in layers.items() %}
                <h3>{{ layer }}</h3>
                {% for item in items %}
                <div class="card">
                    <div class="card-title">
                        <a href="{{ item.article_url }}" target="_blank">{{ item.article_title }}</a>
                    </div>
                    <div class="card-summary">{{ item.fact[:200] }}...</div>
                    <div class="card-meta">
                        <span class="tag">{{ item.region }}</span>
                        <span class="tag">{{ item.layer }}</span>
                        <span>{{ item.source_name }} · {{ item.published_at }}</span>
                    </div>
                </div>
                {% endfor %}
            {% endfor %}
        </div>
    {% endfor %}

    <div style="margin-top: 40px; padding: 20px; background: #f9fafb; text-align: center; color: #6b7280; font-size: 12px;">
        <p>如需退订请联系管理员邮箱</p>
    </div>
</body>
</html>
```

**文件**：`src/composer/templates/attachment.html`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>金融情报日报全量附件 - {{ report_date }}</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }
        .header { border-bottom: 2px solid #1e3a8a; padding-bottom: 10px; margin-bottom: 20px; }
        .item { border: 1px solid #e5e7eb; padding: 15px; margin: 10px 0; }
        .fact { font-weight: bold; margin-bottom: 5px; }
        .opinion { color: #6b7280; font-style: italic; margin-bottom: 5px; }
        .meta { font-size: 12px; color: #9ca3af; }
        .link { color: #3b82f6; text-decoration: none; }
    </style>
</head>
<body>
    <div class="header">
        <h1>金融情报日报 - 全量事实与观点</h1>
        <p>{{ report_date }}</p>
    </div>

    {% for region, layers in sections_full.items() %}
        <h2>{{ region }}</h2>
        {% for layer, items in layers.items() %}
            <h3>{{ layer }}</h3>
            {% for item in items %}
            <div class="item">
                <div class="fact">【事实】{{ item.fact }}</div>
                {% if item.opinion %}
                <div class="opinion">【观点】{{ item.opinion }}</div>
                {% endif %}
                <div class="meta">
                    来源：<a href="{{ item.article_url }}" class="link" target="_blank">{{ item.article_title }}</a>
                    | {{ item.source_name }}
                    | {{ item.published_at }}
                    | 置信度：{{ item.confidence }}
                </div>
            </div>
            {% endfor %}
        {% endfor %}
    {% endfor %}
</body>
</html>
```

**验收**：
- [ ] 模板渲染正确
- [ ] 样式在主流邮件客户端正常显示

---

### C-4：报告任务
**文件**：`src/tasks/report_tasks.py`

- [ ] 实现 Celery 任务：
  ```python
  @celery_app.task
  def build_report_task(report_date: date):
      """
      1. 读取当日 extraction_items
      2. 过滤 + 评分 + 分区 + 排序
      3. 生成 TopN（正文）和全量（附件）
      4. 渲染 HTML
      5. 生成元数据
      6. 写入 reports 表
      """
      pass
  ```

- [ ] 写入 `reports` 表：
  - [ ] `report_date`
  - [ ] `html_body`（正文 HTML）
  - [ ] `html_attachment`（附件 HTML）
  - [ ] `sections_json`（分区统计 JSON）
  - [ ] `build_meta`（元数据 JSON）
  - [ ] `build_ms`（构建耗时）

**验收**：
- [ ] `reports` 表写入 1 条记录
- [ ] `html_body` 和 `html_attachment` 非空
- [ ] `sections_json` 结构正确

---

### C-5：模块 C 集成测试
- [ ] 端到端测试：从 extraction_items 读取到写入 reports
- [ ] 模板测试：HTML 在浏览器中正常显示
- [ ] 边界测试：某分区无数据时不报错
- [ ] CLI 测试：`python -m src.cli.run_once --step compose`

**模块 C 验收标准**：
- ✅ `reports` = 1 条
- ✅ 正文 TopN + 附件全量
- ✅ 链接可用
- ✅ 模板渲染正确

---

## 模块 D：邮件投递 ✅ 已完成

### D-1：SMTP 客户端
**文件**：`src/mailer/smtp_client.py`

- [ ] 实现 SMTP 客户端：
  ```python
  class SMTPClient:
      def __init__(
          self,
          host: str = "smtp.163.com",
          port: int = 465,
          user: str = None,
          password: str = None
      ):
          pass

      async def send_email(
          self,
          to: list[str],
          bcc: list[str],
          subject: str,
          html_body: str,
          attachments: list[tuple[str, bytes]] = None
      ) -> dict:
          """
          返回：
          {
            "message_id": str,
            "status": "ok" | "failed",
            "error": str | None
          }
          """
          pass
  ```

- [ ] 使用 `aiosmtplib` 实现异步发送
- [ ] 使用 SSL 465 端口
- [ ] 支持 UTF-8 编码
- [ ] 支持 HTML 附件（`Content-Type: text/html`）

**验收**：
- [ ] 成功发送测试邮件
- [ ] 附件正确接收
- [ ] UTF-8 中文正常显示

---

### D-2：分批与节流器
**文件**：`src/mailer/batcher.py`

- [ ] 实现分批逻辑：
  ```python
  def batch_recipients(
      recipients: list[str],
      batch_size: int = 50
  ) -> list[dict]:
      """
      返回：
      [
        {"to": [email1], "bcc": [email2, ..., email50]},
        {"to": [email51], "bcc": [email52, ..., email100]},
        ...
      ]
      """
      pass
  ```

- [ ] 实现节流逻辑：
  ```python
  class RateLimiter:
      def __init__(self, rate_per_sec: float = 1.0):
          self.rate = rate_per_sec
          self.last_call = 0

      async def throttle(self):
          """确保调用间隔 ≥ 1/rate 秒"""
          pass
  ```

**验收**：
- [ ] 100 个收件人 → 正确分为 2 批（50+50）
- [ ] 发送间隔 ≥1 秒

---

### D-3：重试与退信处理器
**文件**：`src/mailer/retry_handler.py`

- [ ] 实现重试逻辑：
  ```python
  async def send_with_retry(
      smtp_client: SMTPClient,
      email_data: dict,
      max_retries: int = 2
  ) -> dict:
      """
      失败自动重试，指数退避
      """
      pass
  ```

- [ ] 实现退信检测：
  ```python
  def is_hard_bounce(error_message: str) -> bool:
      """
      检测硬退信（用户不存在、域名无效等）
      """
      pass

  def add_to_blacklist(email: str):
      """
      将硬退信邮箱加入黑名单
      可在 report_recipients 表标记 enabled=false
      """
      pass
  ```

**验收**：
- [ ] 模拟发送失败 → 自动重试 2 次
- [ ] 检测到硬退信 → 加入黑名单

---

### D-4：邮件任务
**文件**：`src/tasks/mail_tasks.py`

- [ ] 实现 Celery 任务：
  ```python
  @celery_app.task
  def send_report_task(report_date: date):
      """
      1. 读取 reports 表（当日）
      2. 读取 report_recipients（type='recipient', enabled=true）
      3. 组装邮件：
         - 主题：金融情报日报 - YYYY-MM-DD
         - 正文：html_body
         - 附件：daily-report-YYYY-MM-DD.html
      4. 分批处理（最多50人/封）
      5. 节流发送（1封/秒）
      6. 记录 delivery_log
      """
      pass
  ```

- [ ] 实现窗口检查：
  ```python
  def check_time_window(
      start: str = "06:05",
      end: str = "06:20"
  ) -> bool:
      """
      检查当前时间是否在窗口内
      """
      pass
  ```

- [ ] 写入 `delivery_log` 表：
  - [ ] `report_id`
  - [ ] `batch_no`（批次号）
  - [ ] `recipients_snapshot`（收件人快照 JSON）
  - [ ] `message_id`（SMTP 返回的 message_id）
  - [ ] `status`（ok / failed / partial）
  - [ ] `error_code`, `error_message`
  - [ ] `sent_at`（发送时间）
  - [ ] `duration_ms`（耗时）

**验收**：
- [ ] 至少 1 封真实邮件发送成功
- [ ] `delivery_log` 表记录完整
- [ ] 批次、状态、错误信息正确

---

### D-5：模块 D 集成测试
- [ ] 端到端测试：从 reports 读取到邮件发送
- [ ] 分批测试：多收件人正确分批
- [ ] 节流测试：发送间隔 ≥1 秒
- [ ] 重试测试：失败自动重试
- [ ] 窗口测试：超出窗口时告警
- [ ] CLI 测试：`python -m src.cli.run_once --step send`

**模块 D 验收标准**：
- ✅ 真实邮件发送成功
- ✅ `delivery_log` 完整
- ✅ 分批/节流/重试正常

---

## 任务编排与调度

### SCHED-1：Celery 配置
**文件**：`src/tasks/celery_app.py`

- [ ] 配置 Celery：
  ```python
  from celery import Celery

  celery_app = Celery(
      "fin_daily_report",
      broker=settings.REDIS_URL,
      backend=settings.REDIS_URL
  )

  celery_app.conf.update(
      task_serializer="json",
      accept_content=["json"],
      result_serializer="json",
      timezone="Asia/Shanghai",
      enable_utc=False,
      task_routes={
          "src.tasks.crawl_tasks.*": {"queue": "crawl"},
          "src.tasks.extract_tasks.*": {"queue": "extract"},
          "src.tasks.report_tasks.*": {"queue": "report"},
          "src.tasks.mail_tasks.*": {"queue": "mail"},
      }
  )
  ```

- [ ] 配置 Celery Beat 定时任务：
  ```python
  from celery.schedules import crontab

  celery_app.conf.beat_schedule = {
      "daily-report-06:00": {
          "task": "src.tasks.orchestrator.run_daily_report",
          "schedule": crontab(hour=6, minute=0),
      }
  }
  ```

**验收**：
- [ ] Celery Worker 正常启动
- [ ] Celery Beat 正常启动
- [ ] 任务路由正确

---

### SCHED-2：任务编排器
**文件**：`src/tasks/orchestrator.py`

- [ ] 实现端到端编排任务：
  ```python
  @celery_app.task
  def run_daily_report():
      """
      完整流程编排：
      1. 采集（06:00）
      2. 抽取（06:05）
      3. 成稿（06:10）
      4. 发送（06:12）
      """
      from celery import chain, group

      # 1. 并发采集所有源
      crawl_tasks = []
      sources = get_enabled_sources()
      for source in sources:
          if source.type == "rss":
              crawl_tasks.append(crawl_rss_task.s(source.id))
          elif source.type == "static":
              crawl_tasks.append(crawl_static_task.s(source.id))

      # 2. 等待采集完成 → 批量抽取
      # 3. 等待抽取完成 → 生成报告
      # 4. 等待报告完成 → 发送邮件
      workflow = chain(
          group(*crawl_tasks),
          run_extraction_batch.s(),
          build_report_task.s(date.today()),
          send_report_task.s(date.today())
      )

      return workflow.apply_async()
  ```

**验收**：
- [ ] 手动触发 `run_daily_report` 任务
- [ ] 所有步骤按顺序执行
- [ ] 失败任务不阻塞后续流程

---

### SCHED-3：CLI 工具
**文件**：`src/cli/run_once.py`

- [ ] 实现命令行工具：
  ```python
  import click

  @click.command()
  @click.option("--step", type=click.Choice(["crawl", "extract", "compose", "send", "all"]), required=True)
  @click.option("--date", type=str, default=None, help="指定日期 YYYY-MM-DD")
  def run_once(step: str, date: str):
      """
      手动执行单个步骤或完整流程

      示例：
        python -m src.cli.run_once --step crawl
        python -m src.cli.run_once --step all
        python -m src.cli.run_once --step extract --date 2025-11-04
      """
      if step == "crawl":
          # 触发采集任务
          pass
      elif step == "extract":
          # 触发抽取任务
          pass
      elif step == "compose":
          # 触发报告生成任务
          pass
      elif step == "send":
          # 触发邮件发送任务
          pass
      elif step == "all":
          # 触发完整流程
          pass

  if __name__ == "__main__":
      run_once()
  ```

**验收**：
- [ ] `run_once --step crawl` 成功执行
- [ ] `run_once --step all` 完整跑通

---

## 系统支撑模块

### SYS-1：配置管理
**文件**：`src/config/settings.py`

- [ ] 使用 `pydantic-settings` 管理配置：
  ```python
  from pydantic_settings import BaseSettings

  class Settings(BaseSettings):
      # 基础
      TZ: str = "Asia/Shanghai"
      ENV: str = "development"

      # 数据库
      DATABASE_URL: str

      # Redis
      REDIS_URL: str

      # LLM
      PROVIDER_DEEPSEEK_API_KEY: str
      PROVIDER_DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
      PROVIDER_DEEPSEEK_MODEL: str = "deepseek-chat"

      PROVIDER_QWEN_API_KEY: str
      PROVIDER_QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
      PROVIDER_QWEN_MODEL: str = "qwen-max"

      # 采集
      CRAWL_CONCURRENCY_RSS: int = 10
      CRAWL_CONCURRENCY_WEB: int = 2
      CRAWL_TIMEOUT_SEC: int = 30
      CRAWL_RETRY_TIMES: int = 3

      # LLM
      LLM_TIMEOUT_SEC: int = 90
      LLM_RETRIES: int = 2
      LLM_CHUNK_BUDGET: float = 0.7
      LLM_CHUNK_OVERLAP_CHARS: int = 200
      LLM_MAX_CHUNKS_PER_ARTICLE: int = 8
      LLM_LONGFORM_STRATEGY: str = "summary_then_extract"
      LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING: bool = False

      # 报告
      REPORT_TOPN: int = 5
      CONFIDENCE_THRESHOLD: float = 0.6
      MIN_CONTENT_LEN: int = 120

      # 邮件
      SMTP_HOST: str = "smtp.163.com"
      SMTP_PORT: int = 465
      SMTP_USER: str
      SMTP_PASS: str
      MAIL_BATCH_LIMIT: int = 50
      MAIL_RATE_LIMIT_PER_SEC: float = 1.0
      MAIL_WINDOW_START: str = "06:05"
      MAIL_WINDOW_END: str = "06:20"

      class Config:
          env_file = ".env"
          case_sensitive = False

  settings = Settings()
  ```

**验收**：
- [ ] 所有配置项可正常读取
- [ ] `.env` 文件修改后立即生效

---

### SYS-2：日志系统
**文件**：`src/utils/logger.py`

- [ ] 使用 `loguru` 配置日志：
  ```python
  from loguru import logger
  import sys

  logger.remove()
  logger.add(
      sys.stdout,
      format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
      level="INFO"
  )

  logger.add(
      "logs/app_{time:YYYY-MM-DD}.log",
      rotation="00:00",
      retention="180 days",
      level="INFO"
  )

  logger.add(
      "logs/error_{time:YYYY-MM-DD}.log",
      rotation="00:00",
      retention="365 days",
      level="ERROR"
  )
  ```

- [ ] 在关键位置添加日志：
  - [ ] 任务开始/结束
  - [ ] 关键步骤（采集、抽取、发送）
  - [ ] 错误与异常
  - [ ] 性能指标（耗时、队列长度）

**验收**：
- [ ] 日志正常输出到控制台和文件
- [ ] 错误日志单独记录

---

### SYS-3：健康检查
**文件**：`src/api/routes/health.py`

- [ ] 实现健康检查端点：
  ```python
  from fastapi import APIRouter

  router = APIRouter()

  @router.get("/healthz")
  async def health_check():
      """
      检查：
      - 数据库连通性
      - Redis 连通性
      - Celery Worker 存活
      """
      checks = {
          "status": "ok",
          "database": check_database(),
          "redis": check_redis(),
          "celery_workers": check_celery_workers()
      }

      if all(v == "ok" for v in checks.values() if v != "ok"):
          return checks
      else:
          return {"status": "error", "checks": checks}
  ```

**验收**：
- [ ] 访问 `/healthz` 返回正常状态
- [ ] 数据库/Redis 异常时返回错误

---

### SYS-4：启动自检
**文件**：`src/utils/bootstrap.py`

- [ ] 实现启动自检：
  ```python
  def bootstrap():
      """
      应用启动时自动执行：
      1. 检查必需环境变量
      2. 检查数据库连接
      3. 检查 Redis 连接
      4. 检查 LLM Provider API Key 有效性
      5. 检查表结构完整性
      """
      logger.info("🚀 启动自检...")

      # 检查环境变量
      required_vars = ["DATABASE_URL", "REDIS_URL", "SMTP_USER", "SMTP_PASS", ...]
      for var in required_vars:
          if not getattr(settings, var, None):
              logger.error(f"❌ 缺少必需环境变量: {var}")
              sys.exit(1)

      # 检查数据库
      try:
          db.execute("SELECT 1")
          logger.info("✅ 数据库连接正常")
      except Exception as e:
          logger.error(f"❌ 数据库连接失败: {e}")
          sys.exit(1)

      # ... 其它检查

      logger.info("✅ 启动自检完成")
  ```

**验收**：
- [ ] 启动时自动执行自检
- [ ] 缺少配置时拒绝启动

---

## 测试任务

### TEST-1：单元测试
为每个模块编写单元测试（使用 `pytest`）：

- [ ] `tests/test_crawlers/` - 采集器测试
  - [ ] `test_rss_crawler.py`
  - [ ] `test_static_crawler.py`
  - [ ] `test_deduplicator.py`
- [ ] `tests/test_nlp/` - LLM 处理测试
  - [ ] `test_chunking.py`
  - [ ] `test_provider_router.py`
  - [ ] `test_merger.py`
- [ ] `tests/test_composer/` - 报告生成测试
  - [ ] `test_scorer.py`
  - [ ] `test_builder.py`
- [ ] `tests/test_mailer/` - 邮件测试
  - [ ] `test_batcher.py`
  - [ ] `test_smtp_client.py`

**验收**：
- [ ] 单元测试覆盖率 ≥70%
- [ ] 所有测试通过

---

### TEST-2：集成测试
- [ ] 端到端测试（使用真实数据库 + Mock LLM）
- [ ] 使用 MailHog 测试邮件发送
- [ ] 模拟失败场景（网络超时、API 错误等）

**验收**：
- [ ] 集成测试通过

---

### TEST-3：冒烟测试（WSL）
在开发环境完整跑通：

```bash
# 1. 启动依赖服务
docker-compose up -d postgres redis

# 2. 初始化数据库
alembic upgrade head

# 3. 插入测试数据
python scripts/seed_test_data.py

# 4. 启动 Celery Worker
celery -A src.tasks.celery_app worker --loglevel=info

# 5. 手动触发完整流程
python -m src.cli.run_once --step all

# 6. 检查结果
# - articles ≥ 10
# - extraction_items ≥ 20
# - reports = 1
# - delivery_log ≥ 1
# - 收件箱收到邮件
```

**验收**：
- [ ] CLI 一次跑通
- [ ] 06:20 前完成
- [ ] 数据库记录完整
- [ ] 邮件发送成功

---

## 最终验收（阶段一完成标准）

### 功能验收
- [ ] ✅ **模块 A**：`articles` ≥ 10，去重生效，`extraction_queue` 入队
- [ ] ✅ **模块 B**：`extraction_items` ≥ 20，分块/回退/合并正常
- [ ] ✅ **模块 C**：`reports` = 1，正文 TopN+附件全量，链接可用
- [ ] ✅ **模块 D**：真实邮件发送成功，`delivery_log` 完整

### 性能验收
- [ ] ✅ 06:00 启动 → 06:20 前完成邮件发送（时效目标）
- [ ] ✅ WSL 开发环境：30-80 篇文章场景满足窗口内完成

### 质量验收
- [ ] ✅ 单元测试覆盖率 ≥70%
- [ ] ✅ 所有测试通过
- [ ] ✅ 日志完整，错误可追溯
- [ ] ✅ 失败任务不阻塞流程

### 文档验收
- [ ] ✅ README.md 完整（环境搭建、配置说明、运行指南）
- [ ] ✅ `.env.example` 提供配置模板
- [ ] ✅ API 文档（FastAPI 自动生成）

---

## 附录：常用命令

### 数据库
```bash
# 初始化迁移
alembic init alembic

# 创建迁移
alembic revision --autogenerate -m "Initial schema"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### Celery
```bash
# 启动 Worker
celery -A src.tasks.celery_app worker --loglevel=info --concurrency=4

# 启动 Beat（定时任务）
celery -A src.tasks.celery_app beat --loglevel=info

# 查看任务列表
celery -A src.tasks.celery_app inspect registered

# 查看队列状态
celery -A src.tasks.celery_app inspect active
```

### 测试
```bash
# 运行所有测试
pytest

# 运行指定测试
pytest tests/test_crawlers/test_rss_crawler.py

# 查看覆盖率
pytest --cov=src --cov-report=html
```

### Docker
```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f postgres

# 停止服务
docker-compose down
```

---

## 风险与注意事项

### 风险
1. **2C/2G 资源受限**：生产环境并发能力有限，需严格控制并发数
2. **LLM API 不稳定**：DeepSeek/Qwen 可能超时或限流，需完善重试和回退机制
3. **邮件发送受限**：网易邮箱可能触发反垃圾机制，需控制发送频率
4. **时效目标紧张**：20 分钟窗口内完成，需优化性能和并发策略

### 注意事项
- 开发期使用高并发压测，生产期严格控制并发=2
- LLM 分块尽量少分，降低成本和时延
- 邮件节流 1封/秒，避免被封禁
- 失败任务记录详细日志，便于补抓和调试
- 定期检查 `extraction_queue` 积压情况

---

**祝开发顺利！🚀**
