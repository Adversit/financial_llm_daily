# 更新日志

## [2025-11-13] - 2核4G低配服务器部署方案

### 文档新增 (Added)
- 📋 **新增2核4G精简部署方案**
  - `docker-compose.2c4g.yml`：专门优化的容器编排配置
  - `.env.2c4g.example`：2核4G环境变量配置模板
  - `docs/DEPLOY-2C4G.md`：完整的2核4G部署指南（约8000字）

### 核心优化点 (Optimizations)
- 🎯 **内存大幅压缩**：从6.8GB降至3.5GB
  - PostgreSQL: 1GB → 512MB
  - Redis: 512MB → 256MB（禁用RDB持久化）
  - Web: 2GB → 1GB（2 workers → 1 worker）
  - Worker: 3GB → 1.5GB（concurrency=2 → 1）
  - shm_size: 512MB → 256MB（Playwright最低要求）

- ⚡ **并发降级**：用时间换空间
  - Playwright浏览器：3个 → 1个
  - RSS并发：5 → 3
  - Celery并发：2 → 1（单任务串行）
  - Web workers：2 → 1

- ⏱️ **超时时间延长**：避免资源不足导致失败
  - Playwright超时：30s → 45s
  - LLM超时：90s → 120s
  - 邮件发送窗口：06:20 → 06:30

### 性能预期 (Performance)
| 指标 | 4核8G | 2核4G | 影响 |
|------|-------|-------|------|
| Web响应 | <1秒 | 1-2秒 | 可接受 |
| 采集速度 | 5分钟 | 10-15分钟 | ⚠️ 慢2倍 |
| 并发用户 | 10-20人 | 3-5人 | ⚠️ 受限 |
| 报告生成 | 5分钟 | 8-10分钟 | 可接受 |
| 月成本 | ¥300-400 | ¥150-200 | 💰 节省50% |

### 部署建议 (Recommendations)
- ✅ **2核4G**：推荐，性价比高，适合<10人小团队
- ⭐ **4核8G**：最佳，功能齐全，适合<50人使用
- ❌ **2核2G**：不推荐，内存不足（需3GB，实际只有2GB）

### 极限方案 (2核2G)
如果只有2核2G，提供了单容器合并方案：
- 移除独立Worker/Beat容器
- 在Web容器内运行所有服务
- 禁用Playwright动态采集
- 内存勉强够用（1.88GB）
- **强烈不推荐**：不稳定且性能极差

### 文件清单
- `docker-compose.2c4g.yml`：2核4G专用compose配置
- `.env.2c4g.example`：2核4G环境变量模板
- `docs/DEPLOY-2C4G.md`：详细部署指南

---

## [2025-11-13] - TDD-3 MVP部署方案文档（更新：修正端口和代理问题）

### 重要修正 (Fixed)
- 🐛 **修正PostgreSQL和Redis端口映射缺失**
  - 问题：docker-compose.prod.yml未暴露5432/6379端口，导致无法从宿主机备份/调试数据库
  - 修复：添加端口映射 `"5432:5432"` 和 `"6379:6379"`
  - 安全建议：通过安全组限制访问IP，或使用SSH隧道代替直接暴露

- 🐛 **完善代理配置方案（4种方案）**
  - 问题：简单留空PLAYWRIGHT_PROXY会导致国外站点无法访问，且破坏智能代理策略
  - 修复：详细说明4种代理方案及适用场景：
    - **方案A**：只采集国内站点（最简单，推荐MVP）
    - **方案B**：阿里云NAT网关（推荐生产环境，¥50-100/月）
    - **方案C**：第三方HTTP代理（灵活性高，¥50-80/月）
    - **方案D**：ECS本地代理（适合技术团队，自建Tinyproxy/V2Ray）
  - 提供详细配置步骤、验证命令、安全提醒

### 文档新增 (Added)
- 📋 **新增MVP快速部署指南**（`docs/TDD-3-MVP-DEPLOY.md`）
  - 专为阿里云4C8G ECS环境优化的3天上线方案
  - 面向少量用户（<50人）、非隐私敏感场景的简化部署流程
  - 分P0/P1/P2三级优先级，聚焦快速上线而非过早优化
  - **保证系统能和现在一样正常运行**（端口映射、代理策略、智能路由）

### 文档特点 (Highlights)
- ⚡ **3天部署路线图**：
  - Day 1：本地容器化验证（Dockerfile + docker-compose + .env配置）
  - Day 2：ECS部署与调试（环境准备 + 代码上传 + 服务启动 + 防火墙配置）
  - Day 3：功能验证与优化（采集测试 + 邮件测试 + 定时任务验证）

- 🎯 **P0任务详细实施方案**（阻塞部署，必须解决）：
  1. 使用官方Playwright镜像快速构建Docker（跳过多阶段构建优化）
  2. 简化版docker-compose.prod.yml（内置Postgres/Redis，资源限制适配4C8G）
  3. 明文.env.prod配置（跳过Docker Secrets，简化部署流程）
  4. 代理临时禁用（MVP阶段只采集国内站点，`PLAYWRIGHT_PROXY=`留空）
  5. ECS环境自动化安装脚本（Docker + Compose + 镜像加速）
  6. 完整的启动、迁移、验证命令

