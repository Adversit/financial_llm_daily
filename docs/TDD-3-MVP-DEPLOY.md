# 金融情报日报系统 · 最小可行部署方案

（TDD-3 MVP Deploy Supplement | 阿里云 4C8G ECS 快速上线指南）

**版本**：v4.0-mvp
**日期**：2025-11-13（Asia/Shanghai）
**目标**：3天内完成阿里云ECS部署，支持<50人使用，非隐私敏感环境

---

## 1. 部署目标与环境说明

### 1.1 目标定义

**快速上线**：在3天内将系统部署到生产环境，实现基本功能可用

**环境资源**：
- 服务器：阿里云 ECS 4核8G内存，40GB+磁盘
- 用户规模：管理员1-5人，邮件收件人<50人
- 数据安全级别：非隐私敏感，可使用明文配置简化部署流程

### 1.2 部署原则与优先级

| 优先级 | 分类 | 说明 | 时间 |
|--------|------|------|------|
| **P0** | 立即解决 | 阻塞部署的问题，必须在上线前完成 | Day 1-2 |
| **P1** | 后续优化 | 不影响基本功能，可以上线后逐步改进 | Week 2-3 |
| **P2** | 长期规划 | 安全加固、高可用等企业级特性 | Phase 3B |

**MVP哲学**：先让系统跑起来，再逐步优化

---

## 2. 3天部署路线图

### Day 1 - 本地容器化验证（P0）

**目标**：完成Docker镜像构建，本地环境验证通过

| 时段 | 任务 | 工时 | 验收标准 |
|------|------|------|----------|
| 上午 | 编写Dockerfile | 2h | `docker build` 成功，镜像<2GB |
| 上午 | 创建docker-compose.prod.yml | 1h | 包含web/worker/beat/postgres/redis |
| 下午 | 配置.env.prod环境变量 | 1h | 所有必填项已填写 |
| 下午 | 本地Docker环境启动测试 | 2h | `docker-compose up -d` 所有容器Running |
| 晚上 | 数据库迁移和初始数据导入 | 1h | 管理员账号可登录 |

**Day 1 完成标志**：
```bash
# 所有容器健康运行
docker-compose -f docker-compose.prod.yml ps
# NAME                  STATUS          PORTS
# finrep_web_prod       Up (healthy)    0.0.0.0:8000->8000/tcp
# finrep_worker_prod    Up              -
# finrep_beat_prod      Up              -
# finrep_postgres_prod  Up (healthy)    5432/tcp
# finrep_redis_prod     Up (healthy)    6379/tcp

# Web界面可访问
curl http://localhost:8000/healthz
# {"status":"ok","postgres":"connected","redis":"connected"}
```

---

### Day 2 - 阿里云ECS部署（P0）

**目标**：代码上传到ECS，系统在云端成功运行

| 时段 | 任务 | 工时 | 验收标准 |
|------|------|------|----------|
| 上午 | ECS环境准备 | 1.5h | Docker+Compose安装完成 |
| 上午 | 代码上传和配置文件修改 | 1h | git clone或scp上传完成 |
| 下午 | 启动服务并验证健康状态 | 2h | 所有容器Running+健康检查通过 |
| 下午 | 配置防火墙和安全组 | 0.5h | 8000端口可公网访问 |
| 晚上 | 数据库迁移和初始数据 | 1h | 添加信息源和收件人 |

**Day 2 完成标志**：
```bash
# ECS上系统启动成功
ssh user@your-ecs-ip
cd /path/to/project
docker-compose -f docker-compose.prod.yml ps
# 所有容器Running

# 公网可访问管理后台
curl http://your-ecs-ip:8000/admin
# 返回登录页面HTML
```

---

### Day 3 - 功能验证与优化（P0）

**目标**：验证核心业务流程，修复问题，确保系统可用

