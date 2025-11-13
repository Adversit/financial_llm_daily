# Playwright动态采集 - 快速入门

## ✅ 功能验证

Playwright动态采集功能已经成功集成并通过测试！

### 测试结果

```bash
✓ 浏览器池启动成功
✓ 动态采集器创建成功
✓ 成功访问网页并获取内容
✓ 完整采集流程运行正常
```

## 🚀 快速开始

### 1. 环境准备（已完成）

```bash
wsl
source .venv/bin/activate
playwright install chromium
alembic upgrade head
```

### 2. 运行功能测试

```bash
# 基础功能测试
python scripts/test_simple_dynamic.py

# 完整集成测试
pytest tests/test_playwright_integration.py -v
```

## 📝 配置你的第一个动态信息源

### 方式1：通过Web界面

1. 访问管理后台：`http://localhost:5000/admin/sources`
2. 点击"添加信息源"
3. 填写配置：

**基本信息：**
- 名称：`财联社快讯`
- 类型：`dynamic`
- URL：`https://www.cls.cn/telegraph`
- 启用：勾选

**parser_config配置：**
```json
{
  "need_scroll": true,
  "scroll_times": 3,
  "link_selectors": [
    "a.article-link",
    ".telegraph-list a[href]"
  ],
  "wait_selector": ".telegraph-list",
  "allow_patterns": ["/telegraph/"],
  "max_links": 15
}
```

### 方式2：通过SQL直接插入

```sql
INSERT INTO sources (name, type, url, enabled, parser_config, region_hint)
VALUES (
  '财联社快讯',
  'dynamic',
  'https://www.cls.cn/telegraph',
  true,
  '{
    "need_scroll": true,
    "scroll_times": 3,
    "link_selectors": ["a.article-link", ".telegraph-list a[href]"],
    "wait_selector": ".telegraph-list",
    "allow_patterns": ["/telegraph/"],
    "max_links": 15
  }'::jsonb,
  '国内'
);
```

## 🎯 推荐的国内财经网站配置

### 1. 新浪财经

```json
{
  "name": "新浪财经",
  "type": "dynamic",
  "url": "https://finance.sina.com.cn/",
  "parser_config": {
    "need_scroll": false,
    "link_selectors": ["a[href*='finance.sina.com.cn/']"],
    "allow_patterns": ["/stock/", "/money/", "/china/"],
    "max_links": 20
  }
}
```

### 2. 东方财富网

```json
{
  "name": "东方财富网",
  "type": "dynamic",
  "url": "https://www.eastmoney.com/",
  "parser_config": {
    "need_scroll": true,
    "scroll_times": 2,
    "link_selectors": [".news-item a", "a[href*='finance.eastmoney.com']"],
    "allow_patterns": ["/news/", "/a/"],
    "max_links": 15
  }
}
```

### 3. 金融界

```json
{
  "name": "金融界",
  "type": "dynamic",
  "url": "https://www.jrj.com.cn/",
  "parser_config": {
    "need_scroll": false,
    "link_selectors": [".news-list a", "a.title"],
    "allow_patterns": ["/stock/", "/finance/", "/money/"],
    "max_links": 20
  }
}
```

## 🔍 如何找到正确的选择器

### 步骤1：打开开发者工具

1. 访问目标网站
2. 按 `F12` 打开开发者工具
3. 点击"选择元素"工具（或 `Ctrl+Shift+C`）

### 步骤2：选择文章链接

点击页面上的文章标题，在Elements面板查看HTML结构

### 步骤3：测试选择器

在Console中测试：

```javascript
// 测试选择器
document.querySelectorAll('a.article-link')

// 查看数量
document.querySelectorAll('a.article-link').length

// 提取链接
Array.from(document.querySelectorAll('a.article-link')).map(a => a.href)
```

### 步骤4：复制选择器

右键元素 → Copy → Copy selector

## ⚙️ 配置项说明

| 配置项 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| `need_scroll` | boolean | 否 | 是否需要滚动加载（默认false） |
| `scroll_times` | number | 否 | 滚动次数（默认3） |
| `link_selectors` | string[] | 是 | CSS选择器数组 |
| `wait_selector` | string | 否 | 等待元素选择器 |
| `allow_patterns` | string[] | 否 | URL过滤规则 |
| `max_links` | number | 否 | 最大链接数（默认20） |

## 🎬 运行采集

### 方式1：手动触发

访问管理后台：`http://localhost:5000/admin`
点击"手动生成日报"按钮

### 方式2：命令行运行

```bash
wsl
source .venv/bin/activate
python -m src.cli.run_once
```

### 方式3：定时任务（已配置）

系统会在每天早上05:30自动运行采集任务

## 📊 监控和日志

### 查看采集状态

访问：`http://localhost:5000/admin/status`

### 查看日志

```bash
# 实时查看采集日志
tail -f logs/celery.log | grep "DynamicCrawler"

# 查看浏览器池状态
tail -f logs/celery.log | grep "BrowserPool"
```

### 查看采集结果

访问：`http://localhost:5000/reports`

## 🐛 常见问题

### Q1: 提取不到链接

**解决方案：**
1. 使用浏览器开发者工具验证选择器
2. 尝试添加 `need_scroll: true`
3. 检查 `allow_patterns` 是否过于严格

### Q2: 采集速度慢

**优化方案：**
1. 降低 `max_links` 数量
2. 使用 `domcontentloaded` 而非 `load`
3. 减少 `scroll_times`

### Q3: 内存占用高

**解决方案：**
```bash
# .env 中调整配置
PLAYWRIGHT_MAX_BROWSERS=3  # 降低浏览器数
CRAWL_CONCURRENCY_DYNAMIC=1  # 降低并发数
```

## 📚 更多文档

- 详细使用指南：`docs/playwright_usage_guide.md`
- 更新日志：`docs/update.md`
- 测试文件：`tests/test_playwright_integration.py`

## 🎉 完成

恭喜！你现在可以使用Playwright采集动态网站了！

**下一步：**
1. 在管理后台配置你的第一个动态信息源
2. 运行采集并查看结果
3. 根据实际情况调整配置

有任何问题请查看 `docs/playwright_usage_guide.md` 或系统日志。
