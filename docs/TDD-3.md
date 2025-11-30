# 金融情报日报系统 · 技术设计文档

（TDD · 第三阶段｜容器化与生产部署）

**版本**：v4.0
**日期**：2025-11-10（Asia/Shanghai）
**目标**：基于阶段一/二的完整实现，构建生产级 Docker 容器化方案，支持 WSL 开发环境与腾讯云 2C/2G 生产环境的一键部署、高可用运维与完整可观测性。

---

## 1. 系统现状与容器化目标

### 1.1 当前架构

系统已完成核心功能开发，包括：

- **采集模块**：RSS、静态网页、Playwright 动态渲染，支持 SimHash 去重
- **NLP 模块**：DeepSeek + Qwen 双 Provider 抽取，智能降级与费用追踪
- **报告模块**：智能打分、HTML 邮件生成、Excel 附件导出
- **邮件模块**：批量投递、节流控制、失败重试与 delivery_log
- **Web 管理台**：FastAPI + Jinja2 SSR，管理员后台、系统监控、费用统计、词云分析
- **任务调度**：Celery Beat 定时触发，Worker 处理异步任务

**当前部署方式**：
- 开发环境：`scripts/start_all.sh` 启动所有服务（依赖 WSL + Poetry 虚拟环境）
- 基础设施：Docker Compose 提供 PostgreSQL 15 + Redis 7

### 1.2 容器化目标

**Phase 3A - 完整容器化**（本阶段重点）：
1. 将 Web、Worker、Beat 应用封装为 Docker 镜像
2. 构建统一的 docker-compose 编排方案，支持开发/生产双环境
3. 实现容器健康检查、资源限制、日志管理
4. 提供一键部署能力，消除手动环境配置

**Phase 3B - 生产优化**（后续增强）：
5. 数据库备份与恢复自动化
6. 反向代理与 TLS 配置
7. 监控告警集成（Prometheus + Grafana）
8. CI/CD 流水线

---

## 2. 容器架构设计

### 2.1 服务拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                       Docker Network: finrep-net            │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │   Web    │  │  Worker  │  │   Beat   │                  │
│  │  :8000   │  │ (Celery) │  │ (Celery) │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
│       │             │              │                         │
│       └─────────────┴──────────────┘                        │
│                     │                                        │
│         ┌───────────┴───────────┐                           │
│         │                       │                           │
│    ┌────▼────┐           ┌─────▼──────┐                    │
│    │PostgreSQL│           │   Redis    │                    │
│    │  :5432  │           │   :6379    │                    │
│    └─────────┘           └────────────┘                    │
│         │                                                    │
│    ┌────▼────┐                                              │
│    │ pgdata  │  (持久化卷)                                 │
│    └─────────┘                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 服务组件详解

| 服务 | 基础镜像 | 端口 | 职责 | 依赖 |
|------|---------|------|------|------|
| **web** | `python:3.11-slim` | 8000 | FastAPI 应用、Web 管理台、API 接口、健康检查 | postgres, redis |
| **worker** | `python:3.11-slim` | - | Celery Worker，处理采集/抽取/报告/邮件任务 | postgres, redis |
| **beat** | `python:3.11-slim` | - | Celery Beat，定时调度（06:00 触发日报流程） | redis |
| **postgres** | `postgres:15` | 5432 | 持久化存储（sources/articles/reports/users） | - |
| **redis** | `redis:7-alpine` | 6379 | Celery Broker/Backend、缓存、节流控制 | - |

**可选服务（生产环境）**：
- `nginx`：反向代理、TLS 终止、静态资源缓存
- `backup`：定时数据库备份（pg_dump + COS 上传）
- `mailhog`：开发环境 SMTP 测试（生产禁用）

### 2.3 存储卷设计

```yaml
volumes:
  postgres_data:      # PostgreSQL 数据持久化
  redis_data:         # Redis RDB/AOF 持久化（可选）
  logs_data:          # 应用日志归档（可选）
  backup_data:        # 数据库备份存储（可选）
```

---

## 3. 镜像构建规范

### 3.1 多阶段构建策略

**Dockerfile 结构**：

```dockerfile
# Stage 1: 依赖构建（builder）
FROM python:3.11-slim as builder
WORKDIR /build
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Stage 2: 运行时镜像（runtime）
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src ./src
COPY scripts ./scripts
COPY alembic.ini ./

# 安装运行时依赖（Playwright 浏览器）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
        libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
        libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
        libgbm1 libpango-1.0-0 libcairo2 libasound2 && \
    playwright install chromium && \
    rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r finrep && useradd -r -g finrep finrep
USER finrep

# 多入口支持（通过 CMD 覆盖）
CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.2 镜像标签规范

- **开发环境**：`finrep/app:dev`
- **生产环境**：`finrep/app:{version}` 或 `finrep/app:{git-sha}`
  - 示例：`finrep/app:1.0.0`、`finrep/app:5c4cd1d`

### 3.3 构建命令

```bash
# 开发镜像（包含调试工具）
docker build -t finrep/app:dev .

# 生产镜像（最小化）
docker build -t finrep/app:1.0.0 --target runtime .

# 多架构构建（支持 ARM64）
docker buildx build --platform linux/amd64,linux/arm64 \
  -t finrep/app:1.0.0 --push .
