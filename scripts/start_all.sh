#!/bin/bash
# 金融情报日报系统 - 一键启动所有服务
# 使用方法: ./scripts/start_all.sh

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/.pids"

# 创建必要目录
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查进程是否运行
is_running() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# 启动 Docker Compose 服务 (PostgreSQL + Redis)
start_docker_services() {
    log_info "启动 Docker 服务 (PostgreSQL + Redis)..."
    cd "$PROJECT_DIR"

    # 检查 docker-compose 是否可用
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        log_error "✗ docker-compose 未安装或不可用"
        exit 1
    fi

    # 使用 docker compose 或 docker-compose
    if docker compose version &> /dev/null 2>&1; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi

    # 启动容器
    $DOCKER_COMPOSE up -d postgres redis
    sleep 5

    # 检查 PostgreSQL
    if docker exec fin_report_postgres pg_isready -U fin_user > /dev/null 2>&1; then
        log_info "✓ PostgreSQL 已启动"
    else
        log_error "✗ PostgreSQL 启动失败"
        exit 1
    fi

    # 检查 Redis
    if docker exec fin_report_redis redis-cli ping > /dev/null 2>&1; then
        log_info "✓ Redis 已启动"
    else
        log_error "✗ Redis 启动失败"
        exit 1
    fi
}

# 启动Web服务
start_web() {
    local pid_file="$PID_DIR/web.pid"

    if is_running "$pid_file"; then
        log_warn "Web 服务已在运行中 (PID: $(cat $pid_file))"
        return
    fi

    log_info "启动 Web 服务 (uvicorn)..."
    cd "$PROJECT_DIR"
    source .venv/bin/activate

    nohup uvicorn src.web.app:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        > "$LOG_DIR/web.log" 2>&1 &

    echo $! > "$pid_file"
    sleep 3

    if is_running "$pid_file"; then
        log_info "✓ Web 服务已启动 (PID: $(cat $pid_file))"
        log_info "  访问地址: http://localhost:8000"
    else
        log_error "✗ Web 服务启动失败，请查看日志: $LOG_DIR/web.log"
        exit 1
    fi
}

# 启动Celery Worker
start_celery_worker() {
    local pid_file="$PID_DIR/celery_worker.pid"

    if is_running "$pid_file"; then
        log_warn "Celery Worker 已在运行中 (PID: $(cat $pid_file))"
        return
    fi

    log_info "启动 Celery Worker..."
    cd "$PROJECT_DIR"
    source .venv/bin/activate

    nohup celery -A src.tasks.celery_app worker \
        --loglevel=info \
        --concurrency=2 \
        > "$LOG_DIR/celery_worker.log" 2>&1 &

    echo $! > "$pid_file"
    sleep 3

    if is_running "$pid_file"; then
        log_info "✓ Celery Worker 已启动 (PID: $(cat $pid_file))"
    else
        log_warn "⚠ Celery Worker 可能启动失败，请查看日志: $LOG_DIR/celery_worker.log"
    fi
}

# 启动Celery Beat
start_celery_beat() {
    local pid_file="$PID_DIR/celery_beat.pid"

    if is_running "$pid_file"; then
        log_warn "Celery Beat 已在运行中 (PID: $(cat $pid_file))"
        return
    fi

    log_info "启动 Celery Beat..."
    cd "$PROJECT_DIR"
    source .venv/bin/activate

    nohup celery -A src.tasks.celery_app beat \
        --loglevel=info \
        > "$LOG_DIR/celery_beat.log" 2>&1 &

    echo $! > "$pid_file"
    sleep 2

    if is_running "$pid_file"; then
        log_info "✓ Celery Beat 已启动 (PID: $(cat $pid_file))"
    else
        log_warn "⚠ Celery Beat 可能启动失败，请查看日志: $LOG_DIR/celery_beat.log"
    fi
}

# 主函数
main() {
    log_info "========================================="
    log_info "金融情报日报系统 - 启动所有服务"
    log_info "========================================="
    echo

    start_docker_services
    start_web
    start_celery_worker
    start_celery_beat

    echo
    log_info "========================================="
    log_info "所有服务启动完成！"
    log_info "========================================="
    echo
    log_info "服务状态:"
    log_info "  🌐 Web管理台:        http://localhost:8000"
    log_info "  🔐 登录页面:         http://localhost:8000/login"
    log_info "  📚 API文档(Swagger): http://localhost:8000/docs"
    log_info "  📖 API文档(ReDoc):   http://localhost:8000/redoc"
    log_info "  🔍 健康检查:         http://localhost:8000/healthz"
    echo
    log_info "管理账号:"
    log_info "  用户名: xtyydsf"
    log_info "  密码:   xtyydsf"
    echo
    log_info "日志与控制:"
    log_info "  日志目录: $LOG_DIR"
    log_info "  PID目录:  $PID_DIR"
    log_info "  查看日志: tail -f $LOG_DIR/web.log"
    log_info "  停止服务: ./scripts/stop_all.sh"
    echo
}

main