| 时段 | 任务 | 工时 | 验收标准 |
|------|------|------|----------|
| 上午 | 手动触发采集任务测试 | 1.5h | 至少5篇文章采集成功 |
| 上午 | 验证LLM抽取功能 | 1h | ExtractionItem有数据，成本记录正常 |
| 下午 | 验证报告生成和邮件发送 | 1.5h | 收件人收到HTML邮件 |
| 下午 | 验证定时任务 | 1h | Celery Beat正常调度 |
| 晚上 | 监控脚本和文档整理 | 2h | 运维文档+监控命令 |

**Day 3 完成标志**：
```bash
# 完整流程验证清单
✅ RSS信息源采集成功
✅ 动态网页采集成功（Playwright）
✅ LLM抽取标题/摘要/关键词成功
✅ 日报生成并打分成功
✅ 邮件发送成功（至少1个收件人）
✅ 定时任务配置正确（06:00触发）
✅ 管理后台所有功能可用
✅ 系统监控页面显示正常
```

---

## 3. P0任务详细实施方案

### 3.1 编写Dockerfile（Day 1上午）

**最小化方案**：使用官方Playwright镜像，避免手动安装依赖

**文件**：`Dockerfile`

```dockerfile
# 阶段1：使用官方Playwright Python镜像（已包含Chromium和所有依赖）
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# 安装Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# 复制依赖文件
COPY pyproject.toml poetry.lock ./

# 安装Python依赖（不创建虚拟环境）
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi && \
    rm -rf /root/.cache/pypoetry

# 复制应用代码
COPY src ./src
COPY alembic.ini ./
COPY scripts ./scripts

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 暴露端口
EXPOSE 8000

# 默认命令（通过docker-compose覆盖）
CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**构建命令**：
```bash
docker build -t finrep/app:mvp .
```

**预计镜像大小**：1.5-2GB（Playwright基础镜像约1.2GB + Python依赖约300MB）

---

### 3.2 创建docker-compose.prod.yml（Day 1上午）

**简化方案**：使用内置Postgres/Redis，暂不使用外部托管服务

**文件**：`docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: finrep_postgres_prod
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-fin_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-change_me_in_prod}
      POSTGRES_DB: ${POSTGRES_DB:-fin_daily_report}
      TZ: Asia/Shanghai
    ports:
      - "5432:5432"  # 暴露端口：支持宿主机备份/调试
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-fin_user}"]
      interval: 10s
      timeout: 5s
      retries: 5
    # 资源限制（4C8G环境）
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  redis:
    image: redis:7-alpine
    container_name: finrep_redis_prod
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"  # 暴露端口：支持Redis CLI调试
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  web:
    image: finrep/app:mvp
    container_name: finrep_web_prod
    command: uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --workers 2
    ports:
      - "8000:8000"
    env_file:
      - .env.prod
    environment:
      - ENV=production
    volumes:
      - ./logs:/app/logs  # 日志挂载（MVP阶段保留文件日志）
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G

  worker:
    image: finrep/app:mvp
    container_name: finrep_worker_prod
    command: celery -A src.tasks.celery_app worker --loglevel=info --concurrency=2 --max-tasks-per-child=50
    env_file:
      - .env.prod
    environment:
      - ENV=production
    volumes:
      - ./logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    shm_size: '512mb'  # Playwright需要共享内存
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 3G

  beat:
    image: finrep/app:mvp
    container_name: finrep_beat_prod
    command: celery -A src.tasks.celery_app beat --loglevel=info --schedule /data/celerybeat-schedule.db
    env_file:
      - .env.prod
    environment:
      - ENV=production
    volumes:
      - ./logs:/app/logs
      - beat_schedule:/data  # 持久化调度信息
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

volumes:
  postgres_data:
  redis_data:
  beat_schedule:

networks:
  default:
    name: finrep-net
```

---

### 3.3 配置.env.prod环境变量（Day 1下午）

**MVP简化原则**：使用明文配置，跳过Docker Secrets

**文件**：`.env.prod`（**不要提交到Git**）

```bash
# ========== 环境配置 ==========
ENV=production
TZ=Asia/Shanghai