```

---

## 4. Docker Compose 配置

### 4.1 开发环境（docker-compose.dev.yml）

**特点**：
- 启用代码热重载（volumes 挂载源码）
- 内置 PostgreSQL + Redis
- 可选 MailHog SMTP 测试服务
- 日志输出到控制台

**核心配置**：

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: finrep_postgres_dev
    environment:
      POSTGRES_USER: fin_user
      POSTGRES_PASSWORD: fin_pass
      POSTGRES_DB: fin_daily_report
      TZ: Asia/Shanghai
    ports:
      - "5432:5432"
    volumes:
      - postgres_data_dev:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fin_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: finrep_redis_dev
    ports:
      - "6379:6379"
    volumes:
      - redis_data_dev:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build:
      context: .
      dockerfile: Dockerfile
    image: finrep/app:dev
    container_name: finrep_web_dev
    command: uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./src:/app/src  # 代码热重载
      - ./logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  worker:
    image: finrep/app:dev
    container_name: finrep_worker_dev
    command: celery -A src.tasks.celery_app worker --loglevel=info --concurrency=2
    env_file:
      - .env
    volumes:
      - ./src:/app/src
      - ./logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  beat:
    image: finrep/app:dev
    container_name: finrep_beat_dev
    command: celery -A src.tasks.celery_app beat --loglevel=info
    env_file:
      - .env
    volumes:
      - ./src:/app/src
      - ./logs:/app/logs
    depends_on:
      redis:
        condition: service_healthy

volumes:
  postgres_data_dev:
  redis_data_dev:
```

### 4.2 生产环境（docker-compose.prod.yml）

**特点**：
- 资源限制（适配 2C/2G 云服务器）
- 自动重启策略
- 日志滚动配置
- 健康检查与优雅关闭
- 外部数据库支持（可选）

**核心配置**：

```yaml
version: '3.8'

services:
  web:
    image: finrep/app:1.0.0
    container_name: finrep_web_prod
    command: uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --workers 2
    ports:
      - "8000:8000"
    env_file:
      - .env.prod
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "3"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    image: finrep/app:1.0.0
    container_name: finrep_worker_prod
    command: celery -A src.tasks.celery_app worker --loglevel=info --concurrency=2 --max-tasks-per-child=50
    env_file:
      - .env.prod
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "3"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  beat:
    image: finrep/app:1.0.0
    container_name: finrep_beat_prod
    command: celery -A src.tasks.celery_app beat --loglevel=info
    env_file:
      - .env.prod
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.2'
          memory: 128M
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "3"
    depends_on:
      redis:
        condition: service_healthy

  postgres:
    image: postgres:15
    container_name: finrep_postgres_prod
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
      TZ: Asia/Shanghai
    ports:
      - "5432:5432"
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "20m"
        max-file: "2"

  redis:
    image: redis:7-alpine
    container_name: finrep_redis_prod
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis_data_prod:/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.3'
          memory: 256M
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "2"

volumes:
  postgres_data_prod:
  redis_data_prod:

networks:
  default:
    name: finrep-net
```

---

## 5. 环境变量配置

### 5.1 必需环境变量

创建 `.env.prod` 文件（**不要提交到版本控制**）：

```bash
# 环境标识
ENV=production
TZ=Asia/Shanghai

# 数据库配置
DATABASE_URL=postgresql://fin_user:fin_pass@postgres:5432/fin_daily_report
POSTGRES_USER=fin_user
POSTGRES_PASSWORD=fin_pass  # 生产环境使用强密码
POSTGRES_DB=fin_daily_report

# Redis 配置
REDIS_URL=redis://redis:6379/0

# LLM Provider - DeepSeek
PROVIDER_DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx
PROVIDER_DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
PROVIDER_DEEPSEEK_MODEL=deepseek-chat

# LLM Provider - Qwen
PROVIDER_QWEN_API_KEY=sk-xxxxxxxxxxxxx
PROVIDER_QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PROVIDER_QWEN_MODEL=qwen-max

# 邮件配置
SMTP_HOST=smtp.exmail.qq.com  # 企业邮箱（推荐）
SMTP_PORT=465
SMTP_USER=report@example.com
SMTP_PASS=xxxxxxxxxxxxxxxx  # SMTP 授权码

# JWT 安全配置
JWT_SECRET_KEY=change-this-to-a-very-long-random-string-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# 系统配置
CRAWL_CONCURRENCY_RSS=10
CRAWL_CONCURRENCY_WEB=2
LLM_TIMEOUT_SEC=90
REPORT_TOPN=5
MAIL_BATCH_LIMIT=50
MAIL_RATE_LIMIT_PER_SEC=1.0
```

### 5.2 配置优先级

1. **环境变量**：Docker Compose `environment` > `.env` 文件
2. **默认值**：`src/config/settings.py` 中的 Pydantic 默认值
3. **运行时覆盖**：管理台"系统设置"可动态修改部分配置

---

## 6. 部署流程

### 6.1 开发环境部署

```bash
# 1. 克隆仓库
git clone <repository-url>
cd Fin_daily_report/V4

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填充必要配置

# 3. 构建镜像
docker-compose -f docker-compose.dev.yml build

# 4. 启动所有服务
docker-compose -f docker-compose.dev.yml up -d

# 5. 初始化数据库
docker-compose -f docker-compose.dev.yml exec web alembic upgrade head

# 6. 导入测试数据（可选）
docker-compose -f docker-compose.dev.yml exec web python scripts/seed_test_data.py

# 7. 验证服务
curl http://localhost:8000/healthz
# 访问管理台：http://localhost:8000
```

### 6.2 生产环境部署（腾讯云 2C/2G）

**服务器要求**：
- Ubuntu 20.04+ / CentOS 8+
- 2 核 CPU，2GB 内存，40GB 磁盘
- Docker 20.10+ / Docker Compose 2.0+

