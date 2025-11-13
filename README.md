# 金融情报日报系统 v4

> 自动化完成“采集 → 抽取 → 成稿 → 邮件投递”的金融情报日报平台,目标是在每天 06:20 前产出可追溯的多源情报。

## 功能亮点

- **多源采集编排**: 支持 RSS、静态网页与 Playwright 动态渲染, `Deduplicator`+SimHash 去重, 统一写入 `articles + extraction_queue`。
- **LLM 抽取与降级策略**: `src/nlp/extractor.py` 以 DeepSeek → Qwen 回退, 配置化 chunk budget/overlap/max chunks, `calculate_llm_cost()` 追踪实际 Provider/模型消费。
- **智能成稿与附件**: `src/composer` 对事实打分排序, 生成 HTML 邮件正文 + 全量附件 (region/layer 标签、置信区间、原文链路)。
- **邮件投递与稽核**: `src/mailer` + `send_report_task` 分批节流 (≤50 人/封, 1 封/秒)、失败重试、退信入库 `delivery_log` 并可后台重发。
- **Web 管理台与权限控制**: FastAPI + Jinja2 SSR, 管理员密码登录、白名单邮箱+OTP、报告浏览、收件人/信息源/系统设置、偏好提示词等。
- **可观测性与费用洞察**: `/admin/status` 展示 PostgreSQL/Redis/Celery/Web 实时指标与 30s 刷新的 ECharts 趋势, `/admin/usage` 以真实元数据统计 DeepSeek/Qwen 费用, `/stats/wordcloud` 提供 Redis 缓存的日/周/月词云。
- **DevOps 友好**: Celery 链式编排(`group→run_extraction_batch→build_report→send_report`)、CLI(`python -m src.cli.run_once`)、`scripts/start_all.sh`、Docker Compose 和完备 PRD/TDD/STARTUP 文档。

## 核心架构

```
浏览器 ──▶ FastAPI (src/web/app.py)
                │
                ├── SQLAlchemy → PostgreSQL (sources/articles/reports/usage)
                ├── Redis 7 (缓存、任务节流、词云)
                ├── Celery Worker & Beat (src/tasks/*)
                │       └── SMTP (aiosmtplib) 发送日报
                └── LLM Providers (DeepSeek/Qwen) via src/nlp/extractor.py
```

| 目录/模块 | 说明 |
| --- | --- |
| `src/config` | Pydantic Settings, 统一 `.env` 配置与默认值 (ENV、LLM 预算、邮件节流等)。 |
| `src/crawlers` | RSS/静态采集器、爬虫基类、去重策略 (Deduplicator、SimHash)。 |
| `src/nlp` | LLM 抽取、长文分块、Provider 回退与费用统计。 |
| `src/composer` | 报告生成、评分、卡片/附件渲染模板。 |
| `src/mailer` | 邮件正文+附件拼装、批次控制、退信/重试逻辑。 |
| `src/tasks` | Celery app、采集/抽取/报告/邮件任务与 `orchestrator`。 |
| `src/web` | FastAPI 路由、Jinja2 模板、Auth/OTP、管理员后台、统计页面。 |
| `scripts` | 启/停、数据播种、调试、诊断脚本 (如 `start_all.sh`, `seed_test_data.py`)。 |
| `docs` | PRD、TDD、启动指南、架构/数据流图与更新日志。 |

### 每日调度流水线

1. **06:00** – Celery Beat 触发 `run_daily_report` (`src/tasks/orchestrator.py`), 并发采集启用信息源。
2. **06:05** – `run_extraction_batch` 依次处理 `extraction_queue`, 记录 LLM provider/模型/状态。
3. **06:10** – `build_report_task` 生成 HTML 正文与附件, 统计 TopN、总条目与耗时。
4. **06:12~06:20** – `send_report_task` 读取收件人, 分批发送邮件并写入 `delivery_log`, 可由 CLI/后台重试。

## 技术栈