# ========== 数据库配置 ==========
DATABASE_URL=postgresql://fin_user:YOUR_DB_PASSWORD@postgres:5432/fin_daily_report
POSTGRES_USER=fin_user
POSTGRES_PASSWORD=YOUR_DB_PASSWORD  # 修改为强密码
POSTGRES_DB=fin_daily_report

# ========== Redis配置 ==========
REDIS_URL=redis://redis:6379/0

# ========== LLM Provider配置 ==========
# DeepSeek
PROVIDER_DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # 填写真实API Key
PROVIDER_DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
PROVIDER_DEEPSEEK_MODEL=deepseek-chat

# Qwen（优先使用，成本低）
PROVIDER_QWEN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # 填写真实API Key
PROVIDER_QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PROVIDER_QWEN_MODEL=qwen-plus

# ========== 邮件配置 ==========
SMTP_HOST=smtp.exmail.qq.com  # 企业邮箱/QQ邮箱
SMTP_PORT=465
SMTP_USER=your-email@example.com  # 发件人邮箱
SMTP_PASS=your-smtp-password  # SMTP授权码
SMTP_FROM=your-email@example.com

# ========== JWT配置 ==========
JWT_SECRET_KEY=请使用openssl_rand_-base64_32生成随机密钥  # 务必修改！
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# ========== Playwright配置 ==========
# 代理配置说明：
# - 如果ECS上没有代理，留空PLAYWRIGHT_PROXY，系统会跳过国外站点采集
# - 如果有阿里云VPC代理或其他代理服务，填写代理地址
# - 推荐使用阿里云NAT网关或第三方HTTP代理服务
PLAYWRIGHT_PROXY=  # 留空或填写代理地址（如 http://proxy.internal:8080）
PLAYWRIGHT_MAX_BROWSERS=3  # 4C8G环境限制并发
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_TIMEOUT_MS=30000

# ========== 采集并发配置 ==========
CRAWL_CONCURRENCY_RSS=5
CRAWL_CONCURRENCY_WEB=1  # 动态采集降低并发
CRAWL_CONCURRENCY_DYNAMIC=1

# ========== 其他配置 ==========
LLM_TIMEOUT_SEC=90
REPORT_TOPN=5
MAIL_BATCH_LIMIT=50
MAIL_RATE_LIMIT_PER_SEC=1.0
```

**安全提示（MVP阶段可暂时跳过）**：
- ⚠️ 数据库密码使用强密码（至少16位，包含大小写字母+数字+符号）
- ⚠️ JWT密钥必须随机生成：`openssl rand -base64 32`
- ⚠️ .env.prod添加到.gitignore，避免泄露

---

### 3.4 代理配置问题处理（Day 1下午，重要！）

**问题说明**：
- 当前系统使用 `http://127.0.0.1:7890` 作为代理，智能代理策略会根据域名自动决定是否使用
- ECS上默认没有本地代理服务，需要根据实际情况选择方案

#### 方案A：只采集国内站点（最简单，推荐MVP）

**适用场景**：快速上线，暂时只关注国内金融信息

**配置步骤**：
```bash
# .env.prod中设置
PLAYWRIGHT_PROXY=  # 留空表示不使用代理
```

**系统行为**：
- ProxyStrategy会识别到无代理配置
- 国内站点（sina.com.cn、caixin.com等）正常采集
- 国外站点（bbc.com、reuters.com等）会超时失败，但不影响系统运行
- 后续可以添加代理后自动恢复国外站点采集

**验证**：
```bash
# 测试采集任务
docker-compose -f docker-compose.prod.yml exec worker \
  celery -A src.tasks.celery_app call src.tasks.crawl_tasks.crawl_rss_task --args='[1]'

# 查看日志，确认国内站点采集成功
docker-compose -f docker-compose.prod.yml logs worker | grep "crawl"
```

---

#### 方案B：使用阿里云NAT网关（推荐生产环境）

**适用场景**：需要采集国外站点，预算充足

**成本**：约¥50-100/月