**部署步骤**：

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | bash
systemctl enable docker
systemctl start docker

# 2. 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 3. 克隆仓库
git clone <repository-url>
cd Fin_daily_report/V4

# 4. 配置生产环境变量
vim .env.prod
# 填充数据库密码、API Key、SMTP 配置等

# 5. 构建生产镜像
docker build -t finrep/app:1.0.0 .

# 6. 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 7. 初始化数据库
docker-compose -f docker-compose.prod.yml exec web alembic upgrade head

# 8. 导入信息源和收件人
docker-compose -f docker-compose.prod.yml exec web python scripts/seed_test_data.py

# 9. 验证服务
curl http://localhost:8000/healthz
docker-compose -f docker-compose.prod.yml ps

# 10. 配置防火墙（开放 8000 端口）
ufw allow 8000/tcp
ufw reload
```

### 6.3 外部数据库配置（推荐）

生产环境建议使用云数据库（如腾讯云 PostgreSQL）：

1. 创建云数据库实例（PostgreSQL 15）
2. 配置网络白名单（添加服务器 IP）
3. 修改 `.env.prod`：

```bash
DATABASE_URL=postgresql://username:password@your-db-host:5432/fin_daily_report
```

4. 修改 `docker-compose.prod.yml`，移除 `postgres` 服务：

```yaml
services:
  web:
    # ...
    depends_on:
      - redis  # 移除 postgres 依赖
```

---

## 7. 健康检查与监控

### 7.1 容器健康检查

**Web 服务**：
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

**Worker 健康检查**（自定义脚本）：

创建 `scripts/celery_health_check.sh`：

```bash
#!/bin/bash
celery -A src.tasks.celery_app inspect ping -d celery@$HOSTNAME | grep -q "pong"
exit $?
```

```yaml
healthcheck:
  test: ["CMD", "/app/scripts/celery_health_check.sh"]
  interval: 60s
  timeout: 10s
  retries: 3
```

### 7.2 日志管理

**查看实时日志**：
```bash
# 所有服务
docker-compose -f docker-compose.prod.yml logs -f

# 特定服务
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f worker

# 最近 100 行
docker-compose -f docker-compose.prod.yml logs --tail=100 worker
```

**日志归档与清理**：

生产环境已配置日志滚动：
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "3"
```

手动清理：
```bash
# 清理所有容器日志
truncate -s 0 /var/lib/docker/containers/*/*-json.log
```

### 7.3 系统监控

**内置监控面板**：
- 访问 `http://<server-ip>:8000/admin/status`
- 实时监控：PostgreSQL 连接状态、Redis 内存使用、Celery 任务队列、Web 响应时间
- ECharts 趋势图：30 秒自动刷新

**费用统计**：
- 访问 `http://<server-ip>:8000/admin/usage`
- 查看 DeepSeek/Qwen API 调用量与费用

**命令行监控**：

```bash
# 容器状态
docker-compose -f docker-compose.prod.yml ps

# 资源使用
docker stats

# Celery 队列状态
docker-compose -f docker-compose.prod.yml exec worker \
  celery -A src.tasks.celery_app inspect active

# Redis 连接数
docker-compose -f docker-compose.prod.yml exec redis redis-cli info clients
```

---

## 8. 备份与恢复

### 8.1 数据库备份（自动化）

**方案一：定时脚本**

创建 `scripts/backup_db.sh`：

```bash
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_URL="postgresql://fin_user:fin_pass@postgres:5432/fin_daily_report"

mkdir -p $BACKUP_DIR
pg_dump $DB_URL | gzip > $BACKUP_DIR/finrep_$DATE.sql.gz

# 保留最近 30 天的备份
find $BACKUP_DIR -name "finrep_*.sql.gz" -mtime +30 -delete

echo "Backup completed: finrep_$DATE.sql.gz"
```

**添加到 crontab**：
```bash
0 7 * * * /path/to/scripts/backup_db.sh >> /var/log/finrep_backup.log 2>&1
```

**方案二：Backup 侧车容器**（推荐）

在 `docker-compose.prod.yml` 添加：

```yaml
services:
  backup:
    image: postgres:15
    container_name: finrep_backup_prod
    environment:
      PGHOST: postgres
      PGUSER: ${POSTGRES_USER}
      PGPASSWORD: ${POSTGRES_PASSWORD}
      PGDATABASE: ${POSTGRES_DB}
      BACKUP_SCHEDULE: "0 7 * * *"  # 每天 07:00
    volumes:
      - backup_data:/backups
      - ./scripts/backup_db.sh:/backup_db.sh
    command: >
      bash -c "
        echo '$BACKUP_SCHEDULE /backup_db.sh' | crontab - &&
        crond -f
      "
    depends_on:
      - postgres

volumes:
  backup_data:
```

### 8.2 数据恢复

```bash
# 从备份恢复
gunzip -c finrep_20251110_070000.sql.gz | \
  docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U fin_user -d fin_daily_report

# 或使用 docker cp
docker cp finrep_20251110_070000.sql.gz finrep_postgres_prod:/tmp/
docker-compose -f docker-compose.prod.yml exec postgres bash -c \
  "gunzip -c /tmp/finrep_20251110_070000.sql.gz | psql -U fin_user -d fin_daily_report"
```

### 8.3 卷备份（整体备份）