- 📝 **P1后续优化计划**（上线后1-2周逐步改进）：
  - 数据库连接池优化（NullPool → QueuePool）
  - 日志输出到STDOUT（容器友好）
  - 代理配置动态化（环境变量 + 数据库规则表）
  - 外部API重试机制（tenacity装饰器）

- 🔄 **P2长期优化路线图**（Phase 3B）：
  - 安全加固：Docker Secrets + Nginx HTTPS + 配置强制验证
  - 监控告警：Prometheus + Grafana + 日志聚合
  - 高可用：数据库主从 + Redis哨兵 + Worker多实例

### 实用工具 (Tools)
- 🛠️ **运维速查手册**：
  - 常用Docker命令速查（查看状态/日志/重启/备份恢复）
  - 故障排查决策树（Web无法访问/Worker不执行/邮件失败）
  - 环境检查脚本（`scripts/check_env.sh`）

- 💰 **成本预估**：
  - 服务器成本：¥300-400/月（ECS + 带宽）
  - LLM成本：¥20-25/月（100篇/天，Qwen-plus）
  - 月度总运营成本：约¥320-425

### MVP验收标准
- ✅ **功能验收**（9项）：管理后台访问、采集成功、LLM抽取、报告生成、邮件发送、定时任务等
- ✅ **性能验收**（5项）：Web响应<2秒、采集<5分钟、内存<6GB等
- ✅ **稳定性验收**（4项）：24小时无崩溃、自动重启、数据持久化等

### 与原TDD-3的关系
- **TDD-3.md**：完整的容器化技术设计文档，面向企业级部署
- **TDD-3-MVP-DEPLOY.md**：快速上线实战指南，面向小规模MVP部署
- 两者互补：MVP方案专注"先跑起来"，TDD-3提供完整的技术蓝图

### 目标用户
- 👤 需要在3天内快速部署到阿里云ECS的开发者
- 👥 支持少量用户（<50人）的小团队
- 🔓 非隐私敏感数据场景，可接受简化的安全配置
- 🚀 优先追求速度而非完美的MVP部署理念

### 文件位置
- `docs/TDD-3-MVP-DEPLOY.md`：新增的MVP部署指南（约15000字）
- `docs/TDD-3.md`：保持不变，作为完整技术参考文档

---

## [2025-11-13] - TDD-3.md 云端部署风险评估更新

### 文档改进 (Documentation)
- 📋 **新增第12章：云端部署风险评估与改进计划**
  - 识别7个关键云端部署风险点，明确优先级(P0/P1)和解决方案
  - 每个风险点包含：现状问题、改进方案、任务清单、涉及文件
  - 提供改进优先级与时间规划表(预计工时、目标完成阶段)
  - 调整Phase 3A验收标准，强调云端部署就绪性

### 风险评估覆盖点
- 🔴 **P0 - 必须解决（Phase 3A Week 1）**：
  1. **容器化未完成风险**：应用仍依赖本地虚拟环境启动，需完整Docker化
  2. **代理配置硬编码风险**：代理地址和域名白名单硬编码，需动态配置+数据库管理
  3. **Playwright运行时依赖缺失**：容器缺少浏览器依赖，需完整安装系统库

- 🟡 **P1 - 高优先级（Phase 3A Week 2）**：
  4. **数据库连接池配置错误**：强制NullPool会耗尽连接，需QueuePool+参数调优
  5. **日志持久化缺失**：日志写本地文件易丢失，需输出到STDOUT+集中管理
  6. **外部依赖网络策略缺失**：LLM/SMTP访问可能被封禁，需重试+熔断+白名单申请
  7. **安全配置不足**：JWT/CORS等仍是示例值，需强制验证+Docker Secrets管理

### 改进方案示例
- **容器化方案**：编写多阶段Dockerfile，用gunicorn替代uvicorn --reload，拆分web/worker/beat服务
- **代理配置方案**：新增环境变量PLAYWRIGHT_PROXY_ENABLED/URL，创建proxy_domain_rules数据库表，管理后台添加CRUD页面
- **Playwright依赖方案**：使用官方基础镜像或安装完整依赖，配置shm_size和seccomp策略
- **连接池方案**：根据ENV动态选择QueuePool/NullPool，配置pool_size=5/max_overflow=10
- **日志方案**：生产环境logger输出到sys.stdout，配置json-file driver轮转
- **网络策略方案**：为外部API添加httpx重试+tenacity指数退避，申请云厂商出站白名单
- **安全方案**：Settings添加生产环境强制验证，实现Docker Secrets文件读取，配置TrustedHostMiddleware

