# 更新日志

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
