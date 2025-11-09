# 金融情报日报系统 · 技术设计文档

（TDD · 第三阶段｜容器化与部署）

**版本**：v3.0  
**日期**：2025-11-05（Asia/Shanghai）  
**目标**：将阶段一/二产物以 **docker-compose** 封装，支持 WSL 开发环境与腾讯云 2C/2G 生产环境一键部署、观测与日常运维。

---

## 1. 架构与容器拓扑

### 1.1 服务组件（容器）

- `web`：FastAPI（HTTP 8000，提供 `/healthz`、下载与管理台）
  
- `worker`：Celery Worker（处理采集/抽取/成稿/发送等任务）
  
- `beat`：Celery Beat（06:00 定时调度流水线）
  
- `redis`：任务队列（Broker/Backend）
  
- `postgres`：数据库（阶段三可用容器或外部托管，**推荐外部托管**）
  
- （可选）`mailhog`：本地联调 SMTP（生产禁用）
  
- （可选）`backup`：pg_dump 定时备份侧车
  
- （可选）`reverse-proxy`：Caddy/Nginx 反向代理与 TLS（生产按需）
  

### 1.2 网络与卷

- Docker 网络：`finrep-net`（bridge）
  
- 卷：
  
    - `pgdata`（Postgres 数据）
      
    - `reports_data`（可选：导出附件/日志归档）
      
    - `backup`（可选：pg_dump 输出）
      

---

## 2. 镜像与构建

### 2.1 语言运行时

- 基础镜像：`python:3.11-slim`（或 3.12-slim）
  
- 多阶段构建：`builder`（安装依赖）→ `runtime`（仅复制产物）
  
- 依赖缓存：`pip wheel` + `--mount=type=cache`（可选）
  

### 2.2 镜像规范

- 镜像标签：`{registry}/{namespace}/finrep-{web|worker|beat}:{git_sha|semver}`
  
- 运行用户：非 root（UID/GID 1000）
  
- 入口：
  
    - `web`：`uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --workers 2`
      
    - `worker`：`celery -A src.tasks worker -l INFO --concurrency=2`（生产 2C/2G）
      
    - `beat`：`celery -A src.tasks beat -l INFO`
      

---

## 3. 配置与机密

### 3.1 环境变量

沿用阶段一/二 `.env`，新增：

`ENV=dev|prod LOG_LEVEL=INFO JWT_SECRET=...                      # 第二阶段已用 MAIL_WINDOW_START=06:05 MAIL_WINDOW_END=06:20`

### 3.2 机密注入

- 本地：`.env` 文件（**勿入库**）
  
- 生产：`docker compose --env-file` 或 Docker Secrets（推荐）
  
- 机密项：`SMTP_PASS`、各 Provider 的 `API_KEY`、`JWT_SECRET`
  

---

## 4. 健康检查与可观测性

### 4.1 Healthcheck

- `web`：`CMD curl -fsS http://localhost:8000/healthz || exit 1`（间隔 30s，重试 3）
  
- `worker/beat`：脚本 `celery inspect ping` 或 Redis 心跳键检测（`HEALTH_OK`）
  

### 4.2 日志

- 标准输出 JSON 行（含 `trace_id`, `service`, `task`, `latency_ms`）
  
- 滚动：由 Docker 日志驱动控制（生产建议 `max-size=50m, max-file=3`）
  

### 4.3 指标面板（轻量）

- 管理台“系统状态”页汇总：队列水位、近 24h 任务/失败率、Provider 超时率、平均处理时延
  
- `/metrics`（可选，Prometheus 文本格式；生产按需开放）
  

---

## 5. docker-compose 设计

### 5.1 文件与 Profiles

- `deploy/compose.yml`：生产/开发共用
  
- Profiles：`dev`（含 mailhog、内置 postgres）、`prod`（外部 postgres、禁用 mailhog）
  

### 5.2 核心字段（规范）

- `restart: unless-stopped`（生产）
  
- 资源限制（生产 2C/2G 指标）：
  
    - `web`：`cpus: 0.5-1.0`, `memory: 512m`
      
    - `worker`：`cpus: 0.5-1.0`, `memory: 1g`
      
    - `beat`：`cpus: 0.2`, `memory: 256m`
      
    - `redis`：`memory: 256m`
    
- 依赖顺序：`depends_on` + healthcheck 条件
  

---

## 6. 部署流程

