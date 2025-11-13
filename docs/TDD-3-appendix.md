# TDD-3 附录：快速参考与故障排查

## B. 常用命令速查表

### 开发环境

```bash
# 启动所有服务
docker-compose -f docker-compose.dev.yml up -d

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f [service_name]

# 重启服务
docker-compose -f docker-compose.dev.yml restart [service_name]

# 停止并删除容器
docker-compose -f docker-compose.dev.yml down

# 重新构建镜像
docker-compose -f docker-compose.dev.yml build --no-cache

# 进入容器
docker-compose -f docker-compose.dev.yml exec web bash
```

### 生产环境

```bash
# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看资源使用
docker stats

# 滚动更新
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --no-deps web worker beat

# 查看最近100行日志
docker-compose -f docker-compose.prod.yml logs --tail=100 -f worker
```

### 数据库操作

```bash
# 执行迁移
docker-compose exec web alembic upgrade head

# 回滚迁移
docker-compose exec web alembic downgrade -1

# 查看迁移历史
docker-compose exec web alembic history

# 进入数据库
docker-compose exec postgres psql -U fin_user -d fin_daily_report

# 备份数据库
docker-compose exec postgres pg_dump -U fin_user fin_daily_report | gzip > backup_$(date +%Y%m%d).sql.gz

# 恢复数据库
gunzip -c backup_20251110.sql.gz | docker-compose exec -T postgres psql -U fin_user -d fin_daily_report
```

### Celery 任务管理

```bash
# 查看活跃任务
docker-compose exec worker celery -A src.tasks.celery_app inspect active

# 查看已注册任务
docker-compose exec worker celery -A src.tasks.celery_app inspect registered

# 查看队列状态
docker-compose exec worker celery -A src.tasks.celery_app inspect stats

# 清除所有任务（危险操作）
docker-compose exec worker celery -A src.tasks.celery_app purge

# 动态调整并发数
docker-compose exec worker celery -A src.tasks.celery_app control pool_grow 2
docker-compose exec worker celery -A src.tasks.celery_app control pool_shrink 1
```

### Redis 操作

```bash
# 进入 Redis CLI
docker-compose exec redis redis-cli

# 查看内存使用
docker-compose exec redis redis-cli info memory

# 查看所有键
docker-compose exec redis redis-cli keys '*'

# 查看特定键值
docker-compose exec redis redis-cli get "key_name"

# 清空数据库（危险操作）
docker-compose exec redis redis-cli FLUSHDB
```

---

## C. 环境变量完整清单

### 必需变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql://fin_user:pass@postgres:5432/fin_daily_report` |
| `REDIS_URL` | Redis 连接串 | `redis://redis:6379/0` |
| `PROVIDER_DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-xxxxxxxxxxxxx` |
| `PROVIDER_QWEN_API_KEY` | Qwen API Key | `sk-xxxxxxxxxxxxx` |
| `SMTP_HOST` | SMTP 服务器地址 | `smtp.exmail.qq.com` |
| `SMTP_PORT` | SMTP 端口 | `465` |
| `SMTP_USER` | SMTP 用户名 | `report@example.com` |
| `SMTP_PASS` | SMTP 密码/授权码 | `xxxxxxxxxxxxxxxx` |

### 可选变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ENV` | 环境标识 | `development` |
| `TZ` | 时区 | `Asia/Shanghai` |
| `JWT_SECRET_KEY` | JWT 密钥 | `dev-secret-key` |
| `JWT_EXPIRE_DAYS` | JWT 过期天数 | `7` |
| `CRAWL_CONCURRENCY_RSS` | RSS 并发数 | `10` |
| `CRAWL_CONCURRENCY_WEB` | 网页并发数 | `2` |
| `LLM_TIMEOUT_SEC` | LLM 超时秒数 | `90` |
| `REPORT_TOPN` | 报告 Top N | `5` |
| `MAIL_BATCH_LIMIT` | 邮件批次限制 | `50` |
| `MAIL_RATE_LIMIT_PER_SEC` | 邮件发送速率 | `1.0` |

