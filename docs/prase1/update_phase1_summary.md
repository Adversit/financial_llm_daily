# 阶段一更新说明

本文件总结了当前阶段（“任务编排与调度”“系统支撑模块”“测试任务”）的主要更新，以便后续开发与验收时参考。

## 任务编排与调度
- `src/tasks/celery_app.py`  
  - 完成 Celery 实例化与配置，包含任务序列化、时区、路由、结果过期、重试策略等。  
  - 配置 Celery Beat 定时任务 `daily-report-06:00`，每日 06:00 触发 `run_daily_report`。
- `src/tasks/orchestrator.py`  
  - 实现端到端编排：采集（并发）→ 抽取 → 成稿 → 邮件发送。  
  - 提供 `run_crawl_only`、`run_extraction_only` 等拆分任务，便于调试。  
  - 增强日志记录（开始/结束、耗时、任务数量）。
- `src/cli/run_once.py`  
  - 提供命令行入口，可通过 `--step` 执行单步骤或完整流程。  
  - 修复 `send` 步骤的 Celery 导入及日期解析，支持同步测试模式。

## 系统支撑模块
- `src/config/settings.py`  
  - 使用 `pydantic-settings` 管理配置，覆盖数据库、Redis、LLM、采集、报告、邮件等参数，默认读取 `.env`。
- `src/utils/logger.py`  
  - 基于 `loguru` 的统一日志配置，输出到控制台与日滚动文件，并提供性能日志、任务进度辅助函数。
- `src/api/routes/health.py`  
  - 健康检查端点 `/healthz`，检测数据库、Redis、Celery Worker、磁盘空间；额外提供 `/healthz/simple` 等细分接口。
- `src/utils/bootstrap.py`  
  - 启动自检，包括环境变量、数据库连接/表结构、Redis、目录、LLM Provider、SMTP 等检查，可选择严格模式。
- `src/api/main.py`  
  - 切换到 FastAPI `lifespan` 机制处理启动/关闭日志，兼容新版 FastAPI。

## 邮件与 NLP 支撑
- `src/tasks/mail_tasks.py`  
  - 支持批量分发、速率限制、失败重试；新增 `scripts/seed_test_data.py` 用于导入测试信息源与收件人。  
  - `src/mailer/smtp_client.py`、`retry_handler.py`、`batcher.py` 等模块完善重试、黑名单处理。
- `src/nlp` 模块  
  - `chunking.py`、`provider_router.py`、`merger.py` 等实现文本分块、LLM Provider 回退、抽取结果合并去重。

## 信息源采集（Static/RSS）
- `src/crawlers/base.py`  
  - 允许注入 `parser` 标识，新增时间归一化逻辑，避免带时区时间与 UTC 比较时报错。
- `src/crawlers/static_crawler.py`  
  - 引入 `SiteRule` 站点配置，当前内置适配以下静态信息源：  
    `openai.com`、`blog.google`、`anthropic.com`、`x.ai`、`nvidia.com`、`microsoft.com`、`finextra.com`、`savanta.com`，以及将 `idc.com` 自动切换到 RSS 模式。  
  - 支持自定义列表选择器、允许/禁止路径、发布时间解析（含 JSON-LD）与 canonical 链接；自动忽略 `.xml` 链接以规避 RSS 警告。  
  - 若新增站点，可在 `SITE_RULES` 中添加配置或为信息源记录 `parser` 字段引用现有规则。
- `src/tasks/crawl_tasks.py`  
  - 构建爬虫时携带 `parser` 信息，静态站点按规则选择 HTML 或 RSS 模式。
- `scripts/test_static_sources.py`  
  - 手动测试脚本（默认涵盖上述 9 个 Static 信息源），示例：  
    `poetry run python scripts/test_static_sources.py --sources openai.com nvidia.com --since-hours 48`。  
  - 输出每篇文章标题/发布时间/链接，便于快速验证；在受限网络环境（如公司代理阻断）下需自行配置出口网络。