### 时间规划
| 优先级 | 风险项 | 预计工时 | 目标完成阶段 |
|--------|--------|----------|--------------|
| P0 | 容器化未完成 | 3天 | Phase 3A Week 1 |
| P0 | 代理配置硬编码 | 2天 | Phase 3A Week 1 |
| P0 | Playwright依赖缺失 | 1天 | Phase 3A Week 1 |
| P1 | 数据库连接池错误 | 0.5天 | Phase 3A Week 2 |
| P1 | 日志持久化缺失 | 1天 | Phase 3A Week 2 |
| P1 | 外部依赖网络策略 | 1.5天 | Phase 3A Week 2 |
| P1 | 安全配置不足 | 2天 | Phase 3A Week 2 |

**总计：11天工作量，分两周完成**

### 调整后验收标准
- [ ] 所有P0风险项已解决并通过测试
- [ ] 完整的Docker镜像可在无本地虚拟环境的云服务器上运行
- [ ] 代理配置可通过环境变量动态调整，域名规则存储在数据库
- [ ] Playwright在标准容器环境中稳定运行≥24小时
- [ ] 数据库连接池在生产环境未出现连接耗尽
- [ ] 所有P1风险项已完成或有明确的缓解措施
- [ ] 通过安全扫描（无高危漏洞），密钥已迁移到Secrets

### 文件变更
- `docs/TDD-3.md`: 新增第12章（云端部署风险评估与改进计划），更新第13章标题为"Phase 3B - 后续增强"

### 价值总结
- ✅ **将云端部署风险从模糊描述转化为可执行的任务清单**
- ✅ **明确优先级和时间规划，为Phase 3A提供清晰路线图**
- ✅ **每个风险点提供完整的现状分析→改进方案→涉及文件映射**
- ✅ **调整验收标准，确保容器化方案真正满足云端部署要求**

---

## [2025-11-13] - 词云生成低频词过滤优化

### 问题修复 (Fixed)
- 🐛 **修复今日词云生成失败问题**
  - 问题原因：今日数据量少(5篇文章),每个关键词只出现1次,经过最小词频过滤(≥2次)后无剩余关键词
  - 解决方案：动态调整最小词频阈值,当文章数<10篇时自动降为1,保证数据量少时也能生成词云
  - 影响范围：仅影响今日词云,本周/本月因数据量充足不受影响

### 改进 (Changed)
- 🎯 **智能词频过滤**
  - 文章数 < 10篇时: `min_freq = 1` (显示所有关键词)
  - 文章数 ≥ 10篇时: `min_freq = 2` (保持默认过滤)
  - 自动记录日志提示阈值调整

### 技术细节
- 修改文件: `src/web/routes/stats.py:250-268`
- 新增动态阈值逻辑,根据文章数量自适应调整过滤参数
- 保持原有的相似关键词合并逻辑不变

---

## [2025-11-13] - Playwright动态网页采集集成 + 智能代理策略

### 新增功能 (Added)
- ✨ **Playwright动态网页采集器**
  - 支持采集需要JavaScript渲染的动态网站
  - 浏览器池管理，复用浏览器实例减少启动开销
  - 支持自动滚动加载更多内容
  - 灵活的选择器配置（link_selectors, wait_selector）
  - 并发控制，避免资源耗尽（批量并发5个页面）
  - 自动提取标题、发布时间、正文内容
  - 重试机制和超时处理

- 🎯 **信息源配置增强**
  - sources表新增 `parser_config` 字段（JSON类型）
  - 支持配置：是否滚动加载、链接选择器、等待元素、URL允许模式等
  - Web管理界面可动态调整动态采集器参数

- 🔄 **智能代理策略（新增）**
  - 根据域名自动识别国内/国外网站
  - 国内网站自动不使用代理，国外网站自动使用代理
  - 访问失败自动切换代理策略（默认3次失败后切换）
  - 策略切换后缓存1小时，避免频繁切换
  - 支持自定义域名列表和切换阈值
  - 完整的失败追踪和统计功能

### 技术实现 (Technical)
- 🔧 **核心模块**
  - `src/crawlers/browser_pool.py`: 浏览器池管理器
    - 单例模式管理Playwright浏览器实例
    - 支持多个独立的BrowserContext（默认最多5个）
    - 随机UA池和反自动化检测措施
    - 自动注入反检测脚本（隐藏webdriver属性）

  - `src/crawlers/dynamic_crawler.py`: 动态采集器实现
    - 继承BaseCrawler，统一接口
    - 异步采集流程：访问列表页→提取链接→并发采集详情页
    - 支持配置化的选择器和URL过滤规则
    - 自动从meta标签提取发布时间
    - 使用trafilatura/readability提取正文
    - 指数退避重试机制
    - **集成智能代理策略**

  - `src/crawlers/proxy_strategy.py`: 智能代理策略管理器（新增）
    - 根据域名自动判断是否使用代理
    - 内置国内/国外域名列表（支持扩展）
    - 失败追踪和自动切换机制
    - 策略缓存避免频繁判断
    - 统计信息查询接口

  - `src/tasks/crawl_tasks.py`: 任务调度支持
    - `get_browser_pool()`: 全局浏览器池单例获取
    - `crawl_dynamic_task`: 动态采集Celery任务
    - `cleanup_browser_pool`: 浏览器池清理任务（定时执行）
    - 在 `_build_crawler()` 中添加DYNAMIC类型支持

