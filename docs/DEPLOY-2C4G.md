# 2核4G ECS 部署指南

**适用场景**：阿里云/腾讯云 2核4G 低配服务器快速部署

**目标**：在有限资源下稳定运行系统，支持基本的采集和日报功能

---

## 1. 资源对比分析

### 1.1 配置对比

| 资源项 | 4核8G（标准） | 2核4G（精简） | 优化说明 |
|--------|---------------|---------------|----------|
| **CPU核心** | 4核 | 2核 | 降低并发数、减少worker数 |
| **内存总量** | 8GB | 4GB | 每个服务内存限制减半 |
| **PostgreSQL** | 1GB | 512MB | 足够小型应用 |
| **Redis** | 512MB | 256MB | 缓存数据较少 |
| **Web** | 2GB (2 workers) | 1GB (1 worker) | 单进程处理请求 |
| **Worker** | 3GB (concurrency=2) | 1.5GB (concurrency=1) | 单任务串行处理 |
| **Beat** | 256MB | 256MB | 保持不变 |
| **内存总需求** | ~6.8GB | ~3.5GB | 为系统保留500MB |

---

### 1.2 性能预期

| 指标 | 4核8G | 2核4G | 影响 |
|------|-------|-------|------|
| **Web响应** | <1秒 | 1-2秒 | 可接受 |
| **采集速度** | 20源/5分钟 | 20源/10-15分钟 | ⚠️ 慢一倍 |
| **并发用户** | 10-20人 | 3-5人 | ⚠️ 受限 |
| **Playwright** | 3个浏览器 | 1个浏览器 | ⚠️ 慢3倍 |
| **报告生成** | 5分钟 | 8-10分钟 | 可接受 |
| **邮件发送** | 50封/15分钟 | 50封/30分钟 | 可接受 |

**结论**：
- ✅ 功能完整性：100%保留
- ⚠️ 性能下降：约50-70%
- ✅ 稳定性：通过优化可保证
- 💰 成本节省：约50%（¥150-200/月）

---

## 2. 关键优化点

### 2.1 内存优化

**PostgreSQL**：
```yaml
deploy:
  resources:
    limits:
      memory: 512M  # 从1G降至512M
```
- 小型应用512MB足够
- 连接池限制为5-10个连接

**Redis**：
```yaml
command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru --save ""
```
- 256MB缓存空间
- 禁用RDB持久化（`--save ""`）节省内存
- LRU淘汰策略

**Web**：
```yaml
command: uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --workers 1
deploy:
  resources:
    limits:
      memory: 1G  # 从2G降至1G
```
- 单worker进程
- 适合小并发（<5人）

**Worker**：
```yaml
command: celery -A src.tasks.celery_app worker --concurrency=1 --max-tasks-per-child=20
deploy:
  resources:
    limits:
      memory: 1.5G  # 从3G降至1.5G
shm_size: '256mb'  # 从512mb降至256mb
```
- **concurrency=1**：单任务串行处理（关键优化）
- **max-tasks-per-child=20**：更频繁重启worker释放内存
- **shm_size=256mb**：Playwright最低要求

---

### 2.2 并发优化

**.env.2c4g.example**：
```bash
# Playwright
PLAYWRIGHT_MAX_BROWSERS=1  # 从3降至1
PLAYWRIGHT_TIMEOUT_MS=45000  # 从30s增至45s

# 采集并发
CRAWL_CONCURRENCY_RSS=3  # 从5降至3
CRAWL_CONCURRENCY_DYNAMIC=1  # 保持1

# LLM
LLM_MAX_CHUNKS_PER_ARTICLE=6  # 从8降至6
LLM_TIMEOUT_SEC=120  # 从90s增至120s

# 邮件
MAIL_RATE_LIMIT_PER_SEC=0.5  # 从1.0降至0.5
MAIL_WINDOW_END=06:30  # 从06:20延长至06:30
```

**核心思想**：用时间换空间
- 降低并发数 → 减少内存占用
- 增加超时时间 → 避免任务失败
- 延长处理窗口 → 确保任务完成

---

## 3. 部署步骤（与4核8G略有不同）

### 3.1 构建镜像（Day 1上午）

```bash
# 使用相同的Dockerfile
docker build -t finrep/app:2c4g .
```