### Static 信息源注意事项
- **OpenAI** (`parser=openai.com`)：按栏目页采集，遇到 `403` 时脚本会自动重试；环境若屏蔽外网需手动配置代理。  
- **Google Blog** (`blog.google`)：列表页为 SPA，需确保访问根域名可达；无法访问时同样会抛出 `ProxyError`。  
- **Anthropic / xAI / Finextra / Savanta**：页面结构稳定，若站点调整 CSS class，可在 `SITE_RULES` 中追加选择器。  
- **NVIDIA News** (`nvidia.com`)：已切换到 `https://nvidianews.nvidia.com/news`；有时文章较旧而被时间过滤掉，可通过 `--since-hours` 放宽窗口。  
- **Microsoft AI Blog** (`microsoft.com`)：入口为 `https://blogs.microsoft.com/ai/`；若出现 404，通常是站点跳转导致，需要刷新站点规则。  
- **IDC** (`idc.com`)：采用 RSS 回退，沿用现有 `RSSCrawler` 逻辑，无需额外适配。  
- **WeChat RSS**：既有 wechatrss 源表现稳定，本阶段未修改；建议继续沿用现有 RSS 管道。
- 新增信息源时：  
  1. 在 `SITE_RULES` 增加缩写配置（或在数据库 `parser` 字段指定现有键）；  
  2. 如需单独脚本，可参考 `scripts/test_static_sources.py` 的调用方式输出结构一致的列表（字段包含 `title`、`url`、`published_at`、`content_text`、`source_name`）。  
  3. 确认 `scripts/test_static_sources.py --sources 新站点` 能返回数据后，再将源录入数据库。

## 阶段一问题记录与解决
- **发送时间窗口限制**：新增 CLI `--force` 参数与任务 `force_send` 选项，允许手动跳过窗口测试邮件发送。  
- **DeliveryLog 写入异常**：修复日志记录逻辑，去除不存在的字段（`report_date` 等），并保存 `recipients_snapshot`、`batch_no`、`message_id` 等核心信息。  
- **静态站点解析难点**：针对 OpenAI、Google Blog 等站点建立规则映射，增加 RSS 回退机制与 `.xml` 过滤，避免解析失败或时区差异导致的异常。  
- **网络可达性**：脚本会在无法连网时抛出 `ProxyError`；需在可出网环境或配置代理后再运行测试与端到端流程。

## 测试任务
- 单元测试：  
  - 新增 `tests/test_crawlers/test_rss_crawler.py`、`test_static_crawler.py`、`test_deduplicator.py`。  
  - 新增 `tests/test_nlp/test_chunking.py`、`test_provider_router.py`、`test_merger.py`。  
  - 新增 `tests/test_mailer/test_smtp_client.py` 并完善 `tests/test_mailer/test_mail_tasks.py`。  
  - 现有 `tests/test_system`、`tests/test_composer`、`tests/test_mailer/test_retry_handler.py` 等覆盖系统支撑与报告生成。
- 集成测试：  
  - `tests/test_e2e/test_modules_a_to_d.py` 模拟模块 A-D 的完整编排流程。
- 冒烟指引：  
  - 使用 CLI (`python -m src.cli.run_once --step all`) 及 Celery Worker/Beat 验证端到端。  
  - 通过 `scripts/seed_test_data.py` 导入 `tests/data/e2e_sources_and_recipients.json` 中的数据。

## 验收与运行要点
1. **环境准备**  
   - `docker-compose up -d postgres redis`  
   - `alembic upgrade head`  
   - `python scripts/seed_test_data.py`（或指定数据文件）  
   - 激活虚拟环境：`wsl` → `source .venv/bin/activate`
2. **测试执行**  
   - 单元测试：`poetry run pytest`（或按目录分组执行）  
   - 覆盖率：`poetry run pytest --cov=src --cov-report=term-missing`
3. **运行流程**  
   - 启动 Celery Worker：`celery -A src.tasks.celery_app worker --loglevel=info`  
   - 如需定时：`celery -A src.tasks.celery_app beat --loglevel=info`  
   - CLI 手动触发：`python -m src.cli.run_once --step all`
4. **健康检查与日志**  
   - FastAPI 健康检查：`http://localhost:8000/healthz`  
   - 日志输出：控制台与 `logs/app_*.log`、`logs/error_*.log`。

如需进一步扩展，可在新增模块/配置后同步更新本文件，确保文档与实现保持一致。若要生成其他文档，请在执行前与负责人确认。