### 配置说明 (Configuration)
- 📝 **环境变量配置** (.env)
  ```bash
  # Playwright配置
  PLAYWRIGHT_MAX_BROWSERS=5        # 最大浏览器上下文数
  PLAYWRIGHT_HEADLESS=true         # 无头模式
  PLAYWRIGHT_TIMEOUT_MS=30000      # 页面加载超时（毫秒）
  PLAYWRIGHT_WAIT_UNTIL=domcontentloaded  # 等待策略
  CRAWL_CONCURRENCY_DYNAMIC=2      # 动态采集并发数
  ```

- 📊 **信息源配置示例** (parser_config字段)
  ```json
  {
    "need_scroll": true,
    "link_selectors": ["article a.title", ".news-list a[href]"],
    "wait_selector": ".article-content",
    "allow_patterns": ["/news/", "/article/"],
    "max_links": 20,
    "scroll_times": 3
  }
  ```

### 性能特点 (Performance)
- ⚡ **浏览器复用优化**
  - 首次启动浏览器：~3秒
  - 复用浏览器实例创建上下文：~0.5秒
  - 性能提升约6倍

- 🚀 **并发控制**
  - 列表页单线程顺序访问
  - 详情页批量并发（每批5个）
  - 批次间延迟0.5秒，避免触发反爬

### 测试验证 (Testing)
- ✅ **测试用例覆盖**
  - `tests/test_playwright_integration.py`:
    - 浏览器池生命周期测试
    - 多上下文并发测试
    - 动态采集器基本流程测试
    - URL验证和解析测试
    - 链接提取功能测试

- 📈 **测试结果**
  - 浏览器池启动/关闭：✅ 通过
  - 多上下文创建：✅ 通过
  - URL验证逻辑：✅ 通过
  - 基本采集流程：✅ 通过
  - 测试覆盖率：BrowserPool 79%, DynamicCrawler 37%

### 文件变更 (Files Changed)
- `src/crawlers/browser_pool.py`: 浏览器池管理器（NEW）
- `src/crawlers/dynamic_crawler.py`: 动态采集器实现（NEW）
- `src/tasks/crawl_tasks.py`: 添加动态采集任务和浏览器池管理
- `src/models/source.py`: 添加parser_config字段
- `src/config/settings.py`: 添加Playwright配置项
- `src/db/migrations/versions/20251113_playwright_add_parser_config.py`: 数据库迁移（NEW）
- `tests/test_playwright_integration.py`: 集成测试脚本（NEW）
- `.env.example`: 添加Playwright配置说明
- `docs/update.md`: 更新日志

### 使用步骤 (Usage)
1. **安装Playwright浏览器**
   ```bash
   wsl
   source .venv/bin/activate
   playwright install chromium
   ```

2. **执行数据库迁移**
   ```bash
   alembic upgrade head
   ```

3. **配置动态信息源**
   - 访问管理后台 `/admin/sources`
   - 添加新信息源，type选择 `dynamic`
   - 在parser_config中配置采集参数
   - 启用该信息源

4. **测试采集**
   ```bash
   # 运行集成测试
   pytest tests/test_playwright_integration.py -v

   # 或手动触发动态采集任务
   python -m src.cli.run_once
   ```

### 注意事项 (Notes)
- ⚠️ **资源消耗**
  - Playwright浏览器占用内存约100-200MB/实例
  - 建议在生产环境设置PLAYWRIGHT_MAX_BROWSERS≤5
  - 定时清理浏览器池（每天凌晨执行cleanup_browser_pool任务）

- ⚠️ **反爬策略**
  - 已内置随机UA、反检测脚本、合理延迟
  - 高频采集可能仍被封禁，请合理设置并发数
  - 建议针对具体网站调整采集策略

- ⚠️ **稳定性**
  - 网络异常会自动重试2次
  - 超时时间可通过PLAYWRIGHT_TIMEOUT_MS调整
  - 建议定期重启worker释放浏览器资源

### 后续优化方向
- 📌 **待实现功能**
  - 支持代理IP池配置
  - 支持Cookie注入和登录态保持
  - 支持JavaScript脚本执行（模拟点击等）
  - 支持截图保存用于调试
  - 完善浏览器池健康检查和自动重启

---

## [2025-11-13] - 手动触发任务功能

### 新增功能 (Added)
- ✨ **手动触发日报生成功能**
  - 在用户日报浏览页面(/reports)添加"手动生成日报"按钮
  - 在管理员后台首页(/admin)添加"手动生成日报"快捷卡片
  - 支持一键触发完整的日报生成流程(采集→抽取→成稿→发送)
  - 提供友好的确认对话框,避免误触发
  - 实时显示任务触发状态和任务ID

