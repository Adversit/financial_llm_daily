# 金融情报日报系统 · 参数约定文档

**版本**：v1.0
**日期**：2025-11-08
**用途**：记录系统所有参数、配置、命名规范和约定，确保开发和维护的一致性

---

## 目录

1. [数据库约定](#1-数据库约定)
2. [环境变量配置](#2-环境变量配置)
3. [定时任务配置](#3-定时任务配置)
4. [枚举类型定义](#4-枚举类型定义)
5. [命名规范](#5-命名规范)
6. [业务常量](#6-业务常量)
7. [时间与时区](#7-时间与时区)
8. [队列与任务](#8-队列与任务)
9. [API路由约定](#9-api路由约定)
10. [模板路径约定](#10-模板路径约定)

---

## 1. 数据库约定

### 1.1 表名清单

| 表名 | 说明 | 主要用途 | 状态 |
|------|------|---------|------|
| `sources` | 信息源表 | 存储RSS/网站信息源配置 | ✅ 已实现 |
| `articles` | 文章表 | 存储采集的文章原文 | ✅ 已实现 |
| `extraction_queue` | 抽取队列表 | LLM抽取任务队列 | ✅ 已实现 |
| `extraction_items` | 抽取结果表 | 存储抽取的事实和观点 | ✅ 已实现 |
| `reports` | 报告表 | 存储每日生成的报告 | ✅ 已实现 |
| `report_recipients` | 收件人/白名单表 | 邮件收件人和登录白名单 | ✅ 已实现 |
| `delivery_log` | 投递日志表 | 邮件发送记录 | ✅ 已实现 |
| `provider_usage` | Provider使用统计表 | LLM调用费用统计 | ✅ 已实现 |
| `users` | 用户表 | 登录用户信息 | 🔄 阶段二 |
| `user_preferences` | 用户偏好表 | 用户自定义提示词模板 | 🔄 阶段二 |
| `watchlist_rules` | 关注清单表 | 关注的来源/关键词 | 🔄 阶段二 |
| `blocklist_rules` | 黑名单表 | 屏蔽的来源/关键词 | 🔄 阶段二 |
| `report_notes` | 报告备注表 | 运营人员添加的备注 | 🔄 阶段二 |
| `system_settings` | 系统设置表 | 动态配置参数 | 🔄 阶段二 |
| `admin_audit_log` | 操作审计日志表 | 管理员操作记录 | 🔄 阶段二 |

### 1.2 核心表字段约定

#### `sources` 表

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `id` | Integer | PK, AUTO_INCREMENT | - | 主键 |
| `name` | String(200) | NOT NULL | - | 信息源名称 |
| `type` | Enum(SourceType) | NOT NULL | - | 类型：rss/static/dynamic |
| `url` | String(500) | NOT NULL | - | 信息源URL |
| `enabled` | Boolean | NOT NULL | `true` | 是否启用 |
| `concurrency` | Integer | NULL | `1` | 并发数 |
| `timeout_sec` | Integer | NULL | `30` | 超时秒数 |
| `parser` | String(50) | NULL | - | 解析器名称 |
| `region_hint` | Enum(RegionHint) | NULL | `未知` | 区域提示 |
| `created_at` | DateTime | NOT NULL | NOW() | 创建时间 |
| `updated_at` | DateTime | NOT NULL | NOW() | 更新时间 |

**索引**：
- 主键索引：`id`

---

#### `articles` 表

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `id` | Integer | PK, AUTO_INCREMENT | - | 主键 |
| `source_id` | Integer | FK(sources.id), NOT NULL | - | 信息源ID |
| `title` | String(500) | NOT NULL | - | 文章标题 |
| `url` | String(1000) | UNIQUE, NOT NULL | - | 文章URL（去重键） |
| `published_at` | DateTime | NULL | - | 发布时间 |
| `fetched_at` | DateTime | NOT NULL | NOW() | 采集时间 |
| `content_text` | Text | NULL | - | 文章正文（纯文本） |
| `content_len` | Integer | NULL | `0` | 正文长度（字符数） |
| `section` | String(100) | NULL | - | 文章分类 |
| `region_tag` | String(20) | NULL | - | 区域标签 |
| `lang` | String(10) | NULL | `zh` | 语言代码 |
| `simhash` | BigInteger | NULL | - | SimHash去重指纹 |
| `canonical_url` | String(1000) | NULL | - | 规范化URL |
| `dedup_key` | String(200) | NULL | - | 去重键（标题+时间） |
| `processing_status` | Enum(ProcessingStatus) | NOT NULL | `raw` | 处理状态 |
| `created_at` | DateTime | NOT NULL | NOW() | 创建时间 |
| `updated_at` | DateTime | NOT NULL | NOW() | 更新时间 |

**索引**：
- 主键索引：`id`
- 唯一索引：`url`
- 普通索引：`published_at`, `processing_status`, `simhash`

---

#### `extraction_items` 表

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `id` | Integer | PK, AUTO_INCREMENT | - | 主键 |
| `article_id` | Integer | FK(articles.id), NOT NULL | - | 文章ID |
| `fact` | Text | NOT NULL | - | 事实描述（必选） |
| `opinion` | Text | NULL | - | 观点描述（可选） |
| `region` | Enum(Region) | NOT NULL | - | 区域：国内/国外/未知 |
| `layer` | Enum(Layer) | NOT NULL | - | 层级：金融政策监管/金融经济/金融大模型技术/金融科技应用/未知 |
| `evidence_span` | Text | NULL | - | 证据片段（原文引用） |
| `confidence` | Float | NOT NULL | - | 置信度（0.0-1.0） |
| `finance_relevance` | Float | NULL | `1.0` | 金融相关性（0.0-1.0） |
| `created_at` | DateTime | NOT NULL | NOW() | 创建时间 |
| `updated_at` | DateTime | NOT NULL | NOW() | 更新时间 |

**索引**：
- 主键索引：`id`
- 普通索引：`article_id`, `(region, layer)`, `confidence`, `finance_relevance`

**业务约束**：
- `confidence` 范围：0.0 - 1.0
- `finance_relevance` 范围：0.0 - 1.0
- 筛选阈值：`confidence >= 0.6`（可配置）

---

#### `reports` 表

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `id` | Integer | PK, AUTO_INCREMENT | - | 主键 |
| `report_date` | Date | UNIQUE, NOT NULL | - | 报告日期（一天一份） |
| `version` | String(20) | NULL | `1.0` | 版本号 |
| `overview_summary` | Text | NULL | - | 总览摘要（150-250字） |
| `sections_json` | JSON | NULL | - | 分区统计（JSON格式） |
| `html_body` | Text | NOT NULL | - | 邮件正文HTML |
| `html_attachment` | Text | NOT NULL | - | 附件HTML（全量） |
| `build_meta` | JSON | NULL | - | 构建元数据 |
| `build_ms` | Integer | NULL | `0` | 构建耗时（毫秒） |
| `created_at` | DateTime | NOT NULL | NOW() | 创建时间 |
| `updated_at` | DateTime | NOT NULL | NOW() | 更新时间 |

**索引**：
- 主键索引：`id`
- 唯一索引：`report_date`

---

#### `report_recipients` 表

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `id` | Integer | PK, AUTO_INCREMENT | - | 主键 |
| `email` | String(200) | UNIQUE, NOT NULL | - | 邮箱地址 |
| `display_name` | String(100) | NULL | - | 显示名称 |
| `type` | Enum(RecipientType) | NOT NULL | `recipient` | 类型：whitelist/recipient |
| `enabled` | Boolean | NOT NULL | `true` | 是否启用 |
| `created_at` | DateTime | NOT NULL | NOW() | 创建时间 |
| `updated_at` | DateTime | NOT NULL | NOW() | 更新时间 |

**索引**：
- 主键索引：`id`
- 唯一索引：`email`
- 普通索引：`(type, enabled)`

**说明**：
- `type=whitelist`：可登录前端的白名单用户
- `type=recipient`：仅接收邮件的收件人

---

### 1.3 数据库连接约定

- **连接URL格式**：`postgresql://<user>:<password>@<host>:<port>/<database>`
- **默认用户**：`fin_user`
- **默认密码**：`fin_pass`（生产环境必须修改）
- **默认数据库名**：`fin_daily_report`
- **默认端口**：`5432`
- **连接池大小**：5（开发环境），20（生产环境）
- **字符集**：`UTF-8`
- **时区**：`Asia/Shanghai`

---

## 2. 环境变量配置

### 2.1 配置文件位置

- **开发环境**：`.env`（项目根目录，不提交Git）
- **示例文件**：`.env.example`（提交Git，供参考）
- **生产环境**：通过环境变量或Docker注入

### 2.2 必需配置（无默认值）

| 变量名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `DATABASE_URL` | str | PostgreSQL连接URL | `postgresql://fin_user:fin_pass@localhost:5432/fin_daily_report` |
| `REDIS_URL` | str | Redis连接URL | `redis://localhost:6379/0` |
| `PROVIDER_DEEPSEEK_API_KEY` | str | DeepSeek API密钥 | `sk-xxx` |
| `PROVIDER_QWEN_API_KEY` | str | Qwen API密钥 | `sk-xxx` |
| `SMTP_USER` | str | SMTP发件人邮箱 | `your_email@163.com` |
| `SMTP_PASS` | str | SMTP授权码 | `your_auth_code` |

### 2.3 可选配置（有默认值）

#### 基础配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `TZ` | str | `Asia/Shanghai` | 时区 |
| `ENV` | str | `development` | 环境：development/production |

#### LLM Provider 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `PROVIDER_DEEPSEEK_BASE_URL` | str | `https://api.deepseek.com/v1` | DeepSeek API地址 |
| `PROVIDER_DEEPSEEK_MODEL` | str | `deepseek-chat` | DeepSeek模型名称 |
| `PROVIDER_QWEN_BASE_URL` | str | `https://dashscope.aliyuncs.com/compatible-mode/v1` | Qwen API地址 |
| `PROVIDER_QWEN_MODEL` | str | `qwen-max` | Qwen模型名称 |

#### 采集配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `CRAWL_CONCURRENCY_RSS` | int | `10` | RSS采集并发数（开发环境可调高） |
| `CRAWL_CONCURRENCY_WEB` | int | `2` | 网站采集并发数（生产环境控制在2） |
| `CRAWL_TIMEOUT_SEC` | int | `30` | 采集超时（秒） |
| `CRAWL_RETRY_TIMES` | int | `3` | 采集重试次数 |

#### LLM 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `LLM_TIMEOUT_SEC` | int | `90` | LLM调用超时（秒） |
| `LLM_RETRIES` | int | `2` | LLM调用重试次数 |
| `LLM_CHUNK_BUDGET` | float | `0.7` | 分块预算比例（70%） |
| `LLM_CHUNK_OVERLAP_CHARS` | int | `200` | 分块重叠字符数 |
| `LLM_MAX_CHUNKS_PER_ARTICLE` | int | `8` | 单篇文章最大分块数 |
| `LLM_LONGFORM_STRATEGY` | str | `summary_then_extract` | 长文策略 |
| `LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING` | bool | `false` | 是否允许并行处理文章 |

#### 报告配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `REPORT_TOPN` | int | `5` | 每区TopN条目数 |
| `CONFIDENCE_THRESHOLD` | float | `0.6` | 置信度阈值（过滤） |
| `MIN_CONTENT_LEN` | int | `120` | 最小内容长度（过滤） |
| `ATTACHMENT_MAX_ITEMS` | int | `500` | 附件最大条目数 |
| `REPORT_USE_LLM_SECTIONS` | bool | `false` | 是否使用LLM生成分区报告 |
| `REPORT_LLM_MODEL_LIMIT` | int | `64000` | LLM模型输入限制（token） |
| `REPORT_LLM_BUDGET` | float | `0.7` | LLM可用预算比例 |
| `REPORT_SECTION_MAX_ITEMS_PER_CHUNK` | int | `20` | 每次LLM调用最大处理条目数 |

#### 邮件配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `SMTP_HOST` | str | `smtp.163.com` | SMTP服务器地址 |
| `SMTP_PORT` | int | `465` | SMTP端口（SSL） |
| `MAIL_BATCH_LIMIT` | int | `50` | 单封邮件最大收件人数 |
| `MAIL_RATE_LIMIT_PER_SEC` | float | `1.0` | 发送速率限制（封/秒） |
| `MAIL_WINDOW_START` | str | `06:05` | 发送窗口起始时间 |
| `MAIL_WINDOW_END` | str | `06:20` | 发送窗口结束时间 |

---

## 3. 定时任务配置

### 3.1 Celery 定时任务

#### 每日报告生成任务

- **任务名称**：`src.tasks.orchestrator.run_daily_report`
- **Cron表达式**：`crontab(hour=5, minute=30)`
- **执行时间**：每天 **05:30**（Asia/Shanghai时区）
- **说明**：提前到05:30启动，确保06:20前完成发送

**时间规划**：
```
05:30  启动任务
  ├── 05:30-05:45  采集阶段（RSS + 静态网站）
  ├── 05:45-06:00  抽取阶段（LLM处理）
  ├── 06:00-06:05  成稿阶段（生成报告）
  └── 06:05-06:20  投递阶段（邮件发送）
```

### 3.2 Celery 队列配置

| 队列名 | 路由规则 | 说明 |
|--------|---------|------|
| `crawl` | `src.tasks.crawl_tasks.*` | 采集任务队列 |
| `extract` | `src.tasks.extract_tasks.*` | 抽取任务队列 |
| `report` | `src.tasks.report_tasks.*` | 报告生成队列 |
| `mail` | `src.tasks.mail_tasks.*` | 邮件发送队列 |

### 3.3 任务时间限制

| 配置项 | 值（秒） | 说明 |
|--------|---------|------|
| `task_time_limit` | `600` | 任务硬超时（10分钟） |
| `task_soft_time_limit` | `540` | 任务软超时（9分钟） |
| `result_expires` | `3600` | 任务结果过期时间（1小时） |

---

## 4. 枚举类型定义

### 4.1 信息源类型 `SourceType`

| 枚举值 | Python值 | 数据库值 | 说明 |
|--------|---------|---------|------|
| RSS | `"rss"` | `rss` | RSS订阅源 |
| STATIC | `"static"` | `static` | 静态网页（requests/Scrapy） |
| DYNAMIC | `"dynamic"` | `dynamic` | 动态网页（Playwright） |

**使用位置**：`sources.type`

---

### 4.2 区域提示 `RegionHint`

| 枚举值 | Python值 | 数据库值 | 说明 |
|--------|---------|---------|------|
| DOMESTIC | `"国内"` | `国内` | 国内信息源 |
| FOREIGN | `"国外"` | `国外` | 国外信息源 |
| UNKNOWN | `"未知"` | `未知` | 未知地区 |

**使用位置**：`sources.region_hint`

---

### 4.3 处理状态 `ProcessingStatus`

| 枚举值 | Python值 | 数据库值 | 说明 |
|--------|---------|---------|------|
| RAW | `"raw"` | `raw` | 原始（未处理） |
| QUEUED | `"queued"` | `queued` | 已入队 |
| RUNNING | `"running"` | `running` | 处理中 |
| DONE | `"done"` | `done` | 完成 |
| FAILED | `"failed"` | `failed` | 失败 |
| PARTIAL | `"partial"` | `partial` | 部分成功 |

**使用位置**：`articles.processing_status`

---

### 4.4 区域标签 `Region`

| 枚举值 | Python值 | 数据库值 | 中文显示 |
|--------|---------|---------|---------|
| DOMESTIC | `"国内"` | `国内` | 国内 |
| FOREIGN | `"国外"` | `国外` | 国外 |
| UNKNOWN | `"未知"` | `未知` | 未知 |

**使用位置**：`extraction_items.region`

---

### 4.5 层级分类 `Layer`

| 枚举值 | Python值 | 数据库值 | 中文显示 |
|--------|---------|---------|---------|
| FINANCIAL_POLICY | `"金融政策监管"` | `金融政策监管` | 金融政策监管 |
| FINANCIAL_ECONOMY | `"金融经济"` | `金融经济` | 金融经济 |
| FINTECH_AI | `"金融大模型技术"` | `金融大模型技术` | 金融大模型技术 |
| FINTECH | `"金融科技应用"` | `金融科技应用` | 金融科技应用 |
| UNKNOWN | `"未知"` | `未知` | 未知 |

**使用位置**：`extraction_items.layer`

**层级定义**：
- **金融政策监管**：央行政策、金融监管、资本市场监管、金融法规
- **金融经济**：股市、债市、汇市、投融资、IPO、并购、金融机构业绩
- **金融大模型技术**：大模型技术进展、模型发布、性能提升
- **金融科技应用**：AI/大数据/区块链在金融场景的应用

---

### 4.6 队列状态 `QueueStatus`

| 枚举值 | Python值 | 数据库值 | 说明 |
|--------|---------|---------|------|
| QUEUED | `"queued"` | `queued` | 队列中 |
| RUNNING | `"running"` | `running` | 处理中 |
| DONE | `"done"` | `done` | 完成 |
| FAILED | `"failed"` | `failed` | 失败 |

**使用位置**：`extraction_queue.status`

---

### 4.7 收件人类型 `RecipientType`

| 枚举值 | Python值 | 数据库值 | 说明 |
|--------|---------|---------|------|
| WHITELIST | `"whitelist"` | `whitelist` | 白名单用户（可登录） |
| RECIPIENT | `"recipient"` | `recipient` | 普通收件人（仅接收邮件） |

**使用位置**：`report_recipients.type`

---

### 4.8 投递状态 `DeliveryStatus`

| 枚举值 | Python值 | 数据库值 | 说明 |
|--------|---------|---------|------|
| OK | `"ok"` | `ok` | 发送成功 |
| FAILED | `"failed"` | `failed` | 发送失败 |
| PARTIAL | `"partial"` | `partial` | 部分成功 |

**使用位置**：`delivery_log.status`

---

## 5. 命名规范

### 5.1 Python 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块名 | 小写+下划线 | `crawl_tasks.py` |
| 类名 | 大驼峰（PascalCase） | `ArticleCrawler` |
| 函数名 | 小写+下划线 | `extract_article()` |
| 变量名 | 小写+下划线 | `article_id` |
| 常量名 | 大写+下划线 | `MAX_RETRY_TIMES` |
| 私有方法 | 前缀单下划线 | `_internal_method()` |
| Celery任务 | 后缀`_task` | `crawl_rss_task` |
| 枚举类 | 大驼峰 | `SourceType` |
| 枚举值 | 大写+下划线 | `SourceType.RSS` |

### 5.2 数据库命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 表名 | 小写+下划线，复数 | `articles` |
| 字段名 | 小写+下划线 | `created_at` |
| 索引名 | `idx_表名_字段名` | `idx_articles_url` |
| 外键名 | 默认（SQLAlchemy生成） | `articles_source_id_fkey` |
| 枚举类型名 | 小写 | `sourcetype` |

### 5.3 API 路由命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 列表查询 | `GET /资源复数` | `GET /reports` |
| 单条查询 | `GET /资源复数/{id}` | `GET /reports/2025-11-08` |
| 创建 | `POST /资源复数` | `POST /preferences` |
| 更新 | `POST /资源复数/{id}` | `POST /admin/sources/1` |
| 删除 | `POST /资源复数/{id}/delete` | `POST /preferences/1/delete` |
| 自定义动作 | `POST /资源复数/动作` | `POST /auth/otp/request` |

---

## 6. 业务常量

### 6.1 内容过滤阈值

| 常量名 | 值 | 说明 | 配置位置 |
|--------|---|------|---------|
| `CONFIDENCE_THRESHOLD` | `0.6` | 置信度阈值（筛选事实观点） | 环境变量 |
| `MIN_CONTENT_LEN` | `120` | 最小内容长度（字符数） | 环境变量 |
| `FINANCE_RELEVANCE_POLICY_MIN` | `0.4` | 金融政策监管层级最低相关性 | 代码常量 |
| `FINANCE_RELEVANCE_AI_MIN` | `0.2` | 金融大模型技术层级最低相关性 | 代码常量 |

### 6.2 时间范围常量

| 常量名 | 值 | 说明 |
|--------|---|------|
| `CRAWL_TIME_RANGE_HOURS` | `24` | 采集时间范围（过去24小时） |
| `OTP_TTL_SECONDS` | `600` | OTP验证码有效期（10分钟） |
| `OTP_RESEND_INTERVAL` | `60` | OTP重发间隔（60秒） |
| `JWT_EXPIRE_DAYS` | `7` | JWT Token有效期（7天） |
| `WORDCLOUD_CACHE_TTL` | `86400` | 词云缓存时间（24小时） |

### 6.3 并发与限制常量

| 常量名 | 值 | 说明 |
|--------|---|------|
| `CRAWL_CONCURRENCY_RSS` | `10` | RSS并发数（开发环境） |
| `CRAWL_CONCURRENCY_WEB` | `2` | 网站并发数（生产环境） |
| `LLM_MAX_CHUNKS_PER_ARTICLE` | `8` | 单篇文章最大分块数 |
| `MAIL_BATCH_LIMIT` | `50` | 单封邮件最大收件人数 |
| `MAIL_RATE_LIMIT_PER_SEC` | `1.0` | 邮件发送速率（封/秒） |
| `USER_PREFERENCES_MAX` | `5` | 用户最多偏好模板数 |
| `ATTACHMENT_MAX_ITEMS` | `500` | 附件最多包含条目数 |

### 6.4 报告结构常量

| 常量名 | 值 | 说明 |
|--------|---|------|
| `REPORT_TOPN` | `5` | 每区域/层级TopN条目数 |
| `OVERVIEW_SUMMARY_MIN_LEN` | `150` | 总览摘要最小长度（字符） |
| `OVERVIEW_SUMMARY_MAX_LEN` | `250` | 总览摘要最大长度（字符） |

**报告分区结构**（2×4=8个分区）：
```
国内 × (金融政策监管, 金融经济, 金融大模型技术, 金融科技应用)
国外 × (金融政策监管, 金融经济, 金融大模型技术, 金融科技应用)
```

---

## 7. 时间与时区

### 7.1 时区约定

- **统一时区**：`Asia/Shanghai`（UTC+8）
- **环境变量**：`TZ=Asia/Shanghai`
- **数据库存储**：**不含时区**的 `DateTime`（Naive Datetime）
- **Celery时区**：`timezone="Asia/Shanghai", enable_utc=False`

### 7.2 时间字段命名

| 字段名 | 说明 | 类型 |
|--------|------|------|
| `created_at` | 创建时间 | DateTime |
| `updated_at` | 更新时间 | DateTime |
| `published_at` | 发布时间（文章） | DateTime |
| `fetched_at` | 采集时间 | DateTime |
| `sent_at` | 发送时间（邮件） | DateTime |
| `processing_started_at` | 处理开始时间 | DateTime |
| `processing_finished_at` | 处理结束时间 | DateTime |
| `last_login_at` | 最后登录时间 | DateTime |

### 7.3 关键时间点

| 时间点 | 说明 |
|--------|------|
| `05:30` | 定时任务启动时间 |
| `06:05` | 邮件发送窗口起始 |
| `06:20` | 邮件发送窗口结束（验收目标） |

---

## 8. 队列与任务

### 8.1 Celery 任务清单

| 任务模块 | 任务名 | 队列 | 说明 |
|---------|--------|------|------|
| `crawl_tasks` | `crawl_rss_task` | `crawl` | 采集单个RSS源 |
| `crawl_tasks` | `crawl_static_task` | `crawl` | 采集单个静态网站 |
| `extract_tasks` | `extract_article_task` | `extract` | 抽取单篇文章 |
| `extract_tasks` | `run_extraction_batch` | `extract` | 批量抽取文章 |
| `report_tasks` | `build_report_task` | `report` | 生成报告 |
| `mail_tasks` | `send_report_task` | `mail` | 发送报告邮件 |
| `orchestrator` | `run_daily_report` | `default` | 每日报告编排器 |

### 8.2 任务依赖关系

```
run_daily_report (编排器)
  ├── 阶段1: 采集 (crawl_rss_task, crawl_static_task) [并行]
  │     └── 输出: articles
  ├── 阶段2: 抽取 (run_extraction_batch) [串行]
  │     └── 输出: extraction_items
  ├── 阶段3: 成稿 (build_report_task) [串行]
  │     └── 输出: reports
  └── 阶段4: 投递 (send_report_task) [串行]
        └── 输出: delivery_log
```

### 8.3 Redis 键命名约定

| 键模式 | TTL | 说明 |
|--------|-----|------|
| `otp:{email}` | 600s | OTP验证码 |
| `otp_resend:{email}` | 60s | OTP重发间隔锁 |
| `otp_attempts:{email}` | 600s | OTP尝试次数 |
| `wc:{scope}:{date}:{width}x{height}` | 86400s | 词云图片缓存 |
| `celery-task-meta-{task_id}` | 3600s | Celery任务结果 |

---

## 9. API路由约定

### 9.1 认证路由

| 路由 | 方法 | 说明 |
|------|------|------|
| `/login` | GET | 登录页面 |
| `/auth/otp/request` | POST | 请求OTP验证码 |
| `/auth/otp/verify` | POST | 验证OTP并登录 |
| `/auth/admin/login` | POST | 管理员密码登录 |
| `/auth/logout` | POST | 登出 |

### 9.2 报告浏览路由

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页（重定向到/reports） |
| `/reports` | GET | 报告列表页 |
| `/reports/{date}` | GET | 报告详情页 |
| `/api/reports/{date}/items` | GET | 获取报告条目（AJAX） |
| `/assets/attachment/{date}.html` | GET | 下载附件 |

### 9.3 统计与词云路由

| 路由 | 方法 | 说明 |
|------|------|------|
| `/stats/wordcloud` | GET | 生成词云图片 |
| `/stats/summary` | GET | 统计摘要 |

### 9.4 用户偏好路由

| 路由 | 方法 | 说明 |
|------|------|------|
| `/preferences` | GET | 偏好列表页 |
| `/preferences` | POST | 创建/更新偏好 |
| `/preferences/{id}/delete` | POST | 删除偏好 |
| `/preferences/set-daily-prompt` | POST | 设置当日全局提示词 |

### 9.5 管理员路由

| 路由 | 方法 | 说明 |
|------|------|------|
| `/admin/sources` | GET | 信息源管理页 |
| `/admin/sources/{id}` | POST | 更新信息源 |
| `/admin/recipients` | GET | 收件人管理页 |
| `/admin/recipients` | POST | 添加收件人 |
| `/admin/recipients/{id}/delete` | POST | 删除收件人 |
| `/admin/whitelist` | GET | 白名单管理页 |
| `/admin/settings` | GET/POST | 系统设置页 |
| `/admin/audit` | GET | 操作审计页 |
| `/admin/status` | GET | 系统状态页 |
| `/admin/watchlist` | GET/POST | 关注清单管理 |
| `/admin/blocklist` | GET/POST | 黑名单管理 |
| `/admin/notes` | GET/POST | 报告备注管理 |

### 9.6 健康检查路由

| 路由 | 方法 | 说明 |
|------|------|------|
| `/healthz` | GET | 完整健康检查 |
| `/healthz/simple` | GET | 简单健康检查 |
| `/healthz/database` | GET | 数据库健康检查 |
| `/healthz/redis` | GET | Redis健康检查 |
| `/healthz/celery` | GET | Celery健康检查 |

---

## 10. 模板路径约定

### 10.1 邮件模板

| 模板文件 | 路径 | 说明 |
|---------|------|------|
| 邮件正文模板 | `src/composer/templates/email_body.html` | 报告正文HTML |
| 附件模板 | `src/composer/templates/attachment.html` | 全量事实观点HTML |

### 10.2 前端页面模板（阶段二）

| 模板分类 | 路径 | 说明 |
|---------|------|------|
| 基础布局 | `src/web/templates/base.html` | 所有页面的基础布局 |
| 认证 | `src/web/templates/auth/login.html` | 登录页 |
| 报告 | `src/web/templates/reports/list.html` | 报告列表 |
| 报告 | `src/web/templates/reports/detail.html` | 报告详情 |
| 统计 | `src/web/templates/stats/wordcloud.html` | 词云展示 |
| 统计 | `src/web/templates/stats/summary.html` | 统计摘要 |
| 偏好 | `src/web/templates/preferences/index.html` | 用户偏好 |
| 管理员 | `src/web/templates/admin/*.html` | 管理页面 |
| 组件 | `src/web/templates/components/*.html` | 可复用组件 |

---

## 附录A：完整环境变量清单

```bash
# ========== 基础配置 ==========
TZ=Asia/Shanghai
ENV=development

# ========== 数据库 ==========
DATABASE_URL=postgresql://fin_user:fin_pass@localhost:5432/fin_daily_report

# ========== Redis ==========
REDIS_URL=redis://localhost:6379/0

# ========== LLM Provider - DeepSeek ==========
PROVIDER_DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
PROVIDER_DEEPSEEK_API_KEY=sk-xxx
PROVIDER_DEEPSEEK_MODEL=deepseek-chat

# ========== LLM Provider - Qwen ==========
PROVIDER_QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PROVIDER_QWEN_API_KEY=sk-xxx
PROVIDER_QWEN_MODEL=qwen-max

# ========== 采集配置 ==========
CRAWL_CONCURRENCY_RSS=10
CRAWL_CONCURRENCY_WEB=2
CRAWL_TIMEOUT_SEC=30
CRAWL_RETRY_TIMES=3

# ========== LLM 配置 ==========
LLM_TIMEOUT_SEC=90
LLM_RETRIES=2
LLM_CHUNK_BUDGET=0.7
LLM_CHUNK_OVERLAP_CHARS=200
LLM_MAX_CHUNKS_PER_ARTICLE=8
LLM_LONGFORM_STRATEGY=summary_then_extract
LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING=false

# ========== 报告配置 ==========
REPORT_TOPN=5
CONFIDENCE_THRESHOLD=0.6
MIN_CONTENT_LEN=120
ATTACHMENT_MAX_ITEMS=500
REPORT_USE_LLM_SECTIONS=false
REPORT_LLM_MODEL_LIMIT=64000
REPORT_LLM_BUDGET=0.7
REPORT_SECTION_MAX_ITEMS_PER_CHUNK=20

# ========== 邮件配置 ==========
SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USER=your_email@163.com
SMTP_PASS=your_auth_code
MAIL_BATCH_LIMIT=50
MAIL_RATE_LIMIT_PER_SEC=1.0
MAIL_WINDOW_START=06:05
MAIL_WINDOW_END=06:20

# ========== 阶段二：JWT 配置 ==========
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# ========== 阶段二：OTP 配置 ==========
OTP_TTL_SECONDS=600
OTP_RESEND_INTERVAL=60
OTP_MAX_ATTEMPTS=5

# ========== 阶段二：前端配置 ==========
THEME_PRIMARY_COLOR=#1d4ed8
STOPWORDS_PATH=./config/stopwords_zh.txt

# ========== 阶段二：安全配置 ==========
ENABLE_CSRF=false
ENABLE_RATE_LIMIT=false
ALLOWED_HOSTS=*
CORS_ORIGINS=*

# ========== 阶段二：缓存配置 ==========
WORDCLOUD_CACHE_TTL=86400
```

---

## 附录B：数据库枚举值快速参考

| 枚举类型 | 可选值 | 使用位置 |
|---------|--------|---------|
| `SourceType` | `rss`, `static`, `dynamic` | `sources.type` |
| `RegionHint` | `国内`, `国外`, `未知` | `sources.region_hint` |
| `ProcessingStatus` | `raw`, `queued`, `running`, `done`, `failed`, `partial` | `articles.processing_status` |
| `Region` | `国内`, `国外`, `未知` | `extraction_items.region` |
| `Layer` | `金融政策监管`, `金融经济`, `金融大模型技术`, `金融科技应用`, `未知` | `extraction_items.layer` |
| `QueueStatus` | `queued`, `running`, `done`, `failed` | `extraction_queue.status` |
| `RecipientType` | `whitelist`, `recipient` | `report_recipients.type` |
| `DeliveryStatus` | `ok`, `failed`, `partial` | `delivery_log.status` |

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| v1.0 | 2025-11-08 | 初始版本，包含阶段一所有参数约定 |

---

**文档维护说明**：
- 每次新增配置项、数据库表、枚举类型时，必须同步更新本文档
- 所有参数默认值的修改，必须在本文档中记录变更历史
- 环境变量的新增/删除，需同步更新 `.env.example` 文件