```bash
# 停止服务
docker-compose -f docker-compose.prod.yml stop

# 备份 PostgreSQL 卷
docker run --rm -v finrep_postgres_data_prod:/data -v $(pwd):/backup \
  busybox tar czf /backup/postgres_data_$(date +%Y%m%d).tar.gz -C /data .

# 恢复卷
docker run --rm -v finrep_postgres_data_prod:/data -v $(pwd):/backup \
  busybox tar xzf /backup/postgres_data_20251110.tar.gz -C /data

# 重启服务
docker-compose -f docker-compose.prod.yml start
```

---

## 9. 运维手册

### 9.1 常见问题排查

#### Web 服务无法启动

**症状**：`docker-compose ps` 显示 web 容器状态为 `Restarting` 或 `Exited`

**排查步骤**：
```bash
# 1. 查看日志
docker-compose -f docker-compose.prod.yml logs web

# 2. 检查健康检查
curl http://localhost:8000/healthz

# 3. 常见原因
# - 数据库连接失败：检查 DATABASE_URL 配置
# - 迁移未执行：运行 alembic upgrade head
# - 端口被占用：lsof -i :8000
# - 环境变量缺失：检查 .env.prod 文件
```

**解决方案**：
```bash
# 重新初始化数据库
docker-compose -f docker-compose.prod.yml exec web alembic upgrade head

# 重启服务
docker-compose -f docker-compose.prod.yml restart web
```

#### Worker 任务积压

**症状**：管理台显示队列任务数持续增长

**排查步骤**：
```bash
# 1. 查看 Worker 状态
docker-compose -f docker-compose.prod.yml exec worker \
  celery -A src.tasks.celery_app inspect active

# 2. 查看失败任务
docker-compose -f docker-compose.prod.yml exec worker \
  celery -A src.tasks.celery_app inspect reserved

# 3. 查看 Worker 日志
docker-compose -f docker-compose.prod.yml logs worker | grep ERROR
```

**解决方案**：
```bash
# 增加 Worker 并发数（临时）
docker-compose -f docker-compose.prod.yml exec worker \
  celery -A src.tasks.celery_app control pool_grow 2

# 或修改 docker-compose.prod.yml，增加 --concurrency 参数后重启

# 清除失败任务（慎用）
docker-compose -f docker-compose.prod.yml exec worker \
  celery -A src.tasks.celery_app purge
```

#### 邮件发送失败

**症状**：delivery_log 显示大量失败记录

**排查步骤**：
```bash
# 1. 查看 SMTP 配置
docker-compose -f docker-compose.prod.yml exec web env | grep SMTP

# 2. 测试 SMTP 连接
docker-compose -f docker-compose.prod.yml exec web python -c "
from src.mailer.smtp_client import SMTPClient
import asyncio
async def test():
    client = SMTPClient()
    await client.send_email('test@example.com', 'Test', '<p>Test</p>')
asyncio.run(test())
"

# 3. 检查收件人白名单
docker-compose -f docker-compose.prod.yml exec web python scripts/list_recipients.py
```

**解决方案**：
- SMTP 授权码过期：更新 `SMTP_PASS` 环境变量
- 被限速：降低 `MAIL_RATE_LIMIT_PER_SEC` 配置
- 收件人地址错误：管理台修正或移除

#### 磁盘空间不足

**排查步骤**：
```bash
# 1. 查看磁盘使用
df -h

# 2. 查看 Docker 卷占用
docker system df -v

# 3. 查看日志文件大小
du -sh /var/lib/docker/containers/*/*-json.log
```

**清理方案**：
```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的卷
docker volume prune

# 清理旧日志
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U fin_user -d fin_daily_report -c "DELETE FROM delivery_log WHERE created_at < NOW() - INTERVAL '90 days';"
```

### 9.2 日常运维命令

**服务管理**：
```bash
# 启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 停止所有服务
docker-compose -f docker-compose.prod.yml down

# 重启特定服务
docker-compose -f docker-compose.prod.yml restart web worker

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看资源使用
docker stats
```

**滚动更新（零停机）**：
```bash
# 1. 拉取新镜像
docker-compose -f docker-compose.prod.yml pull

# 2. 逐个重启服务
docker-compose -f docker-compose.prod.yml up -d --no-deps --build web
docker-compose -f docker-compose.prod.yml up -d --no-deps --build worker
docker-compose -f docker-compose.prod.yml up -d --no-deps --build beat

# 3. 验证服务
curl http://localhost:8000/healthz
```

**数据库管理**：
```bash
# 进入数据库
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U fin_user -d fin_daily_report

# 查看表大小
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U fin_user -d fin_daily_report -c "\dt+"

# 清理旧数据
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U fin_user -d fin_daily_report -c "DELETE FROM articles WHERE created_at < NOW() - INTERVAL '180 days';"
```

**Redis 管理**：
```bash
# 进入 Redis CLI
docker-compose -f docker-compose.prod.yml exec redis redis-cli

# 查看内存使用
docker-compose -f docker-compose.prod.yml exec redis redis-cli info memory

# 清空缓存（慎用）
docker-compose -f docker-compose.prod.yml exec redis redis-cli FLUSHDB
```

### 9.3 性能优化建议

**2C/2G 服务器优化配置**：

1. **限制 Playwright 并发**：
   ```bash
   # .env.prod
   CRAWL_CONCURRENCY_WEB=1  # 降低到 1，避免内存溢出
   ```

2. **优化 Celery Worker**：
   ```yaml
   # docker-compose.prod.yml
   worker:
     command: celery -A src.tasks.celery_app worker
              --loglevel=info
              --concurrency=2
              --max-tasks-per-child=50  # 防止内存泄漏
              --prefetch-multiplier=1   # 减少预取
   ```