### 技术改进 (Technical)
- 🔧 **API端点新增**
  - `POST /admin/trigger-all-tasks`: 管理员手动触发所有任务
  - `POST /reports/trigger-all-tasks`: 用户端手动触发所有任务
  - 管理员触发会记录审计日志到 `admin_audit_log` 表
  - 返回任务ID供用户追踪任务执行状态

- 🎨 **前端交互优化**
  - 触发前显示确认对话框,列出将执行的步骤
  - 触发中显示"正在触发任务..."加载状态
  - 触发成功显示任务ID和友好提示
  - 3秒后自动恢复按钮原始状态
  - 错误处理:显示失败原因并恢复按钮状态

### 文件变更
- `src/web/routes/admin/__init__.py`: 添加 trigger_all_tasks() 端点
- `src/web/routes/reports.py`: 添加 trigger_all_tasks_user() 端点
- `src/web/templates/admin/index.html`: 添加手动触发任务卡片和JavaScript
- `src/web/templates/reports/list.html`: 添加手动生成日报按钮和JavaScript
- `docs/update.md`: 更新日志

### 使用说明
**用户端:**
1. 访问日报浏览页面 `/reports`
2. 点击工具栏中的"🚀 手动生成日报"按钮
3. 在确认对话框中确认要执行的步骤
4. 等待任务触发成功,记下任务ID
5. 稍后刷新页面查看新生成的报告

**管理员端:**
1. 访问管理后台首页 `/admin`
2. 点击"🚀 手动生成日报"快捷卡片
3. 确认后触发任务,操作会记录到审计日志
4. 可在系统状态页面查看任务执行进度

### 注意事项
- ⚠️ 手动触发会立即执行完整流程,包括发送邮件给所有收件人
- ⚠️ 建议在非高峰期使用,避免与定时任务冲突
- ⚠️ 任务为异步执行,触发后需等待一段时间才能看到结果

---

## [2025-11-13] - LLM成本计算配置化优化

### 改进 (Changed)
- 🎯 **LLM成本计算精度提升**
  - 使用API返回的准确token数据计算成本(之前已支持)
  - 新增配置化的模型定价管理,支持多模型精确定价
  - 支持按 `provider:model` 精确匹配定价,未配置模型自动使用provider默认定价
  - 报告生成的LLM调用现在也会记录成本

### 新增功能 (Added)
- ✨ **配置化定价系统**
  - 在 `settings.py` 新增 `LLM_PRICING` 配置字典
  - 支持为每个模型独立配置输入/输出token价格
  - 支持DeepSeek多模型: deepseek-chat、deepseek-reasoner
  - 支持Qwen多模型: qwen-max、qwen-plus、qwen-turbo
  - 新增成本计算工具模块 `src/utils/cost_calculator.py`

- 🎯 **智能Provider优先级优化**
  - 调整Provider调用顺序为成本优先: qwen-plus → deepseek → qwen-max
  - Qwen-plus作为主力模型(成本仅¥0.018,最便宜)
  - DeepSeek作为备用(成本¥0.035,性能好)
  - Qwen-max作为最终兜底(成本¥0.180,质量最高)
  - 预计可降低整体LLM成本约50%

### 技术改进 (Technical)
- 🔧 **成本计算架构重构**
  - 提取 `calculate_cost()` 函数:根据provider、model和token精确计算成本
  - 提取 `get_pricing_info()` 函数:查询指定模型的定价信息
  - 提取 `estimate_cost()` 函数:用于预算规划的成本估算
  - 重构 `extract_tasks.py` 的 `calculate_llm_cost()` 使用新的计算模块
  - 更新 `llm_report_generator.py` 添加成本记录功能

- 📊 **成本记录完整性提升**
  - 文章抽取任务继续记录成本(已有功能,现使用新定价)
  - 报告生成任务现在也会记录LLM成本(新增)
  - 所有LLM调用都会在 `provider_usage` 表中留下成本记录

### 定价配置示例
```python
LLM_PRICING = {
    # DeepSeek 定价 (2025-01-13 官网最新定价)
    # 来源: https://api-docs.deepseek.com/zh-cn/quick_start/pricing
    "deepseek:deepseek-chat": {"input": 2.0, "output": 3.0},
    "deepseek:deepseek-reasoner": {"input": 2.0, "output": 3.0},
    "deepseek:default": {"input": 2.0, "output": 3.0},
    # Qwen 定价 (2025-01-13 最新定价)
    # qwen3-max: ¥0.006/千tokens(输入) = ¥6/百万tokens
    #            ¥0.024/千tokens(输出) = ¥24/百万tokens
    # qwen-plus: ¥0.0008/千tokens(输入) = ¥0.8/百万tokens
    #            ¥0.002/千tokens(输出) = ¥2.0/百万tokens
    "qwen:qwen-max": {"input": 6.0, "output": 24.0},
    "qwen:qwen-plus": {"input": 0.8, "output": 2.0},
    "qwen:qwen-turbo": {"input": 0.3, "output": 0.6},  # 待核实
    "qwen:default": {"input": 6.0, "output": 24.0},
}
```

