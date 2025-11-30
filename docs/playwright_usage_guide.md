# Playwright动态采集使用指南

## 概述

本系统已集成Playwright动态网页采集功能，用于采集需要JavaScript渲染的现代化网站。本指南将帮助你配置和使用动态采集功能。

## 快速开始

### 1. 环境准备

#### 安装Playwright浏览器
```bash
wsl  # 进入WSL环境
source .venv/bin/activate  # 激活虚拟环境
playwright install chromium  # 安装Chromium浏览器
```

#### 执行数据库迁移
```bash
alembic upgrade head
```

### 2. 配置环境变量

在 `.env` 文件中添加以下配置：

```bash
# Playwright配置
PLAYWRIGHT_MAX_BROWSERS=5        # 最大浏览器上下文数（建议3-5）
PLAYWRIGHT_HEADLESS=true         # 无头模式（生产环境建议true）
PLAYWRIGHT_TIMEOUT_MS=30000      # 页面加载超时（毫秒）
PLAYWRIGHT_WAIT_UNTIL=domcontentloaded  # 等待策略
CRAWL_CONCURRENCY_DYNAMIC=2      # 动态采集并发数
```

**等待策略说明：**
- `load`: 等待所有资源加载完成（最慢但最完整）
- `domcontentloaded`: 等待DOM加载完成（推荐，平衡速度和完整性）
- `networkidle`: 等待网络空闲（适用于AJAX密集型网站）

### 3. 添加动态信息源

#### 3.1 通过Web管理界面

1. 访问管理后台：`http://localhost:5000/admin/sources`
2. 点击"添加信息源"
3. 填写基本信息：
   - **名称**：为信息源起一个描述性名称
   - **类型**：选择 `dynamic`
   - **URL**：列表页URL（会从这个页面提取文章链接）
   - **启用**：勾选

4. 配置 `parser_config`（JSON格式）：

```json
{
  "need_scroll": false,
  "link_selectors": ["article a[href]", "a.title"],
  "wait_selector": null,
  "allow_patterns": ["/news/", "/article/"],
  "max_links": 20,
  "scroll_times": 3
}
```

#### 3.2 配置项详解

| 配置项 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| `need_scroll` | boolean | 否 | 是否需要滚动加载更多内容（默认false） |
| `link_selectors` | string[] | 是 | CSS选择器数组，用于提取文章链接 |
| `wait_selector` | string | 否 | 等待特定元素加载（如".article-content"） |
| `allow_patterns` | string[] | 否 | URL必须包含这些关键词之一才会被采集 |
| `max_links` | number | 否 | 最多采集多少个链接（默认20） |
| `scroll_times` | number | 否 | 滚动次数（默认3次，仅当need_scroll=true时生效） |

#### 3.3 配置示例

**示例1：简单新闻网站**
```json
{
  "need_scroll": false,
  "link_selectors": ["article a", ".news-list a[href]"],
  "allow_patterns": ["/news/"],
  "max_links": 15
}
```

**示例2：需要滚动加载的网站**
```json
{
  "need_scroll": true,
  "scroll_times": 5,
  "link_selectors": [".article-card a", "a.post-link"],
  "wait_selector": ".article-list",
  "allow_patterns": ["/post/", "/article/"],
  "max_links": 30
}
```

**示例3：复杂动态网站**
```json
{
  "need_scroll": true,
  "scroll_times": 3,
  "link_selectors": [
    "article h2 a",
    "div[data-testid='article'] a",
    "a[href*='/content/']"
  ],
  "wait_selector": "div[data-testid='article-list']",
  "allow_patterns": ["/content/", "/story/", "/news/"],
  "max_links": 25
}
```

## 如何找到正确的选择器

### 方法1：使用浏览器开发者工具

1. 打开目标网站
2. 按 `F12` 打开开发者工具
3. 点击"选择元素"工具（或按 `Ctrl+Shift+C`）
4. 点击页面上的文章链接
5. 在Elements面板中右键该元素 → Copy → Copy selector

### 方法2：使用控制台测试

在浏览器控制台中测试选择器是否有效：

```javascript
// 测试选择器是否能找到链接
document.querySelectorAll('article a[href]')

// 查看找到多少个元素
document.querySelectorAll('article a[href]').length

// 提取所有链接
Array.from(document.querySelectorAll('article a[href]')).map(a => a.href)
```

### 常见选择器模式

| 网站类型 | 推荐选择器 |
|---------|----------|
| 博客/新闻 | `article a`, `.post-title a`, `h2 a` |
| 列表页 | `.article-list a`, `.news-item a` |
| 卡片布局 | `.card a`, `.item-card a` |
| 特定属性 | `a[href*="/news/"]`, `a[data-type="article"]` |

## 测试和调试

### 运行集成测试

```bash
wsl
source .venv/bin/activate
pytest tests/test_playwright_integration.py -v -s
```

### 调试模式（查看浏览器运行）