---

## D. 故障排查决策树

```
容器无法启动？
├─ 是 → 检查 docker-compose logs [service]
│       ├─ 数据库连接失败？
│       │   └─ 检查 DATABASE_URL 配置
│       │       └─ 确认 postgres 容器健康
│       ├─ 端口被占用？
│       │   └─ lsof -i :8000
│       │       └─ 修改端口或停止占用进程
│       └─ 环境变量缺失？
│           └─ 检查 .env 文件是否存在
│               └─ 对比 .env.example 补全
└─ 否 → 服务运行异常？
        ├─ 是 → Web 服务响应慢？
        │       ├─ 检查 docker stats
        │       │   └─ 内存/CPU 使用率 >90%？
        │       │       └─ 调整资源限制
        │       └─ 检查数据库查询
        │           └─ EXPLAIN ANALYZE 慢查询
        ├─ Worker 任务积压？
        │   ├─ 检查 Celery 队列状态
        │   │   └─ celery inspect active
        │   ├─ 增加并发数
        │   │   └─ --concurrency=4
        │   └─ 检查任务失败日志
        │       └─ LLM API 超时？
        │           └─ 增加 LLM_TIMEOUT_SEC
        └─ 邮件发送失败？
            ├─ 测试 SMTP 连接
            │   └─ telnet smtp.example.com 465
            ├─ 检查 SMTP 配置
            │   └─ SMTP_HOST/PORT/USER/PASS
            └─ 查看 delivery_log 表
                └─ 分析失败原因
```

---

## E. 性能基准与优化目标

### 当前系统基准（2C/2G 服务器）

| 指标 | 基准值 | 目标值 |
|------|--------|--------|
| Web 容器内存 | ~300MB | ≤512MB |
| Worker 容器内存 | ~600MB | ≤1GB |
| Beat 容器内存 | ~150MB | ≤256MB |
| PostgreSQL 内存 | ~200MB | ≤512MB |
| Redis 内存 | ~50MB | ≤256MB |
| 健康检查响应时间 | 200ms | <500ms |
| 采集100篇文章耗时 | ~5分钟 | <10分钟 |
| LLM 抽取单篇文章 | ~30秒 | <60秒 |
| 日报生成耗时 | ~2分钟 | <5分钟 |
| 邮件发送50人 | ~1分钟 | <2分钟 |

### 优化建议

1. **降低 Playwright 并发**：
   - 从 `CRAWL_CONCURRENCY_WEB=2` 降至 `1`
   - 预期节省内存 ~300MB

2. **启用 Redis LRU**：
   - 配置 `maxmemory 256mb` + `maxmemory-policy allkeys-lru`
   - 防止 Redis 内存无限增长

3. **限制 PostgreSQL 连接池**：
   - `pool_size=5`, `max_overflow=10`
   - 减少数据库连接开销

4. **Worker 任务限制**：
   - `--max-tasks-per-child=50`
   - 防止内存泄漏

---

## F. 安全检查清单

### 部署前检查

- [ ] `.env.prod` 文件不包含在镜像中
- [ ] 生产环境使用强密码（数据库、JWT、SMTP）
- [ ] JWT_SECRET_KEY 已修改为随机字符串（≥32字符）
- [ ] PostgreSQL 密码已修改（不使用 `fin_pass`）
- [ ] 数据库容器不暴露外部端口（生产环境）
- [ ] 应用容器使用非 root 用户运行
- [ ] Docker 日志滚动已配置（防止磁盘占满）
- [ ] 防火墙已配置（仅开放必要端口）

### 运行时安全

- [ ] 定期更新基础镜像（安全补丁）
- [ ] 定期备份数据库（至少每周一次）
- [ ] 监控容器资源使用（防止 DoS）
- [ ] 查看 delivery_log 异常发送记录
- [ ] 定期清理旧日志与数据（90 天）
- [ ] 检查 Docker 镜像漏洞（Trivy）