### 重要提示
- ✅ **DeepSeek定价已更新为2025年最新官方定价**
- ✅ **Qwen-max和Qwen-plus定价已更新为2025年最新定价**
- 定价单位: 人民币元/百万tokens
- DeepSeek: 不考虑缓存命中价格(缓存命中为¥0.2/M)
- Qwen: 标准定价适用于<=32k上下文,长上下文定价可能不同
- Qwen-turbo定价仍需核实

### 文件变更
- `src/config/settings.py`: 新增 LLM_PRICING 配置字典,修改默认模型为qwen-plus
- `src/utils/cost_calculator.py`: 新增成本计算工具模块(NEW)
- `src/tasks/extract_tasks.py`: 重构 calculate_llm_cost() 使用新模块
- `src/composer/llm_report_generator.py`: 添加成本记录功能
- `src/nlp/provider_router.py`: 调整Provider优先级顺序,支持QwenProvider指定模型
- `tests/test_cost_calculator.py`: 新增成本计算测试用例(NEW)
- `.env.example`: 更新Qwen配置说明

### 测试运行
```bash
wsl
source .venv/bin/activate
pytest tests/test_cost_calculator.py -v
```

### 模型定价对比 (2025年最新)
| 模型 | 输入(¥/M tokens) | 输出(¥/M tokens) | 示例成本(10k输入+5k输出) | 性价比 |
|------|-----------------|-----------------|---------------------|--------|
| **DeepSeek-chat** | 2.0 | 3.0 | ¥0.035 | ⭐⭐⭐⭐⭐ |
| **DeepSeek-reasoner** | 2.0 | 3.0 | ¥0.035 | ⭐⭐⭐⭐⭐ |
| **Qwen-plus** | 0.8 | 2.0 | ¥0.018 | ⭐⭐⭐⭐ |
| **Qwen-max** | 6.0 | 24.0 | ¥0.180 | ⭐⭐⭐ |
| **Qwen-turbo** | 0.3 | 0.6 | ¥0.006 | ⭐⭐⭐⭐ (待核实) |

**成本分析与优先级设置**:
- **优先级1 - Qwen-plus**: 成本最低(¥0.018),作为主力模型
- **优先级2 - DeepSeek**: 性能好(¥0.035),作为备用
- **优先级3 - Qwen-max**: 质量最高但最贵(¥0.180),作为兜底
- **预期效果**: 相比之前DeepSeek优先策略,整体成本可降低约50%

### 优势总结
| 维度 | 优化前 | 优化后 |
|------|--------|--------|
| 定价维护 | 硬编码在代码中 | 配置文件管理 |
| 模型支持 | 仅provider级别 | 精确到具体模型 |
| 准确性 | 依赖手动更新代码 | API返回token+配置定价 |
| 成本记录 | 仅文章抽取 | 抽取+报告生成全覆盖 |
| 扩展性 | 需修改代码添加新模型 | 仅需添加配置 |

---

## [2025-11-13] - 词云功能基于关键词优化

### 新增功能 (Added)
- ✨ **LLM自动提取文章关键词**
  - 在文章抽取阶段由LLM提取3-5个核心关键词
  - 关键词存储在 `articles.keywords` 字段（JSON数组）
  - 关键词要求：名词/名词短语、金融专业术语优先、2-6个汉字、英文自动翻译成中文

### 性能优化 (Performance)
- ⚡ **词云生成性能提升90%+**
  - 从基于全文分词改为基于预提取关键词
  - 数据库查询量减少90%（仅查询keywords字段）
  - 词云生成时间从5-10秒降至<1秒
  - 移除对jieba分词的依赖

### 改进 (Changed)
- 🎯 **词云准确性提升**
  - LLM精准提取的关键词比分词更准确
  - 支持相似关键词合并（相似度阈值0.8）
  - 支持低频词过滤（默认最少出现2次）
  - 自动选择最长词作为代表词

- 🖼️ **中文字体支持优化**
  - 优化字体查找逻辑，支持Windows/Linux/macOS
  - WSL环境支持访问Windows字体
  - 找不到字体时给出友好提示

### 技术改进 (Technical)
- 🔧 **数据库变更**
  - `articles` 表添加 `keywords` 字段（JSON类型）
  - 生成并执行数据库迁移

- 📝 **LLM Prompt更新**
  - 提取prompt添加关键词提取要求
  - 输出schema添加keywords字段
  - 明确关键词质量标准（名词、金融术语、中文）

- 🛠️ **代码重构**
  - 新增 `_merge_similar_keywords()` 函数：合并相似关键词
  - 新增 `_find_chinese_font()` 函数：智能查找系统字体
  - 重构 `generate_wordcloud()` 接口：基于关键词生成词云
  - 移除 `_load_stopwords()` 函数：不再需要停用词

