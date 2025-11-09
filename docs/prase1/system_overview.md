# 系统架构与文件概览

本文旨在帮助新成员快速了解“金融情报日报系统”的整体设计、核心流程以及代码结构。内容包括系统目标、执行链路、关键模块和文件级说明。

---

## 1. 系统目标与核心能力

- **自动采集**：定时抓取 RSS、WeChat RSS 及多家英文科技/金融资讯站点，存入标准化的文章表。
- **智能抽取**：结合 LLM 将文章内容转化为摘要事实、观点等结构化信息，并记录 Provider 使用情况。
- **报告生成**：按业务规则筛选、排序抽取结果，输出标准日报正文（HTML）及附件。
- **邮件发送**：在设定时间窗口内批量向收件人发送日报邮件，并记录投递日志。
- **编排与监控**：通过 Celery orchestrator、CLI 与 FastAPI 健康检查实现全流程调度与观测。

---

## 2. 核心执行链路（数据流程）

1. **信息源采集**  
   - Celery Beat 在每天 06:00 触发 `run_daily_report`（或 CLI 手动触发）。
   - `crawl_tasks` 根据 `sources` 表启用状态，调用 `RSSCrawler` / `StaticCrawler` / 未来的 `DynamicCrawler`。
   - 去重后写入 `articles` 表，并将待抽取的文章加入 `extraction_queue`。

2. **批量抽取**  
   - `extract_tasks.run_extraction_batch` 拉取队列，串联 `nlp.chunking` → `nlp.provider_router` → `nlp.merger`。
   - 结果写入 `extraction_items` 并更新 `articles.processing_status`，同时记录 Provider 使用情况。

3. **报告生成**  
   - `report_tasks.build_report_task` 读取当日抽取项，执行评分、TopN 筛选，构建正文与附件 HTML。
   - 报告写入 `reports` 表，保存构建时间、元数据。

4. **邮件投递**  
   - `mail_tasks.send_report_task` 检查时间窗口（支持 `force_send`），读入启用的收件人、分批发送。
   - 调用 `mailer.smtp_client` 发送邮件，借助 `retry_handler` 重试、黑名单处理；发送结果落地 `delivery_log`。

5. **监控与自检**  
   - `utils.bootstrap` 在启动时自检环境变量、数据库、Redis、LLM、SMTP 等。
   - `api/routes/health.py` 提供 `/healthz`、`/healthz/simple` 等端点供外部监控。

---

## 3. 运行入口

| 场景 | 命令/方式 | 说明 |
| ---- | --------- | ---- |
| 全流程 | `python -m src.cli.run_once --step all` | CLI 同步执行采集→抽取→报告→邮件 |
| 单步采集 | `python -m src.cli.run_once --step crawl` | 仅触发采集链路 |
| 单步抽取 | `python -m src.cli.run_once --step extract --date YYYY-MM-DD` | 指定日期重跑抽取 |
| 报告生成 | `python -m src.cli.run_once --step compose --date YYYY-MM-DD` | 重新构建日报 |
| 邮件发送 | `python -m src.cli.run_once --step send --date YYYY-MM-DD --force` | 强制跳过时间窗口发送 |
| 生产调度 | Celery Beat (`daily-report-06:00`) | 每日 06:00 自动触发 |
| 健康检查 | `http://localhost:8000/healthz` | FastAPI 健康接口 |

---

## 4. 文件夹 & 文件速览

以下涵盖仓库内所有关键文件（排除 `.claude/`、`.pytest_cache/`、`.venv/`、`.vscode/` 及其内容）。

### 根目录
- `.env` / `.env.example`：环境变量配置与模板。
- `.gitignore`：Git 忽略规则。
- `1`：临时占位文件，可自由使用。
- `README.md`：项目说明、环境搭建、运行方式。
- `alembic.ini`：Alembic 迁移配置。
- `claude.md`：与助手协作记录。
- `docker-compose.yml`：启动 Postgres + Redis。
- `htmlcov/`：覆盖率报告，`index.html` 为入口。
- `logs/`：运行日志，`app_*.log` / `error_*.log` / `performance_*.log`。
- `pyproject.toml` & `poetry.lock`：Poetry 配置与依赖锁。
- `requirements.txt`：pip 安装依赖列表。

### `docs/`（文档）
- `PRD.md`：产品需求。
- `TDD-1.md`、`TDD-2.md`、`TDD-3.md`：不同阶段的测试驱动/任务拆解文档。
- `architecture-phase1.drawio` / `dataflow-phase1.drawio`：架构 & 数据流图。
- `system_overview.md`：本文件。
- `task.md` / `task.md.bak`：阶段任务清单（及备份）。
- `update_phase1_summary.md`：阶段一改动总结与问题记录。