### 访问控制

- [ ] 管理员密码已修改（不使用默认 `xtyydsf/xtyydsf`）
- [ ] 白名单邮箱已配置（OTP 登录）
- [ ] API 接口无公开暴露（除 /healthz）
- [ ] Nginx 限流已启用（登录接口）
- [ ] HTTPS 已配置（生产环境）

---

## G. 容器化迁移路径

### 现有部署 → 容器化（零停机）

**第1步：准备阶段**（不影响现有服务）
```bash
# 1. 构建 Docker 镜像
docker build -t finrep/app:1.0.0 .

# 2. 测试容器启动
docker-compose -f docker-compose.prod.yml config

# 3. 备份现有数据
pg_dump $DATABASE_URL | gzip > backup_before_migration.sql.gz
```

**第2步：并行运行**（容器与现有服务共存）
```bash
# 1. 修改容器端口（避免冲突）
# docker-compose.prod.yml: "8001:8000"

# 2. 启动容器服务
docker-compose -f docker-compose.prod.yml up -d

# 3. 验证容器服务
curl http://localhost:8001/healthz

# 4. 小流量测试（部分用户切换到容器）
```

**第3步：流量切换**（逐步迁移）
```bash
# 1. Nginx 配置双上游
upstream finrep_backend {
    server localhost:8000 weight=9;  # 现有服务 90%
    server localhost:8001 weight=1;  # 容器服务 10%
}

# 2. 观察容器服务稳定性（24小时）

# 3. 逐步增加容器权重
# weight=5 (50%) → weight=9 (90%) → weight=10 (100%)
```

**第4步：完全切换**（停用旧服务）
```bash
# 1. 停止现有服务
./scripts/stop_all.sh

# 2. 容器服务切换到标准端口
# docker-compose.prod.yml: "8000:8000"

# 3. 重启容器
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# 4. 验证所有功能
curl http://localhost:8000/healthz
```

---

## H. 联系与支持

### 文档资源

- **PRD**：`docs/PRD.md` - 产品需求文档
- **TDD-1**：`docs/TDD-1.md` - 数据模型与核心架构
- **TDD-2**：`docs/TDD-2.md` - Web 管理台与可观测性（如有）
- **TDD-3**：本文档 - 容器化与生产部署
- **STARTUP_GUIDE**：`docs/STARTUP_GUIDE.md` - 快速启动指南
- **更新日志**：`docs/update.md` - 版本更新记录

### 常见问题

1. **Q: 容器启动后数据库迁移失败？**
   - A: 确保 PostgreSQL 容器已就绪（healthcheck），手动执行 `docker-compose exec web alembic upgrade head`

2. **Q: Worker 任务一直 Pending 不执行？**
   - A: 检查 Redis 连接、Celery Beat 是否启动、时区配置是否正确

3. **Q: 生产环境如何查看实时日志？**
   - A: `docker-compose -f docker-compose.prod.yml logs -f --tail=100 worker`

4. **Q: 如何调整 LLM 费用预算？**
   - A: 修改 `.env` 中的 `LLM_CHUNK_BUDGET`、`LLM_MAX_CHUNKS_PER_ARTICLE` 参数

5. **Q: 容器重启后任务丢失？**
   - A: 确保 Redis 持久化已启用（RDB/AOF），或使用外部 Redis 服务

### 技术支持

- **项目仓库**：查看 Issues 与 Pull Requests
- **邮件支持**：联系项目维护者
- **监控告警**：生产环境建议配置 Prometheus + Grafana

---

## I. 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v4.0 | 2025-11-10 | 完整重构 TDD-3，基于实际系统架构编写容器化方案 |
| v3.0 | 2025-11-05 | 初始版本（规划阶段，未完全实现） |

---

**文档结束**

有关最新更新，请参阅 `docs/update.md` 与项目提交历史。