- Python 3.12 / FastAPI / Uvicorn / Pydantic v2
- SQLAlchemy 2 + Alembic + PostgreSQL 15
- Redis 7 + Celery 5 + aiosmtplib
- Playwright / Trafilatura / BeautifulSoup / SimHash / jieba / wordcloud
- DeepSeek Chat & Qwen (DashScope 兼容) LLM Providers
- Jinja2 SSR、OTP 登录、JWT (HttpOnly, SameSite=Lax, 7 天)
- Docker Compose、Poetry、pytest/pytest-cov、Black/isort/mypy

## 快速开始

### 1. 环境要求
- Windows 10/11 + WSL2 (Ubuntu 20.04+) 或任意 Linux
- Python 3.11/3.12, Poetry 1.7+
- Docker & Docker Compose / docker compose plugin
- PostgreSQL 15, Redis 7 (可由 Docker 提供)
- SMTP 账号与 DeepSeek/Qwen API Key
- Playwright 依赖 (`playwright install chromium`)

### 2. 克隆仓库

```bash
git clone <repository-url>
cd Fin_daily_report/V4
```

### 3. 启动基础依赖

```bash
docker-compose up -d postgres redis
docker-compose ps
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 使用你喜欢的编辑器填充 .env
```

| 变量 | 必填 | 示例 | 说明 |
| --- | --- | --- | --- |
| `DATABASE_URL` | ✓ | `postgresql://fin_user:fin_pass@localhost:5432/fin_daily_report` | SQLAlchemy 连接串。 |
| `REDIS_URL` | ✓ | `redis://localhost:6379/0` | Celery、缓存、词云使用的 Redis。 |
| `PROVIDER_DEEPSEEK_API_KEY` | ✓ | `sk-xxxx` | DeepSeek Chat Key, Base URL/Model 可在 `.env` 覆盖。 |
| `PROVIDER_QWEN_API_KEY` | ✓ | `sk-xxxx` | Qwen 兼容模式 Key, 作为 LLM 回退。 |
| `SMTP_HOST` / `SMTP_PORT` | ✓ | `smtp.163.com` / `465` | SSL SMTP, 可换企业邮。 |
| `SMTP_USER` / `SMTP_PASS` | ✓ | `user@163.com` / 授权码 | 邮件投递身份。 |
| `JWT_SECRET_KEY` | ✓ | `change-me` | 生产必须更换, 配合 `JWT_EXPIRE_DAYS`。 |
| `ENV` / `TZ` | 可选 | `production` / `Asia/Shanghai` | 影响日志与调度。 |
| `REPORT_TOPN`, `LLM_TIMEOUT_SEC`, `MAIL_BATCH_LIMIT`… | 可选 | 见 `src/config/settings.py` | 可由 `.env` 或后台设置覆盖。 |

> 完整可配置项请参见 `src/config/settings.py` 与管理员后台“系统设置”。

### 5. 安装 Python 依赖

```bash
# Poetry (推荐)
curl -sSL https://install.python-poetry.org | python3 -
poetry config virtualenvs.in-project true
poetry install
source .venv/bin/activate

# 或使用 pip
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 6. 初始化数据库

```bash
alembic upgrade head
python scripts/seed_test_data.py   # 可选: 导入示例信息源/收件人
```

### 7. 启动服务

```bash
# Celery Worker
celery -A src.tasks.celery_app worker --loglevel=info --concurrency=4

# Celery Beat (定时任务)
celery -A src.tasks.celery_app beat --loglevel=info

# FastAPI / Web 管理台
uvicorn src.web.app:app --host 0.0.0.0 --port 8000
```

或运行一键脚本 (WSL/Poetry 环境):

```bash
./scripts/start_all.sh
# 停止所有服务
./scripts/stop_all.sh
```

### 8. 健康检查与入口

- Web 管理台: `http://localhost:8000`
- 登录: `/login` (默认管理员 `xtyydsf` / `xtyydsf`; 普通用户使用白名单邮箱 + OTP)
- 报告: `/reports`, `/reports/{date}`
- API 文档: `/docs`, `/redoc`
- 健康检查: `/healthz`
- 管理后台: `/admin`, `/admin/status`, `/admin/usage`
- 统计/词云: `/stats/wordcloud`

## CLI / 手动执行