### 6.1 WSL（开发）

1. `docker compose -f deploy/compose.yml --profile dev up -d`
   
2. 导入种子数据（sources、recipients）
   
3. 访问：`http://localhost:8000`（第二阶段前端）
   
4. 冒烟：`python -m src.cli.run_once --step all`（容器内或宿主 venv）
   

### 6.2 腾讯云 2C/2G（生产）

1. 安装 Docker/Compose（v2）
   
2. 准备 `.env.prod`（不含明文密码的可共享版，机密用 Secrets）
   
3. 若使用外部 Postgres：创建数据库与网络白名单
   
4. `docker compose -f deploy/compose.yml --profile prod --env-file .env.prod up -d`
   
5. 首次迁移：`docker compose exec web alembic upgrade head`
   
6. 验证 `/healthz`、管理台状态、06:00 自动任务与 06:05–06:20 窗口发信
   

---

## 7. 备份与恢复（可选强烈建议）

### 7.1 备份侧车 `backup`

- 基于 `postgres:16-alpine` + `pg_dump`
  
- Cron：每日 06:30（日报发完后）
  
- 输出：`/backup/finrep_YYYYMMDD.sql.gz`（保留 7–30 天）
  
- 存储：挂载到持久盘或对象存储（COS）
  

### 7.2 恢复

- `gunzip -c finrep_YYYYMMDD.sql.gz | psql $DATABASE_URL`
  

---

## 8. 运维 Runbook

### 8.1 常见问题

- **web 起不来**：查 `/healthz` 错误；多为 `.env` 缺项、DB 连通性或迁移未执行
  
- **worker 积压**：降低并发量、检查 Provider 超时/429；必要时暂停抽取仅保留摘要
  
- **SMTP 被限速**：调小批次与节流，扩大投递窗口；必要时拆分多账号
  
- **磁盘紧张**：清理旧附件或关闭 `reports_data` 卷；开启 pg_dump 过期清理
  

### 8.2 日常操作

- 滚动升级（零停机）：
  
    `docker compose pull docker compose up -d web worker beat`
    
- 查看队列：
  
    `docker compose exec worker celery -A src.tasks inspect active docker compose exec worker celery -A src.tasks inspect reserved`
    

---

## 9. 验收标准（第三阶段 Done）

1. **一键部署**：`docker compose up -d` 后，全部容器健康；管理台可访问
   
2. **定时链路**：06:00 自动触发 → **06:20 前**邮件送达；delivery_log 记录完整
   
3. **观测**：管理台能看到队列/失败率/Provider 状态；`/healthz` 绿灯
   
4. **资源**：2C/2G 下稳定运行 ≥3 天，无 OOM/Kill
   
5. **备份**：每日生成一份 `pg_dump`（若启用）；可人工恢复成功
   
6. **升级**：镜像更新后滚动重启不影响次日任务（无数据损坏）
   

---

## 10. 安全与合规附注

- 生产机密用 Secrets；`.env` 不落盘或严格访问控制
  
- 管理员默认口令在生产强烈建议更改（虽 PRD 允许固定），并限制来源 IP
  
- 仅采集公开页面；`robots` 开关慎用（默认关，业务内网为宜）
  
- SMTP 授权码定期轮换；失败/退信自动黑名单已在阶段一实现
  

---

## 11. CI/CD（可选规范）

- **CI**：lint+test → 构建镜像 → 扫描漏洞（Trivy）
  
- **CD**：推送镜像到私有仓库 → 远端 `docker compose pull && up -d`
  
- 版本：`vMAJOR.MINOR.PATCH+gitsha`；`build_meta` 写入 `reports`
  

---

### 附：compose 关键字段清单（规范级摘要）

> 交付到 Claude Code 生成 YAML 即可

- `services.web`：`image`/`build`、`ports: ["8000:8000"]`、`env_file`、`healthcheck`、`depends_on: [redis, postgres]`
  
- `services.worker`：同 `web` 的 env，`depends_on: [redis, postgres]`
  
- `services.beat`：同上
  
- `services.redis`：`image: redis:7-alpine`、`command: ["--save", "", "--appendonly", "no"]`
  
- `services.postgres`（dev profile）：`image: postgres:16-alpine`、`volumes: [pgdata:/var/lib/postgresql/data]`
  
- `volumes`: `pgdata`, `reports_data`, `backup`（可选）