临时修改环境变量：
```bash
PLAYWRIGHT_HEADLESS=false  # 显示浏览器窗口
```

### 添加调试截图

在 `parser_config` 中添加：
```json
{
  "debug_screenshot": true
}
```

截图会保存在 `debug/` 目录下（需要手动在代码中实现此功能）。

### 查看日志

动态采集器会输出详细的日志信息：

```bash
# 查看采集日志
tail -f logs/celery.log | grep "DynamicCrawler"

# 查看浏览器池状态
tail -f logs/celery.log | grep "BrowserPool"
```

## 性能优化建议

### 1. 并发控制

```bash
# 根据服务器资源调整
PLAYWRIGHT_MAX_BROWSERS=3  # 内存紧张时减少
CRAWL_CONCURRENCY_DYNAMIC=1  # 避免过载
```

### 2. 超时设置

```bash
# 网络较慢时增加超时
PLAYWRIGHT_TIMEOUT_MS=45000  # 增加到45秒
```

### 3. 选择器优化

- 使用更具体的选择器（如 `article.news-item a` 而非 `a`）
- 避免过于复杂的选择器（影响性能）
- 尽量使用ID或class选择器

### 4. 链接数量控制

```json
{
  "max_links": 10  // 降低链接数，加快采集速度
}
```

## 常见问题

### Q1: 浏览器启动失败

**错误信息：** `Browser pool startup failed`

**解决方案：**
```bash
# 重新安装Playwright浏览器
playwright install chromium

# 或安装系统依赖
playwright install-deps chromium
```

### Q2: 提取不到链接

**排查步骤：**

1. 检查选择器是否正确（使用浏览器控制台测试）
2. 检查 `allow_patterns` 是否过于严格
3. 尝试添加 `need_scroll: true`（可能需要滚动加载）
4. 检查 `wait_selector`，确保页面加载完成

### Q3: 采集速度太慢

**优化方案：**

1. 减少 `max_links` 数量
2. 使用 `domcontentloaded` 而非 `load`
3. 降低 `scroll_times`
4. 增加并发数（注意资源限制）

### Q4: 内存占用过高

**解决方案：**

```bash
# 降低浏览器实例数
PLAYWRIGHT_MAX_BROWSERS=2

# 定期清理浏览器池（添加定时任务）
# 在celery_app.py的beat_schedule中添加：
"cleanup-browser-pool": {
    "task": "src.tasks.crawl_tasks.cleanup_browser_pool",
    "schedule": crontab(hour=4, minute=0),  # 每天凌晨4点
}
```

### Q5: 被网站封禁

**反爬对策：**

1. 降低采集频率：增加延迟
2. 使用代理IP（需要自行实现）
3. 调整 `parser_config` 中的 `scroll_times` 和并发数
4. 分析网站具体的反爬策略并针对性优化

## 监控和维护

### 查看采集任务状态

访问管理后台：`http://localhost:5000/admin/status`

### 浏览器池健康检查

```python
# 在Python控制台中
from src.tasks.crawl_tasks import get_browser_pool

pool = get_browser_pool()
print(f"浏览器运行状态: {pool.is_running}")
print(f"活跃上下文数: {pool._context_count}")
```

### 定期维护

建议每周重启一次worker进程，释放浏览器资源：

```bash
# 停止worker
pkill -f "celery worker"

# 重新启动
./scripts/start_celery.sh
```

## 进阶技巧

### 1. 针对特定网站的自定义逻辑

如果某个网站需要特殊处理，可以在 `dynamic_crawler.py` 中添加网站特定逻辑：

```python
# 检测特定域名
if 'example.com' in self.source_url:
    # 执行特殊处理
    await self._handle_example_com(page)
```

### 2. 使用环境变量覆盖配置

```bash
# 临时调试某个源时覆盖配置
export PLAYWRIGHT_HEADLESS=false
export PLAYWRIGHT_TIMEOUT_MS=60000
```

### 3. 批量导入配置

准备JSON文件 `sources.json`：

```json
[
  {
    "name": "科技新闻网",
    "type": "dynamic",
    "url": "https://tech-news.example.com",
    "parser_config": {
      "link_selectors": ["article a"],
      "allow_patterns": ["/news/"]
    }
  }
]
```

然后使用脚本批量导入（需要自行编写导入脚本）。

## 最佳实践

1. **逐步测试**：先测试一个简单的网站，验证配置正确后再扩展
2. **监控资源**：密切关注CPU和内存使用情况
3. **合理延迟**：避免过于频繁的采集触发反爬
4. **日志审查**：定期查看日志，发现问题及时调整
5. **文档记录**：为每个配置的信息源写注释说明

## 技术支持

如遇到问题，请查看：

1. 系统日志：`logs/celery.log`
2. 测试输出：`pytest tests/test_playwright_integration.py -v -s`
3. 更新日志：`docs/update.md`

或联系系统管理员协助排查。

---

**最后更新：** 2025-11-13
**文档版本：** v1.0