**配置步骤**：
1. 在阿里云控制台创建NAT网关
2. 配置SNAT规则（ECS通过NAT访问公网）
3. 配置DNAT规则（如需要）
4. 在ECS上测试外网连通性：
   ```bash
   curl -I https://www.bbc.com
   ```

5. .env.prod配置：
   ```bash
   PLAYWRIGHT_PROXY=  # NAT网关模式不需要代理配置
   ```

**优点**：
- 稳定可靠，阿里云官方支持
- 无需额外代理服务
- 直连国外网站

---

#### 方案C：使用第三方HTTP代理（灵活性高）

**适用场景**：需要国外站点，预算有限

**推荐服务**：
- 快代理（https://www.kuaidaili.com）：约¥50/月
- 阿布云（https://www.abuyun.com）：约¥80/月
- 芝麻代理（http://www.zhimaruanjian.com）：约¥60/月

**配置步骤**：
1. 注册第三方代理服务，获取代理地址
2. .env.prod配置：
   ```bash
   # 示例：快代理提供的HTTP代理
   PLAYWRIGHT_PROXY=http://proxy-server.com:8080
   # 或带认证的代理
   PLAYWRIGHT_PROXY=http://username:password@proxy-server.com:8080
   ```

3. 验证代理连通性：
   ```bash
   # 在ECS上测试
   curl -x http://proxy-server.com:8080 https://www.bbc.com
   ```

**优点**：
- 成本较低
- 灵活切换
- 支持高匿IP池

---

#### 方案D：在ECS上部署本地代理（适合技术团队）

**适用场景**：技术能力强，希望自建代理

**工具选择**：
- V2Ray：功能强大，配置复杂
- Clash：界面友好，适合个人使用
- Tinyproxy：轻量级HTTP代理

**Tinyproxy部署示例**：
```bash
# 1. 安装Tinyproxy
apt-get update && apt-get install -y tinyproxy

# 2. 配置Tinyproxy
vim /etc/tinyproxy/tinyproxy.conf
# 修改：
# Port 8888
# Allow 127.0.0.1
# Allow 172.17.0.0/16  # Docker网络

# 3. 启动服务
systemctl restart tinyproxy
systemctl enable tinyproxy

# 4. 测试代理
curl -x http://127.0.0.1:8888 https://www.bbc.com
```

**docker-compose.prod.yml配置**：
```yaml
# 添加network_mode让容器访问宿主机代理
services:
  worker:
    network_mode: "host"  # 使用宿主机网络
    # 或使用extra_hosts
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

**.env.prod配置**：
```bash
# 容器内访问宿主机代理
PLAYWRIGHT_PROXY=http://host.docker.internal:8888
```

---

#### ⚠️ 重要提醒：代理安全性

无论使用哪种方案，请注意：

1. **不要暴露代理端口到公网**：
   ```bash
   # 错误示例
   ports:
     - "0.0.0.0:7890:7890"  # ❌ 危险！任何人都能用你的代理

   # 正确示例
   ports:
     - "127.0.0.1:7890:7890"  # ✅ 只允许本机访问
   ```

2. **代理认证**：如果使用本地代理，务必配置用户名/密码

3. **定期检查代理日志**：防止被滥用

---

#### MVP阶段推荐方案

**Day 1-3（快速上线）**：
- 使用**方案A**（只采集国内站点）
- 配置：`PLAYWRIGHT_PROXY=`（留空）
- 在信息源管理中只添加国内站点

**Week 2-3（功能完善）**：
- 评估是否需要国外站点
- 如需要，选择**方案B**（阿里云NAT）或**方案C**（第三方代理）

**验证清单**：
```bash
# 1. 检查代理配置
cat .env.prod | grep PLAYWRIGHT_PROXY

# 2. 测试采集任务
docker-compose -f docker-compose.prod.yml exec worker \
  python -c "
from src.crawlers.proxy_strategy import ProxyStrategy
strategy = ProxyStrategy()
print('国内站点需要代理:', strategy.should_use_proxy('https://www.sina.com.cn'))
print('国外站点需要代理:', strategy.should_use_proxy('https://www.bbc.com'))
"