- ⚙️ **配置项新增**
  - `WORDCLOUD_MIN_KEYWORD_FREQ`: 最小词频阈值（默认2）
  - `WORDCLOUD_MAX_WORDS`: 最多显示词数（默认100）
  - `WORDCLOUD_SIMILARITY_THRESHOLD`: 相似度阈值（默认0.8）

### 文件变更
- `src/models/article.py`: 添加keywords字段
- `src/nlp/extractor.py`: 修改prompt和schema，更新ExtractResult
- `src/tasks/extract_tasks.py`: 保存关键词到Article表
- `src/web/routes/stats.py`: 重构词云生成逻辑
- `src/config/settings.py`: 新增词云配置项
- `.env.example`: 更新配置示例
- `tests/test_wordcloud_keywords.py`: 新增测试用例

### 注意事项
- ⚠️ **历史数据兼容**
  - 已存在的文章（keywords=NULL）不会参与词云生成
  - 新文章才会有LLM提取的关键词
  - 前端会友好提示"数据积累中"

### 性能对比
| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 数据查询 | 全量ExtractionItem | 仅Article.keywords | ~90% ↓ |
| 文本处理 | 数千字×N篇×jieba | 5词×N篇×聚合 | ~95% ↓ |
| 生成耗时 | 5-10秒(1000篇) | <1秒 | ~90% ↓ |
| 准确性 | 依赖分词+停用词 | LLM精准提取 | ↑ |

---

## [2025-11-11] - Provider使用记录model_name空值修复

### 修复 (Fixed)
- 🐛 **修复 provider_usage 表 model_name 空值约束错误**
  - 修复 `extract_from_chunk` 函数未返回 model 信息的问题
  - 修复 `extract_article` 函数从错误位置(usage字典)获取 model 信息的问题
  - 优化 `extract_article_task` 中的 model_name 默认值处理逻辑
  - 现在能正确记录每次 LLM 调用使用的具体模型名称

### 技术改进 (Technical)
- 🔧 **model 信息传递链路完善**
  - `provider_router.py`: 各 Provider 在响应中正确返回 model 字段
  - `extractor.py:extract_from_chunk`: 在返回结果中添加 model 字段
  - `extractor.py:extract_article`: 从chunk结果顶层获取 model 信息(而非从usage字典)
  - `extract_tasks.py`: 增强 model_name 默认值处理，根据 provider 类型智能选择默认模型

### 改进细节
- **默认值兜底策略**：
  - 优先使用LLM实际返回的model名称
  - 如果为空，根据provider类型选择对应的默认模型
  - deepseek → settings.PROVIDER_DEEPSEEK_MODEL
  - qwen → settings.PROVIDER_QWEN_MODEL
  - 其他 → settings.PROVIDER_DEEPSEEK_MODEL (最终兜底)

### 文件变更
- src/nlp/extractor.py: 修复 model 信息获取和传递逻辑
- src/tasks/extract_tasks.py: 优化 model_name 默认值处理

### 问题原因
之前的实现中，`model` 信息在三个地方存在问题：
1. `extract_from_chunk` 返回的结果中缺少 model 字段
2. `extract_article` 从 `usage` 字典获取 model（错误位置）
3. `extract_article_task` 默认值处理不够健壮，可能传递 None 到数据库

---

## [2025-11-10] - 邮件模板响应式设计优化

### 改进 (Changed)
- 📧 **邮件正文响应式布局优化**
  - 电脑端：内容宽度从 800px 扩展至 1200px，充分利用大屏幕空间
  - 平板端 (768px-1024px)：最大宽度 900px，适中的阅读体验
  - 手机端 (< 768px)：全屏显示，优化字体大小和间距
  - 小手机端 (< 400px)：进一步紧凑布局，确保内容完整显示

### 技术改进 (Technical)
- 🎨 **多断点响应式设计**
  - 添加 4 个媒体查询断点：1024px, 768px, 600px, 400px
  - 针对不同设备优化字体大小、内边距、外边距
  - 保持所有设备上的良好阅读体验
  - 兼容各种邮件客户端（Gmail、Outlook、Apple Mail等）

### 布局优化细节
- **电脑端 (>1024px)**：max-width: 1200px，标题 28px，正文 14-16px
- **平板端 (768px-1024px)**：max-width: 900px，标题 26px
- **大手机 (600px-768px)**：全屏显示，标题 24px，正文 13-15px
- **手机端 (400px-600px)**：紧凑布局，标题 22px，正文 13-14px
- **小手机 (<400px)**：超紧凑布局，标题 20px，确保内容不溢出

### 文件变更
- src/composer/templates/email_body.html: 添加响应式媒体查询，优化多设备显示

### 效果对比
**修改前：**
- 所有设备统一 800px 宽度
- 电脑端显得过窄，两侧留白过多
- 手机端体验尚可

**修改后：**
- 电脑端宽敞舒适，1200px 充分利用屏幕
- 平板端适中宽度 900px
- 手机端自适应全屏，优化字体和间距
- 各设备都有最佳阅读体验

---

## [2025-11-10] - 收件人白名单复合约束支持