| 命令 | 说明 |
| --- | --- |
| `python -m src.cli.run_once --step crawl` | 仅执行采集任务。 |
| `python -m src.cli.run_once --step extract [--date YYYY-MM-DD]` | 对指定日期队列执行 LLM 抽取。 |
| `python -m src.cli.run_once --step compose [--date ...]` | 生成日报 (HTML 正文 + 附件)。 |
| `python -m src.cli.run_once --step send [--date ...] [--force]` | 发送日报, `--force` 可跳过时间窗口限制。 |
| `python -m src.cli.run_once --step all [--date ...]` | 在同进程内串行执行全流程 (调试/回测)。 |

> CLI 会将 Celery 配置为同步 (`task_always_eager`), 便于本地调试。

## Web 管理台与可视化

- **报告与偏好**: 查看日报列表/详情、下载附件、维护关键词/提示词模板、设置关注/禁用词。
- **统计 / 词云**: `/stats/wordcloud` 支持日/周/月, Redis 缓存 24h, 可自定义停用词(`SystemSetting`)。
- **管理员能力**:
  - 信息源: 启停 RSS/网站源, 调整并发/超时。
  - 收件人 & 白名单: 管理邮件订阅与 OTP 用户。
  - 系统设置: 在线修改报告阈值、爬虫并发、LLM 预算、主题色等, 并记录 `AdminAuditLog`。
  - 系统状态: PostgreSQL 连接/响应时间/数据库大小, Redis 内存/键数量/命中率, Celery 活跃任务 & 今日完成数, Web 数据统计, 内置 ECharts 趋势(30s 自动刷新)。
  - 费用统计: 基于抽取 metadata 中的 provider/model, 按 Provider/模型展示 token 用量、单价和人民币花费 (DeepSeek/Qwen)。

## 监控、日志与排障

- `logs/web.log`, `logs/celery_worker.log`, `logs/celery_beat.log`: 由 `scripts/start_all.sh` 自动创建, 便于 tail 观察。
- `docker-compose logs -f postgres|redis` 可检查依赖健康度。
- `htmlcov/index.html`: `pytest --cov` 后生成的覆盖率报告。
- 变更记录参见 `docs/update.md` (如 2025-01-09 的系统监控/费用计算增强)。

## 项目结构

```
V4/
├── src/
│   ├── api/          # FastAPI 路由入口
│   ├── cli/          # CLI 工具
│   ├── composer/     # 报告生成与模板
│   ├── config/       # Pydantic Settings
│   ├── crawlers/     # 信息源采集与去重
│   ├── db/           # 会话 & Alembic 支撑
│   ├── mailer/       # 邮件发送逻辑
│   ├── models/       # SQLAlchemy ORM
│   ├── nlp/          # LLM 抽取策略
│   ├── tasks/        # Celery 任务与 orchestrator
│   ├── utils/        # 工具函数
│   └── web/          # Web 应用、模板、静态资源
├── scripts/          # start_all、seed_test_data 等脚本
├── docs/             # PRD/TDD/STARTUP/架构图/更新日志
├── tests/            # 单元与集成测试
├── logs/             # 运行日志目录
├── docker-compose.yml
├── pyproject.toml / poetry.lock
└── README.md
```

## 测试与质量控制

```bash
pytest
pytest tests/test_crawlers/
pytest --cov=src --cov-report=term-missing --cov-report=html

# 代码风格
poetry run black src tests
poetry run isort src tests
poetry run mypy src
```

## 文档与参考

- `docs/PRD.md` – 产品需求文档 (v4)。
- `docs/TDD-1.md` – 技术设计 & 数据模型细节。
- `docs/STARTUP_GUIDE.md` – 详细环境/部署指南 (WSL/Poetry)。
- `docs/task.md` – 任务清单 / Roadmap。
- `docs/architecture-phase1.drawio`, `docs/dataflow-phase1.drawio` – 架构与数据流图。
- `docs/update.md` – 更新日志 (例: 2025-01-09 系统监控与费用计算增强)。
- `QUICKSTART.md` – 运维一页纸手册。

## 许可证

Copyright © 2025 All Rights Reserved.

## 联系方式

如有问题或建议,请联系项目维护者。