# 3. 查看采集日志
docker-compose -f docker-compose.prod.yml logs worker | grep -E "(proxy|crawl)"
```

---

### 3.5 ECS环境准备（Day 2上午）

**任务清单**：
```bash
# 1. SSH登录ECS
ssh root@your-ecs-ip

# 2. 安装Docker（阿里云镜像源）
curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
systemctl enable docker
systemctl start docker

# 3. 安装Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
docker-compose --version

# 4. 配置Docker国内镜像加速（可选，但推荐）
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://registry.docker-cn.com"
  ]
}
EOF
systemctl restart docker

# 5. 创建项目目录
mkdir -p /opt/finrep
cd /opt/finrep
```

---

### 3.6 代码上传和配置（Day 2上午）

**方案A：Git克隆（推荐）**
```bash
cd /opt/finrep
git clone <your-git-repo-url> .
```

**方案B：SCP上传（适用于无Git仓库）**
```bash
# 在本地执行
cd /path/to/local/V4
tar czf finrep-mvp.tar.gz \
  --exclude='.venv' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='logs' \
  .

scp finrep-mvp.tar.gz root@your-ecs-ip:/opt/finrep/
```

```bash
# 在ECS上执行
cd /opt/finrep
tar xzf finrep-mvp.tar.gz
rm finrep-mvp.tar.gz
```

**配置文件修改**：
```bash
cd /opt/finrep

# 复制环境变量模板
cp .env.example .env.prod

# 编辑配置文件
vim .env.prod
# 修改：数据库密码、LLM API Key、SMTP配置、JWT密钥

# 创建必要目录
mkdir -p logs
chmod 755 logs
```

---

### 3.7 启动服务（Day 2下午）

```bash
cd /opt/finrep

# 1. 构建镜像
docker build -t finrep/app:mvp .
# 预计耗时：5-10分钟（首次构建）

# 2. 启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 3. 查看容器状态
docker-compose -f docker-compose.prod.yml ps
# 确保所有容器状态为 "Up" 或 "Up (healthy)"

# 4. 查看启动日志（排查问题）
docker-compose -f docker-compose.prod.yml logs -f web
# Ctrl+C 退出日志查看

# 5. 执行数据库迁移
docker-compose -f docker-compose.prod.yml exec web \
  alembic upgrade head

# 6. 创建管理员账号（可选：通过管理界面添加白名单后自动创建）
# 或手动插入数据库
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U fin_user -d fin_daily_report -c \
  "INSERT INTO report_recipients (email, type, is_active, created_at)
   VALUES ('admin@example.com', 'whitelist', true, NOW());"

# 7. 验证健康检查
curl http://localhost:8000/healthz
# 预期输出：{"status":"ok","postgres":"connected","redis":"connected"}
```

---

### 3.8 配置防火墙和安全组（Day 2下午）

**阿里云安全组配置**：
1. 登录阿里云控制台
2. 进入 ECS 实例 → 安全组配置
3. 添加入方向规则：

| 端口 | 授权对象 | 说明 | 是否必须 |
|------|---------|------|----------|
| 8000 | 0.0.0.0/0 或特定IP | Web管理后台访问 | ✅ 必须 |
| 5432 | 你的本地IP/32 | PostgreSQL远程备份/调试 | ⚠️ 建议按需开放 |
| 6379 | 你的本地IP/32 | Redis CLI调试 | ⚠️ 建议按需开放 |

**⚠️ 安全提醒**：
- **不要**将 5432/6379 端口开放给 0.0.0.0/0（全网），这会造成严重安全风险
- 如需远程访问数据库，建议：
  1. 只开放给你的办公室IP或家庭IP
  2. 使用SSH隧道转发（更安全）：
     ```bash
     # 本地电脑执行
     ssh -L 5432:localhost:5432 root@your-ecs-ip
     # 然后通过 localhost:5432 访问远程数据库
     ```

**服务器防火墙配置（如果启用了ufw/firewalld）**：
```bash
# Ubuntu（ufw）
ufw allow 8000/tcp
# 数据库端口按需开放
ufw allow from YOUR_IP to any port 5432  # 限制来源IP
ufw reload