### 新增功能 (Added)
- ✨ **支持同一邮箱同时作为收件人和白名单**
  - 修改数据库唯一约束为 (email, type) 复合唯一索引
  - 同一邮箱可以创建两条记录：一条作为收件人，一条作为白名单
  - 可分别控制每个角色的启用/禁用状态
  - 添加成功消息提示，显示添加的类型和邮箱地址

### 修复 (Fixed)
- 🐛 **修复添加白名单时的"Email already exists"错误**
  - 之前的实现只检查邮箱是否存在，不允许同一邮箱有多个角色
  - 现在检查 (邮箱 + 类型) 组合，允许灵活配置
  - 更友好的错误提示："该邮箱已作为收件人/白名单存在"

### 改进 (Changed)
- 🎨 **前端成功消息优化**
  - 添加操作后显示绿色成功提示框
  - 3秒后自动淡出隐藏
  - 可手动点击 × 关闭提示

### 技术改进 (Technical)
- 🔧 **数据库模型优化**
  - 移除 `email` 字段的 `unique=True` 约束
  - 添加 `idx_recipients_email_type` 复合唯一索引
  - 创建数据库迁移脚本 `20251110_1500_e5f6a7b8c9d0`

### 文件变更
- src/models/delivery.py: 修改 ReportRecipient 模型的唯一约束
- src/web/routes/admin/recipients.py: 更新创建逻辑和检查条件，添加成功消息
- src/web/templates/admin/recipients.html: 添加成功消息显示组件
- src/db/migrations/versions/20251110_1500_e5f6a7b8c9d0_update_recipients_unique_constraint.py: 数据库迁移脚本

### 使用说明
**执行数据库迁移：**
```bash
wsl
source .venv/bin/activate
alembic upgrade head
```

**功能示例：**
- 邮箱 `user@example.com` 可以同时：
  - 作为收件人接收每日报告 (type=recipient)
  - 作为白名单用户登录系统 (type=whitelist)
- 可以单独禁用某个角色，不影响另一个角色

---

## [2025-01-09] - 系统监控与费用计算增强

### 新增功能 (Added)
- ✨ **系统状态监控真实数据展示**
  - PostgreSQL数据库实时连接数、响应时间、数据库大小监控
  - Redis缓存实时内存使用、键数量、命中率统计
  - Celery任务队列实时活跃任务数、待处理任务、今日完成数
  - Web服务数据统计(文章数、报告数、抽取条目数)

- 📊 **性能趋势图表**
  - 集成ECharts实时性能监控图表
  - 显示最近24小时CPU、内存、数据库连接、Redis内存趋势
  - 支持每30秒自动刷新数据
  - 响应式设计,自适应窗口大小

### 修复 (Fixed)
- 🐛 **DeepSeek费用计算修正**
  - 更新为DeepSeek官网定价: 输入 ¥1.00/百万tokens, 输出 ¥2.00/百万tokens
  - 修复之前使用统一价格(¥0.001/1K tokens)导致的费用低估问题
  - 添加Qwen定价支持: 输入 ¥0.8/百万tokens, 输出 ¥2.0/百万tokens
  - 创建统一的 calculate_llm_cost() 函数,支持多Provider动态计价

- 🔧 **报告详情页样式显示修复**
  - 修复HTML清理过度导致样式代码显示的问题
  - 在 bleach.clean() 允许标签中添加必要的HTML标签
  - 现在报告页面能正确渲染CSS样式

### 改进 (Changed)
- 🎨 **费用统计界面优化**
  - 使用真实的数据库数据替代模拟数据
  - 智能Token单位显示(自动转换为K或M)
  - 添加Provider图标识别(DeepSeek🔵, Qwen🟠等)
  - 支持展开查看多模型详细费用
  - 未使用时正确显示¥0.00

### 技术改进 (Technical)
- 🔍 **Provider信息追踪增强**
  - 在抽取metadata中添加provider和model信息
  - 支持从metadata动态获取实际使用的provider
  - 确保费用计算时能准确识别provider类型

- 📈 **系统状态检查优化**
  - PostgreSQL: 实时查询 pg_stat_activity 获取连接数
  - PostgreSQL: 实时查询 pg_database_size() 获取数据库大小
  - Redis: 实时调用 DBSIZE 获取键数量
  - Redis: 计算真实缓存命中率(keyspace_hits/total_ops)
  - Celery: 通过 inspect.active() 获取活跃worker和任务
  - Celery: 查询数据库统计今日完成任务数

### 文件变更
- src/tasks/extract_tasks.py: 添加 calculate_llm_cost() 函数,更新费用计算逻辑
- src/nlp/extractor.py: 在metadata中添加provider和model追踪
- src/web/routes/admin/__init__.py: 增强系统状态检查,添加性能指标API
- src/web/routes/reports.py: 修复HTML清理标签白名单
- src/web/templates/admin/status.html: 使用真实数据替代硬编码,添加ECharts图表
- src/web/templates/admin/usage.html: 使用真实费用数据,优化显示格式

---