3. **启用 Redis LRU 淘汰**：
   ```yaml
   redis:
     command: redis-server
              --maxmemory 256mb
              --maxmemory-policy allkeys-lru
   ```

4. **PostgreSQL 连接池**：
   ```python
   # src/db/session.py
   engine = create_engine(
       settings.DATABASE_URL,
       pool_size=5,  # 限制连接数
       max_overflow=10,
       pool_pre_ping=True
   )
   ```

---

## 10. 安全加固

### 10.1 机密管理

**Docker Secrets（推荐）**：

```yaml
# docker-compose.prod.yml
secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
  smtp_password:
    file: ./secrets/smtp_password.txt

services:
  web:
    secrets:
      - postgres_password
      - smtp_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      SMTP_PASS_FILE: /run/secrets/smtp_password
```

修改 `src/config/settings.py` 支持文件读取：

```python
@validator("POSTGRES_PASSWORD", pre=True)
def load_postgres_password(cls, v):
    if file_path := os.getenv("POSTGRES_PASSWORD_FILE"):
        return Path(file_path).read_text().strip()
    return v
```

### 10.2 网络隔离

```yaml
# docker-compose.prod.yml
networks:
  frontend:  # Web 对外网络
  backend:   # 数据库内部网络

services:
  web:
    networks:
      - frontend
      - backend
    ports:
      - "8000:8000"

  postgres:
    networks:
      - backend  # 仅内部访问
    # 移除 ports 配置，禁止外部访问
```

### 10.3 反向代理（Nginx）

**配置示例** (`nginx/finrep.conf`)：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # HTTPS 重定向
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # 静态资源缓存
    location /static/ {
        alias /app/src/web/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # 代理到 Web 服务
    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持（如需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 限流
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;
    location /login {
        limit_req zone=login_limit burst=2 nodelay;
        proxy_pass http://web:8000;
    }
}
```

**添加到 docker-compose.prod.yml**：

```yaml
services:
  nginx:
    image: nginx:alpine
    container_name: finrep_nginx_prod
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/finrep.conf:/etc/nginx/conf.d/default.conf
      - ./nginx/certs:/etc/nginx/certs
      - ./src/web/static:/app/src/web/static:ro
    depends_on:
      - web
    restart: unless-stopped
```

---

## 11. 验收标准（Phase 3A 完成标准）

### 11.1 功能验收

- [ ] **一键部署**：开发环境 `docker-compose.dev.yml up -d` 后所有容器健康
- [ ] **生产部署**：`docker-compose.prod.yml` 在 2C/2G 服务器成功运行 ≥72 小时
- [ ] **健康检查**：`/healthz` 接口返回 200，包含 Postgres/Redis/Celery 状态
- [ ] **定时任务**：Celery Beat 在 06:00 自动触发日报流程
- [ ] **邮件投递**：06:20 前完成邮件发送，`delivery_log` 记录完整
- [ ] **数据持久化**：容器重启后数据不丢失（PostgreSQL 卷）
- [ ] **日志滚动**：生产环境日志文件自动轮转，不超过 150MB

### 11.2 性能验收

- [ ] **资源限制**：Web ≤512MB，Worker ≤1GB，Beat ≤256MB
- [ ] **并发处理**：Celery Worker 同时处理 2 个任务不 OOM
- [ ] **响应时间**：`/healthz` 接口响应时间 <500ms（P95）
- [ ] **内存稳定性**：运行 3 天后内存增长 <10%

### 11.3 可观测性验收

- [ ] **容器监控**：`docker stats` 显示所有容器资源使用
- [ ] **日志查询**：`docker-compose logs` 可查询最近 7 天日志
- [ ] **系统监控**：管理台 `/admin/status` 显示实时指标与趋势图
- [ ] **告警机制**：容器崩溃后自动重启（restart: unless-stopped）

### 11.4 安全验收

- [ ] **机密隔离**：`.env.prod` 不包含在镜像中
- [ ] **非 root 运行**：应用容器使用非特权用户（UID 1000）
- [ ] **网络隔离**：数据库容器不暴露外部端口（生产环境）
- [ ] **HTTPS 支持**：Nginx 反向代理配置 TLS（可选，推荐生产环境）

---

## 12. 云端部署策略（阿里云 4C8G ECS 环境）

### 12.0 部署目标与环境说明

**目标**：快速部署到阿里云 4核8G ECS，支持少量用户（<50人）使用，非隐私敏感数据

**环境资源**：
- 阿里云 ECS：4核8G 内存，40GB+ 磁盘
- 用户规模：管理员 1-5人，邮件收件人 <50人
- 数据安全级别：非隐私敏感，允许明文配置简化部署

**部署原则**：
- ✅ **P0 - 立即解决**：阻塞部署的问题，必须在上线前完成
- ⏳ **P1 - 后续优化**：不影响基本功能，可以上线后逐步改进
- 🔄 **P2 - 长期规划**：安全加固、高可用等企业级特性

---

### 12.1 最小可行部署方案（MVP Deploy）- 3天上线

#### 阶段目标
在 **3天内** 完成部署，系统能够：
- ✅ 在 ECS 上通过 Docker Compose 一键启动
- ✅ 定时采集信息源并生成日报
- ✅ 发送邮件给收件人列表
- ✅ 管理员可通过 Web 界面管理系统
- ✅ 基本的日志记录和错误追踪

#### 快速部署检查清单

**Day 1 - 容器化基础（P0）**
```yaml
- [ ] 编写基础 Dockerfile（基于 python:3.11-slim + playwright）
- [ ] 创建简化版 docker-compose.prod.yml（web + worker + beat + postgres + redis）
- [ ] 配置 .env.prod 环境变量（明文配置，简化部署）
- [ ] 测试本地 Docker 环境启动成功
```

**Day 2 - ECS 部署与调试（P0）**
```yaml
- [ ] 在 ECS 安装 Docker + Docker Compose
- [ ] 上传代码和配置文件到 ECS
- [ ] 启动服务并验证各组件健康状态
- [ ] 配置防火墙开放 8000 端口
- [ ] 执行数据库迁移和初始数据导入
```

**Day 3 - 功能验证与优化（P0）**
```yaml
- [ ] 手动触发采集任务，验证动态采集功能
- [ ] 验证定时任务自动执行（Celery Beat）
- [ ] 测试邮件发送功能
- [ ] 配置域名解析（可选）
- [ ] 添加基本的监控脚本（docker stats）
```

---

### 12.2 P0 任务详解（阻塞部署，必须解决）

#### P0-1：完成应用容器化 【Day 1，4小时】

**现状问题**：
- 应用依赖 `scripts/start_all.sh` 在本地虚拟环境启动
- 云端无法使用 WSL 和交互式环境

**最小化方案**（跳过多阶段构建优化）：

### 12.1 容器化未完成风险 【P0 - 必须解决】

**现状问题**：
- `docker-compose.yml` 仅启动 Postgres/Redis，Web/Celery 仍依赖 `scripts/start_all.sh` 在本机 `.venv` 中用 `nohup + uvicorn --reload` 拉起
- 云端节点无法依赖交互式虚拟环境，`--reload` 和 PID 文件管理不适用于生产环境

**改进方案**：
```yaml
# 任务清单
- [ ] 编写多阶段 Dockerfile，包含 poetry install + playwright install chromium
- [ ] 在 docker-compose.prod.yml 中拆分服务：
      - web: gunicorn -k uvicorn.workers.UvicornWorker --workers 2
      - celery-worker: celery worker --concurrency=2
      - celery-beat: celery beat
      - scheduler: 独立定时调度服务（可选）