# CentOS（firewalld）
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="YOUR_IP" port protocol="tcp" port="5432" accept'
firewall-cmd --reload
```

**验证公网访问**：
```bash
# 在本地电脑浏览器访问
http://your-ecs-ip:8000

# 或使用curl测试
curl http://your-ecs-ip:8000/healthz

# 测试数据库连接（需要先配置安全组）
psql -h your-ecs-ip -U fin_user -d fin_daily_report
# 输入数据库密码
```

---

### 3.9 导入初始数据（Day 2晚上）

**添加信息源示例**：
```bash
# 登录管理后台
http://your-ecs-ip:8000/admin

# 添加RSS信息源
# 名称：财新网-金融
# URL：http://economy.caixin.com/rss/financial.xml
# 类型：rss
# 状态：启用

# 添加收件人
# 邮箱：your-email@example.com
# 类型：recipient（接收日报）或 whitelist（管理员）
# 状态：启用
```

**或使用脚本批量导入**：
```bash
docker-compose -f docker-compose.prod.yml exec web \
  python scripts/seed_test_data.py
```

---

## 4. Day 3 功能验证清单

### 4.1 手动触发采集任务

```bash
# 方法1：通过管理后台
# 访问 http://your-ecs-ip:8000/admin
# 点击"手动生成日报"按钮

# 方法2：通过命令行
docker-compose -f docker-compose.prod.yml exec worker \
  celery -A src.tasks.celery_app call src.tasks.orchestrator.run_full_pipeline_task
```

**验证结果**：
```bash
# 查看采集日志
docker-compose -f docker-compose.prod.yml logs worker | grep "crawl"

# 查看数据库
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U fin_user -d fin_daily_report -c \
  "SELECT COUNT(*) FROM articles WHERE created_at > NOW() - INTERVAL '1 hour';"
# 应该有新文章数据

# 查看抽取结果
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U fin_user -d fin_daily_report -c \
  "SELECT COUNT(*) FROM extraction_items WHERE created_at > NOW() - INTERVAL '1 hour';"
```

---

### 4.2 验证邮件发送

```bash
# 查看投递日志
docker-compose -f docker-compose.prod.yml logs worker | grep "mail"

# 查看数据库投递记录
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U fin_user -d fin_daily_report -c \
  "SELECT recipient, status, error_msg FROM delivery_log ORDER BY created_at DESC LIMIT 5;"
```

**排查SMTP问题**：
```bash
# 测试SMTP连接
docker-compose -f docker-compose.prod.yml exec web python -c "
from src.mailer.smtp_client import SMTPClient
import asyncio
async def test():
    client = SMTPClient()
    await client.send_email('test@example.com', 'Test Subject', '<p>Test Body</p>')
asyncio.run(test())
"
```

---

### 4.3 验证定时任务

```bash
# 查看Celery Beat状态
docker-compose -f docker-compose.prod.yml logs beat | tail -20

# 查看注册的定时任务
docker-compose -f docker-compose.prod.yml exec beat \
  celery -A src.tasks.celery_app inspect registered

# 手动触发定时任务（测试）
docker-compose -f docker-compose.prod.yml exec beat \
  celery -A src.tasks.celery_app call src.tasks.scheduled.daily_report_at_6am
```

---

## 5. P1后续优化计划（上线后1-2周）

### 5.1 数据库连接池优化（0.5天）

**问题**：当前使用NullPool，高并发下可能耗尽连接

**解决方案**：
```python
# src/db/session.py
from sqlalchemy.pool import QueuePool

if settings.ENV == "production":
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )
```

---

### 5.2 日志输出到STDOUT（1天）

**问题**：当前日志写文件，容器重启后丢失

**解决方案**：
```python
# src/utils/logger.py
if settings.ENV == "production":
    logger.remove()
    logger.add(sys.stdout, level="INFO")
