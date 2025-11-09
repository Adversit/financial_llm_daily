#!/bin/bash
# 项目初始化脚本
# 用于快速设置开发环境

set -e

echo "🚀 金融情报日报系统 - 项目初始化"
echo "================================"

# 检查是否已安装Poetry
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry 未安装,正在安装..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "✅ Poetry 已安装"
fi

# 配置Poetry在项目目录创建虚拟环境
echo "📦 配置 Poetry..."
poetry config virtualenvs.in-project true

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "⚠️  .env 文件不存在,从模板创建..."
    cp .env.example .env
    echo "⚙️  请编辑 .env 文件,填写必要的配置项"
    echo "   必填项: DATABASE_URL, REDIS_URL, API Keys, SMTP配置"
fi

# 安装依赖
echo "📦 安装 Python 依赖..."
poetry install

# 安装Playwright浏览器
echo "🌐 安装 Playwright 浏览器..."
poetry run playwright install chromium

# 启动Docker服务
echo "🐳 启动 Docker 服务 (PostgreSQL + Redis)..."
docker-compose up -d

# 等待数据库启动
echo "⏳ 等待数据库启动..."
sleep 5

# 检查数据库连接
echo "🔍 检查数据库连接..."
docker-compose exec -T postgres pg_isready -U fin_user || {
    echo "❌ 数据库未就绪,请检查 Docker 服务"
    exit 1
}

echo "✅ 数据库已就绪"

# 创建初始迁移
echo "🗃️  创建数据库迁移..."
poetry run alembic revision --autogenerate -m "Initial schema"

# 执行迁移
echo "⬆️  执行数据库迁移..."
poetry run alembic upgrade head

echo ""
echo "✨ 初始化完成!"
echo ""
echo "下一步:"
echo "1. 编辑 .env 文件,填写 API Keys 和 SMTP 配置"
echo "2. 激活虚拟环境: poetry shell"
echo "3. 运行测试: pytest"
echo "4. 手动执行任务: poetry run python -m src.cli.run_once --step all"
echo ""
echo "启动服务:"
echo "- Celery Worker: poetry run celery -A src.tasks.celery_app worker --loglevel=info"
echo "- Celery Beat: poetry run celery -A src.tasks.celery_app beat --loglevel=info"
echo "- FastAPI: poetry run uvicorn src.api.main:app --reload"
