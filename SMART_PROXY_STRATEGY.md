# 智能代理策略使用指南

## ✅ 功能验证成功

智能代理策略已完整实现并通过所有测试！

### 测试结果
```
✓ 国内外域名自动识别
✓ 失败后自动切换策略
✓ 真实采集代理应用
✓ 统计信息完整
```

## 🎯 核心功能

### 1. 自动域名识别

系统自动识别域名类型，智能选择是否使用代理：

**国内域名（不使用代理）：**
- 新浪财经 (finance.sina.com.cn) → ❌ 不使用代理
- 东方财富 (eastmoney.com) → ❌ 不使用代理
- 财联社 (cls.cn) → ❌ 不使用代理
- ...更多国内网站

**国外域名（使用代理）：**
- BBC (bbc.com) → ✅ 使用代理
- 路透社 (reuters.com) → ✅ 使用代理
- 彭博社 (bloomberg.com) → ✅ 使用代理
- ...更多国外网站

### 2. 智能失败切换

当访问连续失败时，自动切换代理策略：

```
尝试1: 不使用代理 -> 失败
尝试2: 不使用代理 -> 失败
尝试3: 不使用代理 -> 失败
----自动切换----
尝试4: 使用代理 -> 成功！
```

**切换规则：**
- 默认失败阈值：3次
- 切换后保持时间：1小时
- 成功后清除失败记录

### 3. 策略缓存

切换后的策略会缓存1小时，避免频繁切换：

```python
# 第一次访问 unknown-site.com
失败3次 -> 切换为"使用代理"

# 后续1小时内访问 unknown-site.com
直接使用"使用代理"（无需再次判断）
```

## 📖 使用方法

### 配置代理服务器

在 `.env` 文件中设置：

```bash
PLAYWRIGHT_PROXY=http://127.0.0.1:7890
```

### 代码自动应用

无需修改任何代码，系统会自动：

1. **初始化时**：读取代理配置
2. **访问网站时**：根据域名选择策略
3. **失败时**：自动切换并重试
4. **成功时**：记录成功，清除失败计数

## 🔍 工作流程

### 场景1：访问国内网站

```
1. 用户配置信息源: https://finance.sina.com.cn/
2. 系统识别: 国内域名
3. 策略决定: 不使用代理
4. 直接访问: 成功 ✅
```

### 场景2：访问国外网站

```
1. 用户配置信息源: https://www.bbc.com/news
2. 系统识别: 国外域名
3. 策略决定: 使用代理 (http://127.0.0.1:7890)
4. 通过代理访问: 成功 ✅
```

### 场景3：访问失败自动切换

```
1. 用户配置信息源: https://unknown-site.example.com/
2. 系统识别: 未知域名
3. 策略决定: 默认不使用代理
4. 第1次访问: 失败 ❌ (失败计数: 1/3)
5. 第2次访问: 失败 ❌ (失败计数: 2/3)
6. 第3次访问: 失败 ❌ (失败计数: 3/3)
7. 自动切换: 使用代理
8. 第4次访问: 成功 ✅
9. 策略缓存: 1小时内都使用代理
```

## 🛠️ 配置选项

### 在proxy_strategy.py中配置

```python
class ProxyStrategy:
    # 国内域名列表（不需要代理）
    DOMESTIC_DOMAINS = [
        'sina.com.cn',
        'eastmoney.com',
        # 可以添加更多...
    ]

    # 国外域名列表（需要代理）
    FOREIGN_DOMAINS = [
        'bbc.com',
        'reuters.com',
        # 可以添加更多...
    ]

    def __init__(self, proxy_url: Optional[str] = None, max_failures: int = 3):
        # max_failures: 失败多少次后切换策略（默认3次）
        pass
```

### 添加自定义域名

编辑 `src/crawlers/proxy_strategy.py`：

```python
# 添加到国内域名列表
DOMESTIC_DOMAINS = [
    # ...现有域名...
    'your-custom-site.com',  # 你的自定义域名
]

# 添加到国外域名列表
FOREIGN_DOMAINS = [
    # ...现有域名...
    'your-foreign-site.com',  # 你的自定义域名
]
```

## 📊 统计信息

查看代理策略使用情况：

```python
from src.crawlers.proxy_strategy import get_proxy_strategy

strategy = get_proxy_strategy()
stats = strategy.get_statistics()

print(f"失败记录数: {stats['failure_records']}")
print(f"策略切换数: {stats['strategy_switches']}")
print(f"详细信息: {stats['details']}")
```

输出示例：
```
失败记录数: 0
策略切换数: 1
详细信息: {
    'switches': {
        'unknown-site.com': {
            'use_proxy': True,
            'switch_time': '2025-11-13 14:35:31'
        }
    }
}
```

## 🧪 测试

运行智能代理策略测试：

```bash
wsl
source .venv/bin/activate
export PLAYWRIGHT_PROXY='http://127.0.0.1:7890'
python scripts/test_smart_proxy.py
```