```

---

### 5.3 代理配置动态化（2天）

**问题**：代理地址硬编码，无法灵活切换

**解决方案**：
1. 环境变量配置代理开关和地址
2. 数据库表存储域名规则
3. 管理后台添加代理管理页面

---

### 5.4 外部API重试机制（1天）

**问题**：LLM/SMTP调用失败未重试

**解决方案**：
```python
# 安装tenacity
poetry add tenacity

# 添加重试装饰器
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def call_llm_api(...):
    ...
```

---

## 6. P2长期优化计划（Phase 3B）

### 6.1 安全加固

- [ ] Docker Secrets管理敏感信息
- [ ] Nginx反向代理+HTTPS证书
- [ ] 强制生产环境配置验证
- [ ] 定期安全漏洞扫描

### 6.2 监控告警

- [ ] Prometheus+Grafana监控
- [ ] 告警规则配置
- [ ] 日志聚合（ELK/阿里云SLS）

### 6.3 高可用

- [ ] 数据库主从复制
- [ ] Redis哨兵模式
- [ ] Celery Worker多实例
- [ ] Nginx负载均衡

---

## 7. 运维速查手册

### 7.1 常用命令

```bash
# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看实时日志
docker-compose -f docker-compose.prod.yml logs -f [service_name]

# 重启服务
docker-compose -f docker-compose.prod.yml restart [service_name]

# 查看资源使用
docker stats

# 进入容器调试
docker-compose -f docker-compose.prod.yml exec web bash

# 查看Celery队列状态
docker-compose -f docker-compose.prod.yml exec worker \
  celery -A src.tasks.celery_app inspect active

# 清空Celery队列（慎用）
docker-compose -f docker-compose.prod.yml exec worker \
  celery -A src.tasks.celery_app purge

# 数据库备份
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U fin_user fin_daily_report | gzip > backup_$(date +%Y%m%d).sql.gz

# 数据库恢复
gunzip -c backup_20251113.sql.gz | \
  docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U fin_user -d fin_daily_report
```

---

### 7.2 故障排查

**Web服务无法访问**：
```bash
# 1. 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 2. 查看Web日志
docker-compose -f docker-compose.prod.yml logs web | tail -50

# 3. 检查健康检查
curl http://localhost:8000/healthz

# 4. 检查端口占用
netstat -tulnp | grep 8000

# 5. 检查防火墙
ufw status
```

**Worker任务不执行**：
```bash
# 1. 查看Worker日志
docker-compose -f docker-compose.prod.yml logs worker | tail -50

# 2. 检查Redis连接
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# 3. 查看队列积压
docker-compose -f docker-compose.prod.yml exec worker \
  celery -A src.tasks.celery_app inspect active

# 4. 重启Worker
docker-compose -f docker-compose.prod.yml restart worker
```

**邮件发送失败**：
```bash
# 1. 查看投递日志
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U fin_user -d fin_daily_report -c \
  "SELECT * FROM delivery_log ORDER BY created_at DESC LIMIT 10;"

# 2. 检查SMTP配置
docker-compose -f docker-compose.prod.yml exec web env | grep SMTP

# 3. 手动测试邮件
docker-compose -f docker-compose.prod.yml exec web python -c "
from src.mailer.smtp_client import SMTPClient
import asyncio
async def test():
    client = SMTPClient()
    await client.send_email('test@example.com', 'Test', '<p>Test</p>')