- [ ] 移除 scripts/start_all.sh 对 nohup/PID 文件的依赖
- [ ] 为每个服务配置健康检查与自动重启策略
```

**涉及文件**：
- `docker-compose.yml:2-31`
- `scripts/start_all.sh:7-140`

---

### 12.2 代理配置硬编码风险 【P0 - 必须解决】

**现状问题**：
- `.env.example` 将 `PLAYWRIGHT_PROXY` 硬编码为 `http://127.0.0.1:7890`
- BrowserPool 和智能代理策略直接注入该地址到 Playwright 上下文
- 云上容器若无同机代理会导致所有国外站点挂起或超时
- 域名白名单硬编码在代码中，无法动态更新

**改进方案**：
```yaml
# 任务清单
- [ ] 修改 BrowserPool/ProxyStrategy，支持通过环境变量动态配置代理：
      - PLAYWRIGHT_PROXY_ENABLED=true/false
      - PLAYWRIGHT_PROXY_URL（留空则不使用代理）
      - PROXY_DOMESTIC_DOMAINS（国内白名单域名，逗号分隔）
- [ ] 将域名白名单迁移到数据库表（proxy_domain_rules）：
      | id | domain         | use_proxy | priority |
      |----|----------------|-----------|----------|
      | 1  | *.cn          | false     | 100      |
      | 2  | *.baidu.com   | false     | 90       |
      | 3  | *             | true      | 0        |
- [ ] 在管理后台添加"代理规则管理"页面，支持 CRUD 操作
- [ ] 更新文档，说明不同部署环境的代理配置方案：
      - 本地开发: http://127.0.0.1:7890
      - 云端 VPC: http://proxy.internal:8080
      - 无代理环境: 留空或 false
```

**涉及文件**：
- `.env.example:29-35`
- `src/crawlers/browser_pool.py:72-104`
- `src/crawlers/proxy_strategy.py:23-145`

---

### 12.3 Playwright 运行时依赖缺失 【P0 - 必须解决】

**现状问题**：
- Dockerfile 未安装 `playwright install-deps` 需要的系统库（字体/glib/nss 等）
- 容器启动时因缺少共享内存或 sandbox 权限导致 Chromium 启动失败
- BrowserPool 强制使用 `--no-sandbox/--disable-dev-shm-usage` 存在安全隐患

**改进方案**：
```dockerfile
# Dockerfile 改进示例
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy as base

# 或使用自定义基础镜像
FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    fonts-wqy-zenhei && \
    playwright install chromium && \
    playwright install-deps && \
    rm -rf /var/lib/apt/lists/*

# 配置共享内存
RUN mkdir -p /dev/shm && chmod 1777 /dev/shm
```

```yaml
# docker-compose.prod.yml 配置
services:
  worker:
    shm_size: '256mb'  # 增加共享内存
    security_opt:
      - seccomp:unconfined  # 放宽 seccomp 限制（仅在必要时）
    # 或使用非 root 用户 + CAP_SYS_ADMIN
    cap_add:
      - SYS_ADMIN
    user: "1000:1000"
```

**任务清单**：
```yaml
- [ ] 更新 Dockerfile，集成官方 Playwright 基础镜像或完整安装依赖
- [ ] 配置容器 shm_size 和 seccomp 策略
- [ ] 测试在无 --no-sandbox 模式下运行（优先推荐）
- [ ] 添加健康检查脚本，验证 Chromium 可正常启动
```