### 3.2 配置环境变量（Day 1下午）

```bash
# 复制2核4G专用配置
cp .env.2c4g.example .env.prod

# 编辑配置文件
vim .env.prod
# 修改：
# - 数据库密码
# - LLM API Key
# - SMTP配置
# - JWT密钥
```

### 3.3 启动服务（Day 2上午）

```bash
# 使用2核4G专用compose文件
docker-compose -f docker-compose.2c4g.yml up -d

# 查看容器状态
docker-compose -f docker-compose.2c4g.yml ps

# 查看资源使用
docker stats
```

### 3.4 验证内存占用（Day 2上午）

```bash
# 等待所有容器启动完成（约2-3分钟）
sleep 180

# 查看实际内存使用
docker stats --no-stream

# 预期输出示例：
# NAME                    CPU %   MEM USAGE / LIMIT   MEM %
# finrep_postgres_prod    2%      180MB / 512MB       35%
# finrep_redis_prod       1%      50MB / 256MB        20%
# finrep_web_prod         5%      350MB / 1GB         35%
# finrep_worker_prod      15%     800MB / 1.5GB       53%
# finrep_beat_prod        1%      80MB / 256MB        31%
#
# 总内存使用：约1.5GB（空闲时）
# 任务执行时：约2.5-3GB（Playwright启动时）
```

---

## 4. 性能验证与调优

### 4.1 压力测试

**测试场景1：采集任务**
```bash
# 手动触发采集任务
docker-compose -f docker-compose.2c4g.yml exec worker \
  celery -A src.tasks.celery_app call src.tasks.orchestrator.run_full_pipeline_task

# 观察内存变化
watch -n 5 'docker stats --no-stream'

# 预期结果：
# - RSS采集：内存增加100-200MB
# - 动态采集（Playwright）：内存峰值2.8-3.2GB
# - 如果超过3.5GB，说明内存不足，需要进一步优化
```

**测试场景2：并发Web请求**
```bash
# 使用ab工具测试
ab -n 100 -c 3 http://localhost:8000/

# 预期结果：
# - 并发3个请求：正常响应
# - 并发5个请求：可能出现慢响应
# - 并发10个请求：不推荐（内存不足）
```

---

### 4.2 如果内存不足（OOM）

**症状**：
- 容器频繁重启
- 系统日志出现 `Out of memory` 错误
- `docker stats` 显示内存使用接近100%

**解决方案**：

#### 方案1：禁用动态采集（Playwright）
```bash
# .env.prod
PLAYWRIGHT_MAX_BROWSERS=0  # 禁用Playwright

# 只添加RSS和静态网页信息源
# 删除所有 type=dynamic 的信息源
```
**效果**：节省约800MB内存

---

#### 方案2：减少信息源数量
```bash
# 管理后台：/admin/sources
# 只保留5-10个重要信息源
# 禁用不活跃的信息源
```
**效果**：减少采集压力，间接降低内存

---

#### 方案3：调整定时任务频率
```python
# src/tasks/scheduled.py
# 将每日1次改为每2天1次

@app.task(name="scheduled.daily_report_every_two_days")
def daily_report_every_two_days():
    """每两天早上6点生成日报"""
    run_full_pipeline_task.delay()

# 修改Celery Beat配置
app.conf.beat_schedule = {
    'daily-report-every-two-days': {
        'task': 'scheduled.daily_report_every_two_days',
        'schedule': crontab(hour=6, minute=0, day_of_week='1,3,5'),  # 周一/三/五
    },
}
```
**效果**：降低整体负载

---

#### 方案4：启用SWAP（不推荐，但应急可用）
```bash
# 创建2GB SWAP
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# 永久生效
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 调整swappiness（降低swap使用频率）
sysctl vm.swappiness=10
echo 'vm.swappiness=10' >> /etc/sysctl.conf
```
**效果**：提供2GB虚拟内存缓冲
**副作用**：性能下降明显（磁盘比内存慢100倍）

---

## 5. 2核2G能否运行？

### 5.1 理论分析

**内存需求**：
- 系统 + Docker：约500MB
- 容器最低配置：约2.5GB
- **总需求**：3GB
- **可用内存**：2GB

**结论**：❌ **2核2G无法运行完整系统**

---

### 5.2 极限方案（不推荐）