asyncio.run(test())
"
```

---

## 8. MVP部署验收标准

### 8.1 功能验收

- [ ] Web管理后台可访问（http://your-ecs-ip:8000/admin）
- [ ] 管理员账号可登录
- [ ] 可添加信息源和收件人
- [ ] 手动触发采集任务成功
- [ ] LLM抽取功能正常
- [ ] 报告生成成功
- [ ] 邮件发送成功（至少1个收件人收到）
- [ ] 定时任务配置正确（Celery Beat）
- [ ] 系统监控页面显示正常

### 8.2 性能验收

- [ ] Web响应时间<2秒（P95）
- [ ] 单次采集任务<5分钟（20个信息源）
- [ ] 报告生成<1分钟
- [ ] 邮件发送<30秒（50个收件人）
- [ ] 内存使用<6GB（预留2GB缓冲）

### 8.3 稳定性验收

- [ ] 持续运行24小时无崩溃
- [ ] 容器自动重启正常
- [ ] 数据库数据持久化
- [ ] 定时任务准时触发

---

## 9. 成本预估

### 9.1 服务器成本

- 阿里云ECS 4C8G：约¥200-300/月
- 公网带宽5M：约¥100/月
- **月度总计**：¥300-400

### 9.2 LLM成本

假设：
- 每日采集100篇文章
- 平均每篇5000字，token约7500
- 使用Qwen-plus（¥0.8输入/¥2.0输出 per 百万token）

**月度成本估算**：
- 输入token：100篇×7500×30天 = 22.5M tokens → ¥18
- 输出token（摘要）：100篇×500×30天 = 1.5M tokens → ¥3
- 报告生成：30次×5000 tokens = 0.15M tokens → ¥0.5
- **月度总计**：约¥20-25

### 9.3 总成本

**月度运营成本**：约¥320-425（服务器+LLM）

---

## 10. 后续优化路线图

| 阶段 | 时间 | 任务 | 预期效果 |
|------|------|------|----------|
| **MVP上线** | Day 1-3 | 完成本文档所有P0任务 | 系统可用 |
| **Week 2** | +1周 | P1优化：连接池+日志+重试 | 稳定性提升 |
| **Week 3** | +2周 | 代理动态配置+管理界面优化 | 易用性提升 |
| **Month 2** | +1月 | 监控告警+自动备份 | 可观测性提升 |
| **Month 3** | +2月 | P2安全加固+HTTPS | 安全性提升 |
| **Phase 3B** | +3月 | 高可用架构+CI/CD | 企业级部署 |

---

## 附录：环境检查脚本

创建文件：`scripts/check_env.sh`

```bash
#!/bin/bash
echo "========== 环境检查脚本 =========="

# 1. 检查Docker
echo "1. 检查Docker..."
docker --version || echo "❌ Docker未安装"

# 2. 检查Docker Compose
echo "2. 检查Docker Compose..."
docker-compose --version || echo "❌ Docker Compose未安装"

# 3. 检查端口占用
echo "3. 检查端口占用..."
netstat -tulnp | grep :8000 && echo "⚠️  8000端口已被占用"

# 4. 检查磁盘空间
echo "4. 检查磁盘空间..."
df -h | grep "/$" | awk '{if($5+0 > 80) print "⚠️  磁盘使用率超过80%: "$5}'

# 5. 检查内存
echo "5. 检查内存..."
free -h

# 6. 检查.env.prod文件
echo "6. 检查配置文件..."
if [ ! -f .env.prod ]; then
    echo "❌ .env.prod文件不存在"
else
    echo "✅ .env.prod文件存在"
    # 检查必填项
    grep -q "POSTGRES_PASSWORD=" .env.prod || echo "⚠️  缺少POSTGRES_PASSWORD"
    grep -q "PROVIDER_DEEPSEEK_API_KEY=" .env.prod || echo "⚠️  缺少PROVIDER_DEEPSEEK_API_KEY"
    grep -q "SMTP_HOST=" .env.prod || echo "⚠️  缺少SMTP_HOST"
fi

echo "========== 检查完成 =========="
```

运行检查：
```bash
chmod +x scripts/check_env.sh
./scripts/check_env.sh
```

---

**结束语**：

这份MVP部署方案专注于**快速上线**，跳过了很多企业级特性的实现细节。核心原则是：
1. **Day 1-3快速部署**，先让系统跑起来
2. **Week 2-3逐步优化**，解决性能和稳定性问题
3. **Month 2-3安全加固**，提升安全性和可观测性
4. **Phase 3B企业级改造**，高可用和自动化

建议按照这个节奏稳步推进，避免陷入过早优化的陷阱。祝部署顺利！🚀