测试覆盖：
1. ✅ 国内外域名自动识别
2. ✅ 失败后自动切换策略
3. ✅ 真实网站采集（新浪财经 + BBC）
4. ✅ 统计信息查询

## 💡 最佳实践

### 1. 代理服务器配置

```bash
# .env文件
PLAYWRIGHT_PROXY=http://127.0.0.1:7890

# 如果需要认证
PLAYWRIGHT_PROXY=http://username:password@127.0.0.1:7890
```

### 2. 添加常用网站到域名列表

将你经常采集的网站添加到 `DOMESTIC_DOMAINS` 或 `FOREIGN_DOMAINS`，避免首次访问判断失误。

### 3. 调整失败阈值

根据网络稳定性调整 `max_failures`：

```python
# 网络稳定：降低阈值，快速切换
strategy = ProxyStrategy(proxy_url=proxy, max_failures=2)

# 网络不稳定：提高阈值，避免误切换
strategy = ProxyStrategy(proxy_url=proxy, max_failures=5)
```

### 4. 监控切换日志

查看日志了解策略切换情况：

```bash
tail -f logs/celery.log | grep "策略切换"
```

## ⚙️ 高级配置

### 自定义域名判断逻辑

修改 `src/crawlers/proxy_strategy.py`：

```python
def get_proxy_for_url(self, url: str) -> Optional[str]:
    domain = self._extract_domain(url)

    # 自定义逻辑：特定端口使用代理
    if ':8080' in url:
        return self.proxy_url

    # 自定义逻辑：特定路径使用代理
    if '/api/' in url:
        return self.proxy_url

    # 原有逻辑
    if self._is_domestic_domain(domain):
        return None
    # ...
```

### 不同网站使用不同代理

```python
def get_proxy_for_url(self, url: str) -> Optional[str]:
    domain = self._extract_domain(url)

    # 特定网站使用特定代理
    if 'special-site.com' in domain:
        return 'http://127.0.0.1:8888'  # 专用代理

    # 其他使用默认代理
    if self._is_foreign_domain(domain):
        return self.proxy_url

    return None
```

## 🐛 故障排查

### Q1: 切换不生效

**原因**：策略已缓存

**解决**：等待1小时或手动重置

```python
from src.crawlers.proxy_strategy import get_proxy_strategy

strategy = get_proxy_strategy()
strategy.reset()  # 清除所有缓存
```

### Q2: 频繁切换

**原因**：失败阈值太低或网络不稳定

**解决**：提高 `max_failures`

```python
# 在 dynamic_crawler.py 中修改
self.proxy_strategy = get_proxy_strategy(
    proxy_url=proxy_url,
    max_failures=5  # 提高到5次
)
```

### Q3: 特定网站总是失败

**原因**：可能需要手动添加到域名列表

**解决**：添加到相应的域名列表

```python
# proxy_strategy.py
DOMESTIC_DOMAINS = [
    # ...
    'problematic-site.com',  # 添加到这里
]
```

## 📈 性能影响

智能代理策略对性能的影响：

| 操作 | 额外开销 | 说明 |
|------|---------|------|
| 域名判断 | <1ms | 简单字符串匹配 |
| 失败记录 | <1ms | 字典操作 |
| 策略切换 | <1ms | 更新缓存 |
| 代理访问 | +10-50ms | 代理转发延迟 |

**总体影响**：几乎可以忽略不计

## 🔒 安全建议

1. **不要在代码中硬编码代理地址**
2. **使用环境变量管理代理配置**
3. **定期检查代理服务器安全性**
4. **生产环境使用HTTPS代理**
5. **避免在日志中记录代理密码**

## 📝 日志示例

正常运行时的日志：

```
2025-11-13 14:35:14 | INFO  | 代理策略初始化: proxy=http://127.0.0.1:7890, max_failures=3
2025-11-13 14:35:14 | DEBUG | [finance.sina.com.cn] 国内域名，不使用代理
2025-11-13 14:35:21 | DEBUG | [bbc.com] 国外域名，使用代理
2025-11-13 14:35:23 | INFO  | 使用代理: http://127.0.0.1:7890
2025-11-13 14:35:31 | WARNING | [unknown-site.com] 访问失败 (3/3), 当前策略: use_proxy=False
2025-11-13 14:35:31 | WARNING | [unknown-site.com] 策略切换: False -> True (使用代理)
```

## 🎉 总结

智能代理策略为你的采集系统提供：

✅ **自动化**：无需手动配置每个网站
✅ **智能化**：根据域名和失败情况自动决策
✅ **容错性**：失败后自动切换策略
✅ **高效性**：缓存策略避免重复判断
✅ **灵活性**：支持自定义域名和规则

现在你可以：
1. 配置一次代理，全局生效
2. 国内外网站自动识别
3. 访问失败自动容错
4. 轻松扩展域名列表

---

**最后更新**：2025-11-13
**测试状态**：✅ 全部通过
**生产就绪**：✅ 是
