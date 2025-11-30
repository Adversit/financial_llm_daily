# 金融情报日报系统 - 启动指南

**版本**: v2.0
**更新日期**: 2025-11-09
**适用环境**: Windows + WSL2 + Poetry

---

## 📋 目录

1. [系统架构](#系统架构)
2. [前置要求](#前置要求)
3. [环境准备](#环境准备)
4. [数据库初始化](#数据库初始化)
5. [启动服务](#启动服务)
6. [访问系统](#访问系统)
7. [常见问题](#常见问题)
8. [开发调试](#开发调试)

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     浏览器 (Browser)                         │
│                  http://localhost:8000                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Web Server                          │
│                  (src/web/app.py)                           │
│         端口: 8000 | 进程: uvicorn                          │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┬─────────────┐
                ↓             ↓             ↓             ↓
        ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
        │PostgreSQL│   │  Redis   │   │ Celery   │   │  SMTP    │
        │  (数据)  │   │ (缓存)   │   │ (任务)   │   │ (邮件)   │
        │5432端口  │   │6379端口  │   │ Worker   │   │          │
        └──────────┘   └──────────┘   └──────────┘   └──────────┘
```

---

## 前置要求

### 必需组件

| 组件 | 版本要求 | 说明 |
|------|---------|------|
| **Windows** | 10/11 | 主操作系统 |
| **WSL2** | Ubuntu 20.04+ | Linux子系统 |
| **Python** | 3.11+ | 通过 Poetry 管理 |
| **Poetry** | 1.7+ | Python 依赖管理 |
| **PostgreSQL** | 14+ | 数据库 |
| **Redis** | 7+ | 缓存与队列 |
| **SMTP账号** | - | 邮件发送 (如: 163邮箱) |

### 可选组件

- **Git** - 版本管理
- **VS Code** - 推荐编辑器 (带 WSL 扩展)

---

## 环境准备

### 1️⃣ 安装依赖

#### 在 WSL 中安装必要工具

```bash
# 启动 WSL
wsl

# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python 3.11 (如果未安装)
sudo apt install python3.11 python3.11-venv python3-pip -y

# 安装 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 添加 Poetry 到 PATH (添加到 ~/.bashrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 验证安装
poetry --version
```

#### 安装 PostgreSQL (如未安装)

```bash
# 在 WSL 中安装
sudo apt install postgresql postgresql-contrib -y

# 启动服务
sudo service postgresql start

# 创建数据库和用户
sudo -u postgres psql -c "CREATE USER fin_user WITH PASSWORD 'fin_pass';"
sudo -u postgres psql -c "CREATE DATABASE fin_daily_report OWNER fin_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE fin_daily_report TO fin_user;"
```

#### 安装 Redis (如未安装)

```bash
# 在 WSL 中安装
sudo apt install redis-server -y

# 启动服务
sudo service redis-server start

# 验证
redis-cli ping  # 应返回 PONG
```

### 2️⃣ 克隆并进入项目

```bash
# 进入项目目录 (从 Windows 盘符访问)
cd /mnt/d/work/project/Fin_daily_report/V4

# 如果使用 Git
git pull  # 更新代码
```

### 3️⃣ 安装 Python 依赖

```bash
# 激活虚拟环境并安装依赖
source .venv/bin/activate

# 安装所有依赖 (包括开发依赖)
poetry install

# 仅安装生产依赖
poetry install --no-dev
```

### 4️⃣ 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置 (使用 nano/vim 或在 Windows 中编辑)
nano .env
```

**关键配置项**:

```bash
# 数据库 (必须配置)
DATABASE_URL=postgresql://fin_user:fin_pass@localhost:5432/fin_daily_report

# Redis (必须配置)
REDIS_URL=redis://localhost:6379/0

# LLM API (必须配置)
PROVIDER_DEEPSEEK_API_KEY=sk-your-deepseek-key
PROVIDER_QWEN_API_KEY=sk-your-qwen-key

# SMTP 邮件 (必须配置)
SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USER=your_email@163.com
SMTP_PASS=your_auth_code

# JWT 密钥 (生产环境必须修改)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
```

---

## 数据库初始化

### 1️⃣ 运行数据库迁移

```bash
# 确保在虚拟环境中
source .venv/bin/activate

# 查看当前迁移状态
alembic current

# 执行所有迁移 (创建表和初始数据)
alembic upgrade head

# 验证迁移
python -c "
from src.db.session import get_db
from src.models.user import User

db = next(get_db())
admin = db.query(User).filter(User.email == 'xtyydsf@system.local').first()
print(f'✅ 管理员账号: {admin.email}' if admin else '❌ 管理员账号未创建')
"
```

**预置数据**:
- 管理员账号: `xtyydsf@system.local` / `xtyydsf` (或直接输入 `xtyydsf`)
- 系统默认配置: TopN=5, 阈值=0.6, 主题色=#1d4ed8 等

### 2️⃣ (可选) 添加白名单用户

如果需要普通用户登录 (OTP方式):

```bash
# 进入 Python 环境
python

# 添加白名单邮箱
from src.db.session import get_db
from src.models.delivery import ReportRecipient, RecipientType

db = next(get_db())

# 添加白名单用户
whitelist_user = ReportRecipient(
    email="your.email@example.com",
    display_name="Your Name",
    type=RecipientType.WHITELIST,
    enabled=True
)
db.add(whitelist_user)
db.commit()
print("✅ 白名单用户已添加")
```

---

## 启动服务

### 方式一: 分别启动各服务 (推荐用于开发)

#### 终端 1: 启动 Web 服务

```bash
# 在 WSL 中
cd /mnt/d/work/project/Fin_daily_report/V4
source .venv/bin/activate

# 启动 FastAPI Web 服务 (开发模式，支持热重载)
uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --reload

# 生产模式 (多 worker)
# uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --workers 2
```

#### 终端 2: 启动 Celery Worker (可选，用于后台任务)

```bash
# 在 WSL 中新开终端
cd /mnt/d/work/project/Fin_daily_report/V4
source .venv/bin/activate

# 启动 Celery Worker
celery -A src.tasks.celery_app worker --loglevel=info --concurrency=2

# 查看 Celery 状态
celery -A src.tasks.celery_app inspect active
```

#### 终端 3: 启动 Celery Beat (可选，用于定时任务)

```bash
# 在 WSL 中新开终端
cd /mnt/d/work/project/Fin_daily_report/V4
source .venv/bin/activate

# 启动 Celery Beat
celery -A src.tasks.celery_app beat --loglevel=info
```

### 方式二: 使用启动脚本 (即将创建)

```bash
# 一键启动所有服务
./scripts/start_all.sh

# 停止所有服务
./scripts/stop_all.sh
```

---

## 访问系统

### 🌐 Web 管理台

- **URL**: http://localhost:8000
- **登录页**: http://localhost:8000/login
- **健康检查**: http://localhost:8000/healthz

### 🔐 登录方式

#### 方式一: 管理员密码登录

1. 访问 http://localhost:8000/login
2. 邮箱: `xtyydsf` (或 `xtyydsf@system.local`)
3. 密码: `xtyydsf`
4. 点击"登录"

#### 方式二: 普通用户 OTP 登录

1. 访问 http://localhost:8000/login
2. 输入白名单邮箱 (如 `your.email@example.com`)
3. 点击"发送验证码"
4. 查收邮件，输入 6 位验证码
5. 点击"登录"

### 📊 主要功能页面

| 页面 | URL | 说明 |
|------|-----|------|
| 报告列表 | /reports | 查看所有日报 |
| 报告详情 | /reports/{date} | 查看指定日期报告 |
| 用户偏好 | /preferences | 管理提示词模板 |
| 统计摘要 | /stats/summary | 数据统计 |
| 词云 | /stats/wordcloud | 词云可视化 |
| 管理后台 | /admin | 仅管理员可访问 |
| 信息源管理 | /admin/sources | 管理采集源 |
| 收件人管理 | /admin/recipients | 管理收件人 |
| 系统设置 | /admin/settings | 系统参数配置 |
| 操作审计 | /admin/audit | 查看审计日志 |
| 系统状态 | /admin/status | 监控系统健康 |

---

## 常见问题

### ❓ 启动时提示"端口已被占用"

```bash
# 查找占用端口的进程
sudo lsof -i :8000

# 杀死进程
sudo kill -9 <PID>

# 或者换个端口启动
uvicorn src.web.app:app --port 8001
```

### ❓ 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
sudo service postgresql status

# 启动 PostgreSQL
sudo service postgresql start

# 测试连接
psql -U fin_user -d fin_daily_report -h localhost -W
```

### ❓ Redis 连接失败

```bash
# 检查 Redis 是否运行
sudo service redis-server status

# 启动 Redis
sudo service redis-server start

# 测试连接
redis-cli ping
```

### ❓ OTP 验证码收不到

1. 检查 `.env` 中的 SMTP 配置是否正确
2. 确认邮箱在白名单中 (`report_recipients` 表, `type='whitelist'`)
3. 查看 Web 服务日志是否有发送错误
4. 检查邮箱授权码 (不是密码!)

### ❓ 登录后提示"未登录"

1. 检查浏览器是否允许 Cookie
2. 确认 JWT_SECRET_KEY 已配置
3. 检查浏览器控制台是否有错误
4. 尝试清除浏览器 Cookie 后重新登录

### ❓ 页面样式错乱

1. 检查静态文件目录是否存在: `src/web/static/`
2. 确认 Tailwind CDN 可访问
3. 查看浏览器开发者工具的网络请求

---

## 开发调试

### 🔍 查看日志

```bash
# Web 服务日志 (终端直接输出)
# 使用 uvicorn --reload 时会自动显示

# Celery Worker 日志
# 使用 --loglevel=info 时会输出到终端

# 数据库查询日志
# 在 src/config/settings.py 中设置 SQLALCHEMY_ECHO=True
```

### 🧪 运行测试

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/test_web/

# 查看覆盖率
pytest --cov=src --cov-report=html
```

### 📝 创建新的数据库迁移

```bash
# 修改模型后生成迁移
alembic revision --autogenerate -m "描述你的修改"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 🐛 交互式调试

```bash
# 进入 IPython
ipython

# 导入并测试模块
from src.web.security import hash_password, verify_password
from src.db.session import get_db
from src.models.user import User

db = next(get_db())
admin = db.query(User).first()
print(admin)
```

---

## 快速命令参考

```bash
# === 服务管理 ===
sudo service postgresql start    # 启动数据库
sudo service redis-server start  # 启动 Redis
source .venv/bin/activate       # 激活虚拟环境

# === Web 服务 ===
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000

# === Celery ===
celery -A src.tasks.celery_app worker --loglevel=info
celery -A src.tasks.celery_app beat --loglevel=info

# === 数据库 ===
alembic upgrade head            # 执行迁移
alembic current                 # 查看当前版本
alembic downgrade -1            # 回滚一个版本

# === 测试 ===
pytest                          # 运行所有测试
pytest -v                       # 详细输出
pytest --cov=src               # 测试覆盖率

# === 代码质量 ===
black src/                      # 格式化代码
flake8 src/                     # 代码检查
mypy src/                       # 类型检查
```

---

## 📞 获取帮助

- 查看项目文档: `docs/` 目录
- 技术设计文档: `docs/TDD-2.md`
- 任务文档: `docs/task_2.md`
- 进度记录: `docs/stage2_progress.md`

---

**祝你使用愉快！** 🚀