### `scripts/`（运维脚本）
- `seed_test_data.py`：导入测试信息源与收件人（读自 `tests/data/e2e_sources_and_recipients.json`）。
- `test_static_sources.py`：批量测试静态站点采集，支持 `--sources`、`--since-hours`。

### `src/`（核心代码）

```
src/
├── api/                # FastAPI 接口层
│   ├── __init__.py
│   ├── main.py         # FastAPI 应用入口、CORS、lifespan
│   └── routes/
│       └── health.py   # 健康检查接口
├── cli/
│   ├── __init__.py
│   └── run_once.py     # CLI 入口，支持 --step 与 --force
├── config/
│   ├── __init__.py
│   └── settings.py     # pydantic-settings 配置加载
├── crawlers/
│   ├── __init__.py
│   ├── base.py         # 采集器基类、网络重试、时间过滤
│   ├── deduplicator.py # URL + SimHash 去重
│   ├── rss_crawler.py  # RSS/Atom 信息源采集
│   ├── static_crawler.py# 静态站点采集与站点规则
│   └── text_extractor.py# 正文抽取清洗
├── db/
│   ├── __init__.py
│   ├── session.py      # SQLAlchemy 引擎与会话工厂
│   └── migrations/
│       ├── __init__.py
│       ├── env.py      # Alembic 环境配置
│       ├── script.py.mako
│       └── versions/
│           └── 20251105_2242_c89b568287b0_initial_schema.py
├── mailer/
│   ├── __init__.py
│   ├── batcher.py      # 收件人分批、限流
│   ├── retry_handler.py# 失败重试、黑名单
├── models/
│   ├── __init__.py
│   ├── base.py         # Base 类、时间戳混入
│   ├── article.py      # 文章表模型
│   ├── extraction.py   # 抽取队列/结果模型
│   ├── report.py       # 报告表模型
│   ├── delivery.py     # 收件人、投递日志、Provider 使用
│   └── source.py       # 信息源定义
├── nlp/
│   ├── __init__.py
│   ├── chunking.py     # 文章分块与降级策略
│   ├── extractor.py    # 抽取管线入口
│   ├── merger.py       # 抽取项合并/去重
│   └── provider_router.py # 多 Provider 路由与回退
├── tasks/
│   ├── __init__.py
│   ├── celery_app.py   # Celery 实例、Beat 配置
│   ├── crawl_tasks.py  # 采集任务
│   ├── extract_tasks.py# 抽取任务
│   ├── report_tasks.py # 报告生成任务
│   ├── mail_tasks.py   # 邮件发送任务（支持 force_send）
│   └── orchestrator.py # 端到端编排
└── utils/
    ├── __init__.py
    ├── bootstrap.py    # 启动自检
    ├── logger.py       # Loguru 配置
    ├── retry.py        # 网络重试装饰器
    └── time_utils.py   # 时间窗口、时区工具
```

### `tests/`（测试套件）
- `test_celery_execution.py`：Celery 任务在 eager 模式下的验证。
- `test_api/test_health_routes.py`：健康检查接口。
- `test_crawlers/test_rss_crawler.py` / `test_static_crawler.py` / `test_deduplicator.py`：采集与去重单测。
- `test_nlp/test_chunking.py` / `test_provider_router.py` / `test_merger.py`：NLP 管线单测。
- `test_composer/test_builder.py` / `test_report_tasks.py` / `test_scorer.py`：报告生成相关测试。
- `test_mailer/test_batcher.py` / `test_mail_tasks.py` / `test_retry_handler.py` / `test_smtp_client.py`：邮件发送单元测试。
- `test_system/test_bootstrap.py` / `test_logger.py`：系统工具测试。
- `test_e2e/test_modules_a_to_d.py`：端到端流程集成测试。
- `tests/data/e2e_sources_and_recipients.json`：E2E 测试使用的数据集。

---

## 5. 常见问题与注意事项

- **网络访问**：部分外部站点（OpenAI、Google Blog 等）需要可访问的外网环境；若终端受限，采集脚本会返回 `ProxyError`。
- **发送时间窗口**：生产环境默认 06:05–06:20，可通过 CLI `--force` 在测试时跳过。
- **日志位置**：终端输出与 `logs/` 文件夹同时记录；邮件发送、抽取、采集的关键轨迹均可在日志中追踪。
- **测试策略**：`pytest` 目录涵盖单元、集成、端到端测试；在变更采集逻辑或任务编排后建议运行对应用例。
- **扩展信息源**：静态站点可在 `crawlers/static_crawler.py` 的 `SITE_RULES` 中添加规则；也可通过数据库 `source.parser` 指定现有配置。

---

通过以上结构和说明，可快速定位到系统任意模块及其职责，为后续的功能扩展、问题排查或新成员入职提供清晰的指引。
