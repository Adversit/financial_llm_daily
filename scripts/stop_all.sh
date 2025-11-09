#!/bin/bash
# 金融情报日报系统 - 停止所有服务
# 使用方法: ./scripts/stop_all.sh

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$PROJECT_DIR/.pids"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 停止进程
stop_process() {
    local name="$1"
    local pid_file="$PID_DIR/$2.pid"

    if [ ! -f "$pid_file" ]; then
        log_warn "$name 未运行 (PID 文件不存在)"
        return
    fi

    local pid=$(cat "$pid_file")

    if ! ps -p "$pid" > /dev/null 2>&1; then
        log_warn "$name 未运行 (进程不存在)"
        rm -f "$pid_file"
        return
    fi

    log_info "停止 $name (PID: $pid)..."
    kill -TERM "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
    sleep 2

    if ps -p "$pid" > /dev/null 2>&1; then
        log_warn "强制停止 $name..."
        kill -9 "$pid" 2>/dev/null
        sleep 1
    fi

    rm -f "$pid_file"
    log_info "✓ $name 已停止"
}

# 停止 Docker 服务
stop_docker_services() {
    log_info "停止 Docker 服务..."
    cd "$PROJECT_DIR"

    # 使用 docker compose 或 docker-compose
    if docker compose version &> /dev/null 2>&1; then
        DOCKER_COMPOSE="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        log_warn "docker-compose 不可用，跳过 Docker 服务停止"
        return
    fi

    $DOCKER_COMPOSE down
    log_info "✓ Docker 服务已停止"
}

# 主函数
main() {
    log_info "========================================="
    log_info "金融情报日报系统 - 停止所有服务"
    log_info "========================================="
    echo

    stop_process "Celery Beat" "celery_beat"
    stop_process "Celery Worker" "celery_worker"
    stop_process "Web 服务" "web"
    stop_docker_services

    echo
    log_info "所有服务已停止"
    echo
}

main