**涉及文件**：
- `Dockerfile` （待创建完整版本）
- `src/crawlers/browser_pool.py:58-66`

---

### 12.4 数据库连接池配置错误 【P1 - 高优先级】

**现状问题**：
- `src/db/session.py` 强制使用 `NullPool`，每个请求新建 TCP 连接
- 多进程 FastAPI/Celery 场景下会耗尽托管数据库连接数
- 未配置连接池参数（`pool_size`/`max_overflow`）

**改进方案**：
```python
# src/db/session.py 改进
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from src.config.settings import settings

# 根据环境选择连接池策略
if settings.ENV == "production":
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,          # 基础连接数
        max_overflow=10,      # 最大溢出连接
        pool_timeout=30,      # 连接超时
        pool_recycle=3600,    # 连接回收时间（1小时）
        pool_pre_ping=True,   # 连接前检查有效性
        echo=False
    )
else:
    # 开发环境保持原有配置
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        echo=True
    )
```

**任务清单**：
```yaml
- [ ] 修改 src/db/session.py，根据 ENV 环境变量动态选择连接池
- [ ] 为生产环境配置 QueuePool 参数（考虑 2C/2G 资源限制）
- [ ] 可选：在数据库前部署 PgBouncer 连接池代理
- [ ] 监控数据库连接数，添加告警规则（>80% 触发）
```

**涉及文件**：
- `src/db/session.py:13-22`

---

### 12.5 日志与调度状态持久化缺失 【P1 - 高优先级】

**现状问题**：
- Loguru 默认写 `logs/app_*.log` 等本地文件，容器重启后丢失
- `start_all.sh` 在项目根目录创建 `.pids` 文件
- `celerybeat-schedule.db` 存储在容器内，无法横向扩展

**改进方案**：
```python
# 方案一：日志输出到 STDOUT（推荐）
from loguru import logger
import sys

logger.remove()  # 移除默认处理器
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO" if settings.ENV == "production" else "DEBUG"
)

# 方案二：集中日志（ELK/CloudWatch）
logger.add(
    "syslog://logstash.internal:5140",  # Logstash 接收端
    format="{message}",
    serialize=True  # JSON 格式
)
```

```yaml
# docker-compose.prod.yml 日志配置
services:
  web:
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "3"
      # 或使用 fluentd/syslog driver
      # driver: "fluentd"
      # options:
      #   fluentd-address: "localhost:24224"
```

```yaml
# Celery Beat 持久化
services:
  beat:
    command: celery -A src.tasks.celery_app beat --schedule /data/celerybeat-schedule.db
    volumes:
      - beat_schedule:/data  # 持久化卷
volumes:
  beat_schedule:
```

**任务清单**：
```yaml
- [ ] 修改 src/utils/logger.py，生产环境输出到 STDOUT
- [ ] 移除 scripts/start_all.sh 对 .pids 文件的依赖
- [ ] 配置 Celery Beat 使用持久化卷存储 schedule
- [ ] 添加日志轮转与归档策略（保留 30 天）
- [ ] 可选：集成 ELK Stack 或云厂商日志服务
```

**涉及文件**：
- `src/utils/logger.py:11-82`
- `scripts/start_all.sh` （待移除）
- `docker-compose.prod.yml`

---

### 12.6 外部依赖网络策略缺失 【P1 - 高优先级】

**现状问题**：
- LLM 路由器并发访问 DeepSeek/Qwen API（国外域名）
- 邮件发送通过 SSL 465 端口，很多云供应商默认封禁
- 未配置重试、熔断与降级策略

**改进方案**：
```python
# src/nlp/provider_router.py 改进
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class ProviderRouter:
    def __init__(self):
        # 配置超时与重试
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(90.0, connect=10.0),
            limits=httpx.Limits(max_connections=10),
            transport=httpx.AsyncHTTPTransport(retries=3)
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def call_provider(self, provider: str, prompt: str):
        try:
            response = await self.client.post(...)
            return response.json()
        except httpx.ConnectTimeout:
            logger.error(f"Provider {provider} connection timeout, check network policy")
            raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limit
                logger.warning(f"Provider {provider} rate limited, retrying...")
                raise
            else:
                return None  # 降级处理
```

**网络策略检查清单**：
```yaml
- [ ] 申请云厂商出站白名单：
      - api.deepseek.com（DeepSeek API）
      - dashscope.aliyuncs.com（Qwen API）
      - smtp.exmail.qq.com:465（企业邮箱）
- [ ] 配置 HTTP 代理或 VPN 转发服务
- [ ] 为所有外部 API 调用添加 timeout/retry/circuit breaker
- [ ] 在管理后台添加"外部服务连通性测试"工具
- [ ] 监控外部 API 成功率，<95% 时触发告警
```

**涉及文件**：
- `src/nlp/provider_router.py:24-190`
- `src/mailer/smtp_client.py:34-123`

---

### 12.7 安全配置不足 【P1 - 高优先级】

**现状问题**：
- `ALLOWED_HOSTS`/`CORS_ORIGINS`/`JWT_SECRET_KEY` 仍是示例值
- Web 模块未配置 HTTPS/反向代理信任
- 环境变量中直接内嵌 API Key 和密码

**改进方案**：

