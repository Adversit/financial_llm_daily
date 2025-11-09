# 金融情报日报系统 v1.0 (MVP)

## 项目简介

金融情报日报系统是一个自动化的信息采集、处理和投递平台,每日自动从多个信息源采集金融相关资讯,通过LLM提取关键事实和观点,生成结构化报告并通过邮件投递给订阅用户。

### 核心功能

- **信息源采集**: 支持RSS订阅、静态网页、动态网页三种采集方式
- **智能处理**: 基于LLM的事实观点抽取,支持长文分块和降级策略
- **报告生成**: 自动评分排序,生成HTML格式的日报正文和全量附件
- **邮件投递**: 分批节流发送,支持重试和退信处理

### 技术栈

- **后端**: Python 3.12 + FastAPI
- **数据库**: PostgreSQL 15
- **缓存/消息队列**: Redis 7
- **任务调度**: Celery + Celery Beat
- **LLM**: DeepSeek / Qwen (可配置多Provider回退)
- **网页采集**: Playwright, Trafilatura, BeautifulSoup
- **部署**: Docker Compose

## 快速开始

### 1. 环境要求

- Python 3.11+
- Docker & Docker Compose
- WSL2 (Windows用户)

### 2. 克隆项目

```bash
git clone <repository-url>
cd V4
```

### 3. 启动依赖服务

```bash
# 启动 PostgreSQL 和 Redis
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 4. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件,填写必要的配置
# 必填项:
# - DATABASE_URL
# - REDIS_URL
# - PROVIDER_DEEPSEEK_API_KEY
# - PROVIDER_QWEN_API_KEY
# - SMTP_USER
# - SMTP_PASS
```

### 5. 安装Python依赖

**方式一: 使用 Poetry (推荐 - WSL环境)**

```bash
# 安装 Poetry (如果未安装)
curl -sSL https://install.python-poetry.org | python3 -

# 配置 Poetry 在项目目录创建虚拟环境
poetry config virtualenvs.in-project true

# 安装依赖
poetry install

# 激活虚拟环境
source .venv/bin/activate

# 安装 Playwright 浏览器
playwright install chromium
```

**方式二: 使用 pip**

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac/WSL:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 6. 初始化数据库

```bash
# 执行数据库迁移
alembic upgrade head

# (可选) 插入测试数据
python scripts/seed_test_data.py
```

### 7. 启动服务

```bash
# 启动 Celery Worker
celery -A src.tasks.celery_app worker --loglevel=info --concurrency=4

# 启动 Celery Beat (定时任务)
celery -A src.tasks.celery_app beat --loglevel=info

# 启动 FastAPI (可选,阶段一仅健康检查)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

## 使用指南

### 手动执行任务

使用CLI工具可以手动触发各个步骤:

```bash
# 执行完整流程
python -m src.cli.run_once --step all

# 仅采集
python -m src.cli.run_once --step crawl

# 仅LLM抽取
python -m src.cli.run_once --step extract

# 仅生成报告
python -m src.cli.run_once --step compose

# 仅发送邮件
python -m src.cli.run_once --step send

# 指定日期执行
python -m src.cli.run_once --step extract --date 2025-11-04
```

### 定时任务

系统默认配置为每日 06:00 自动执行完整流程:

1. 06:00 - 采集信息源
2. 06:05 - LLM抽取处理
3. 06:10 - 生成报告
4. 06:12 - 发送邮件

目标: 06:20 前完成所有任务

## 项目结构

```
V4/
├── src/                    # 源代码
│   ├── config/            # 配置管理
│   ├── models/            # 数据模型
│   ├── db/                # 数据库连接和迁移
│   ├── crawlers/          # 采集器模块
│   ├── nlp/               # LLM处理模块
│   ├── composer/          # 报告生成模块
│   ├── mailer/            # 邮件投递模块
│   ├── tasks/             # Celery任务
│   ├── api/               # FastAPI接口
│   ├── cli/               # 命令行工具
│   └── utils/             # 工具函数
├── tests/                 # 测试用例
├── docs/                  # 文档
├── logs/                  # 日志文件
├── requirements.txt       # Python依赖
├── docker-compose.yml     # Docker编排
├── alembic.ini           # Alembic配置
├── .env                   # 环境变量(不入库)
└── README.md             # 本文件
```

## 数据库表结构

核心表:
- `sources`: 信息源配置
- `articles`: 采集的文章
- `extraction_queue`: 抽取队列
- `extraction_items`: 抽取结果(事实观点)
- `reports`: 生成的报告
- `report_recipients`: 收件人列表
- `delivery_log`: 投递日志
- `provider_usage`: LLM用量统计

详见: `docs/TDD-1.md`

## 开发说明

### 运行测试

```bash
# 运行所有测试
pytest

# 运行指定模块测试
pytest tests/test_crawlers/

# 查看覆盖率
pytest --cov=src --cov-report=html
```

### 代码规范

- 遵循 PEP 8
- 使用 Type Hints
- 函数和类添加 Docstring
- 提交前运行测试

### 常见问题

**Q: Playwright 安装失败?**
A: 确保网络畅通,或使用镜像源安装

**Q: 数据库连接失败?**
A: 检查 docker-compose 服务是否正常运行,`.env` 配置是否正确

**Q: LLM API 超时?**
A: 检查网络连接,调整 `LLM_TIMEOUT_SEC` 配置,或启用备用Provider

**Q: 邮件发送失败?**
A: 检查 SMTP 配置,确认授权码正确,注意发送频率限制

## 文档

- [产品需求文档 (PRD)](docs/PRD.md)
- [技术设计文档 (TDD)](docs/TDD-1.md)
- [任务清单](docs/task.md)
- [架构图](docs/architecture-phase1.drawio)
- [数据流图](docs/dataflow-phase1.drawio)

## 许可证

Copyright © 2025 All Rights Reserved.

## 联系方式

如有问题或建议,请联系项目维护者。