如果必须在2核2G上运行，需要：

#### 方案：单容器模式（合并服务）

**思路**：
- 移除Worker/Beat容器
- 在Web容器内运行Celery（非容器化）
- 禁用Playwright动态采集
- 只保留RSS采集

**配置**：
```yaml
services:
  postgres:
    # 同上，256MB
  redis:
    # 同上，128MB

  web:
    command: >
      bash -c "
      celery -A src.tasks.celery_app beat --detach &&
      celery -A src.tasks.celery_app worker --detach --concurrency=1 &&
      uvicorn src.web.app:app --host 0.0.0.0 --port 8000
      "
    deploy:
      resources:
        limits:
          memory: 1.5G  # 合并所有Python进程
```

**内存分配**：
- Postgres: 256MB
- Redis: 128MB
- Web+Worker+Beat: 1.5GB
- **总计**: 1.88GB

**限制**：
- ❌ 无法使用Playwright
- ❌ 无法并发处理任务
- ❌ 性能极差（采集需30分钟+）
- ❌ 不稳定（内存不足风险高）

**建议**：不如直接购买2核4G服务器（多¥30/月），避免运维噩梦

---

## 6. 推荐配置与成本

| 配置 | 月成本 | 适用场景 | 推荐度 |
|------|--------|----------|--------|
| **2核4G** | ¥150-200 | <10人使用，每日1次报告 | ⭐⭐⭐⭐ 推荐 |
| **4核8G** | ¥300-400 | <50人使用，功能齐全 | ⭐⭐⭐⭐⭐ 最佳 |
| 2核2G | ¥100-150 | ❌ 不推荐 | ⭐ 极限方案 |

---

## 7. 快速部署清单（2核4G）

```bash
# Day 1 - 本地准备
cd /path/to/V4
docker build -t finrep/app:2c4g .
cp .env.2c4g.example .env.prod
# 编辑 .env.prod
docker-compose -f docker-compose.2c4g.yml up -d
docker-compose -f docker-compose.2c4g.yml exec web alembic upgrade head

# Day 2 - ECS部署
ssh root@your-ecs-ip
# 安装Docker（参考TDD-3-MVP-DEPLOY.md）
git clone <repo-url>
cd V4
cp .env.2c4g.example .env.prod
# 编辑 .env.prod
docker build -t finrep/app:2c4g .
docker-compose -f docker-compose.2c4g.yml up -d
docker-compose -f docker-compose.2c4g.yml exec web alembic upgrade head

# Day 3 - 验证
docker stats --no-stream
docker-compose -f docker-compose.2c4g.yml logs -f worker
# 手动触发采集任务
# 查看报告生成
```

---

## 8. 常见问题

### Q1: Worker内存占用超过1.5GB怎么办？
**A**:
1. 检查是否同时运行多个Playwright任务
2. 确认 `PLAYWRIGHT_MAX_BROWSERS=1`
3. 降低 `CRAWL_CONCURRENCY_RSS` 至 2
4. 考虑禁用动态采集

### Q2: 采集任务超时失败？
**A**:
1. 增加 `PLAYWRIGHT_TIMEOUT_MS` 至 60000
2. 增加 `LLM_TIMEOUT_SEC` 至 150
3. 减少信息源数量至10个以内

### Q3: Web界面响应慢？
**A**:
1. 正常现象（单worker处理请求）
2. 避免高峰期访问
3. 考虑升级到4核8G

---

## 9. 总结

### 2核4G：✅ 可以运行（推荐）

**优点**：
- ✅ 成本低（约¥150/月）
- ✅ 功能完整
- ✅ 稳定性可接受

**缺点**：
- ⚠️ 性能下降50%
- ⚠️ 并发受限
- ⚠️ 需要精细调优

**适合**：
- 个人使用或小团队（<10人）
- 预算有限
- 对性能要求不高

---

### 2核2G：❌ 不推荐

**问题**：
- ❌ 内存不足，OOM风险高
- ❌ 需要极限优化（禁用Playwright等）
- ❌ 运维成本高

**建议**：
- 加¥30/月升级到2核4G
- 或使用轻量级方案（serverless）

---

**最终建议**：
- **首选**：2核4G（性价比最高）
- **理想**：4核8G（功能齐全）
- **避免**：2核2G（不值得折腾）