**1. 安全配置强化**：
```python
# src/config/settings.py
class Settings(BaseSettings):
    # 强制生产环境覆盖
    ALLOWED_HOSTS: list[str] = Field(
        default=["*"] if ENV == "development" else [],
        description="允许的域名列表，生产环境必须显式配置"
    )

    CORS_ORIGINS: list[str] = Field(
        default=["*"] if ENV == "development" else [],
        description="CORS 允许的源"
    )

    JWT_SECRET_KEY: str = Field(
        ...,  # 必填
        min_length=32,
        description="JWT 签名密钥，至少 32 字符"
    )

    @validator("JWT_SECRET_KEY")
    def validate_jwt_secret(cls, v, values):
        if values.get("ENV") == "production" and v == "change-this-to-a-very-long-random-string":
            raise ValueError("生产环境必须更换 JWT_SECRET_KEY")
        return v
```

**2. 密钥管理（Docker Secrets）**：
```yaml
# docker-compose.prod.yml
secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
  deepseek_api_key:
    file: ./secrets/deepseek_api_key.txt
  smtp_password:
    file: ./secrets/smtp_password.txt

services:
  web:
    secrets:
      - postgres_password
      - deepseek_api_key
      - smtp_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      PROVIDER_DEEPSEEK_API_KEY_FILE: /run/secrets/deepseek_api_key
      SMTP_PASS_FILE: /run/secrets/smtp_password
```

```python
# src/config/settings.py 支持文件读取
@validator("POSTGRES_PASSWORD", pre=True)
def load_from_file(cls, v):
    if file_path := os.getenv("POSTGRES_PASSWORD_FILE"):
        return Path(file_path).read_text().strip()
    return v
```

**3. 反向代理配置**：
```python
# src/web/app.py
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

if settings.ENV == "production":
    # 强制 HTTPS
    app.add_middleware(HTTPSRedirectMiddleware)

    # 限制允许的 Host 头
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

    # 信任反向代理的 X-Forwarded-* 头
    app.middleware("http")(trust_forwarded_headers)
```

**任务清单**：
```yaml
- [ ] 更新 src/config/settings.py，生产环境强制验证安全参数
- [ ] 实现 Docker Secrets 支持，移除 .env 中的明文密钥
- [ ] 添加 TrustedHostMiddleware 和 HTTPS 重定向
- [ ] 配置 Nginx 反向代理，终结 TLS
- [ ] 在部署文档中强调生产环境配置检查清单
- [ ] 使用工具生成强密码（如 openssl rand -base64 32）
```

**涉及文件**：
- `src/config/settings.py:94-111`
- `.env.example:6-19,76-84`
- `docker-compose.prod.yml`

---

### 12.8 改进优先级与时间规划

| 优先级 | 风险项 | 预计工时 | 目标完成阶段 |
|--------|--------|----------|--------------|
| **P0** | 容器化未完成 | 3 天 | Phase 3A Week 1 |
| **P0** | 代理配置硬编码 | 2 天 | Phase 3A Week 1 |
| **P0** | Playwright 依赖缺失 | 1 天 | Phase 3A Week 1 |
| **P1** | 数据库连接池错误 | 0.5 天 | Phase 3A Week 2 |
| **P1** | 日志持久化缺失 | 1 天 | Phase 3A Week 2 |
| **P1** | 外部依赖网络策略 | 1.5 天 | Phase 3A Week 2 |
| **P1** | 安全配置不足 | 2 天 | Phase 3A Week 2 |

**Phase 3A 调整后验收标准**：
- [ ] 所有 P0 风险项已解决并通过测试
- [ ] 完整的 Docker 镜像可在无本地虚拟环境的云服务器上运行
- [ ] 代理配置可通过环境变量动态调整，域名规则存储在数据库
- [ ] Playwright 在标准容器环境中稳定运行 ≥24 小时
- [ ] 数据库连接池在生产环境未出现连接耗尽
- [ ] 所有 P1 风险项已完成或有明确的缓解措施
- [ ] 通过安全扫描（无高危漏洞），密钥已迁移到 Secrets

---

## 13. 下一阶段规划（Phase 3B - 后续增强）

### 13.1 监控告警（Prometheus + Grafana）

- 集成 Prometheus Exporter（Postgres、Redis、Celery）
- Grafana 仪表盘：队列积压、任务成功率、LLM 费用趋势
- 告警规则：容器崩溃、任务失败率 >10%、磁盘使用 >80%

### 13.2 CI/CD 流水线

- GitHub Actions / GitLab CI 自动化测试
- 镜像构建与漏洞扫描（Trivy）
- 自动部署到生产环境（Webhook + docker-compose pull）

### 13.3 高可用增强

- PostgreSQL 主从复制（Patroni + etcd）
- Redis Sentinel 哨兵模式
- Celery Worker 多实例负载均衡
- Nginx 负载均衡（多 Web 实例）

### 13.4 业务增强

- 多租户支持（SaaS 化）
- WebSocket 实时推送（报告生成进度）
- 移动端适配（响应式设计）
- 多语言支持（i18n）

---

## 附录

### A. 完整部署清单

**目录结构**：
```
V4/
├── docker-compose.dev.yml      # 开发环境编排
├── docker-compose.prod.yml     # 生产环境编排
├── Dockerfile                  # 应用镜像构建
├── .env.example                # 环境变量模板
├── .env.prod                   # 生产环境配置（不提交）
├── alembic.ini                 # 数据库迁移配置
├── pyproject.toml              # Poetry 依赖管理
├── src/                        # 应用源码
├── scripts/                    # 运维脚本
│   ├── backup_db.sh            # 数据库备份
│   ├── celery_health_check.sh  # Celery 健康检查
│   └── seed_test_data.py       # 测试数据导入
├── nginx/                      # Nginx 配置（可选）
│   ├── finrep.conf
│   └── certs/
└── docs/                       # 文档