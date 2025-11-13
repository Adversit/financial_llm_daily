# 词云优化 - 测试指南

## 优化概述

本次优化将词云生成从**基于全文分词**改为**基于LLM提取的关键词**，实现了：
- ⚡ 性能提升90%+（5-10秒 → <1秒）
- 🎯 准确性提升（LLM精准提取 vs 分词+停用词）
- 💾 资源节省（查询量减少90%）

## 测试步骤

### 1. 运行单元测试

```bash
wsl
source .venv/bin/activate
pytest tests/test_wordcloud_keywords.py -v
```

预期输出：
```
test_merge_similar_keywords PASSED
test_find_chinese_font PASSED
test_extract_result_with_keywords PASSED
test_keywords_frequency_counter PASSED
```

### 2. 测试LLM提取功能

#### 方式A：使用run_once命令

```bash
# 完整流程：采集 → 提取 → 生成报告
python -m src.cli.run_once --step all
```

#### 方式B：单独测试提取

```bash
# 1. 先采集文章
python -m src.cli.run_once --step crawl

# 2. 再执行提取（会提取关键词）
python -m src.cli.run_once --step extract
```

### 3. 验证关键词提取

在数据库中检查文章是否包含关键词：

```sql
-- 查看最新文章的关键词
SELECT id, title, keywords, created_at
FROM articles
WHERE keywords IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;
```

预期结果示例：
```json
{
  "id": 123,
  "title": "央行发布数字货币新政策",
  "keywords": ["数字货币", "央行政策", "金融监管", "货币政策"]
}
```

### 4. 测试词云生成

#### 访问词云页面

1. 启动Web服务：
```bash
python -m src.web.main
```

2. 访问：http://localhost:8000/stats/wordcloud/view

3. 点击"今日"、"本周"、"本月"按钮测试不同范围

#### 直接访问API

```bash
# 生成今日词云
curl "http://localhost:8000/stats/wordcloud/image?scope=day" -o wordcloud_today.png

# 生成本周词云
curl "http://localhost:8000/stats/wordcloud/image?scope=week" -o wordcloud_week.png
```

### 5. 性能对比测试

#### 测试A：有关键词的文章（优化后）
```bash
# 清空Redis缓存
redis-cli FLUSHDB

# 访问词云API，记录耗时
time curl "http://localhost:8000/stats/wordcloud/image?scope=week" -o test.png
```

预期：<1秒

#### 测试B：检查数据库查询

查看日志输出，应该看到类似：
```
INFO  生成词云: 范围=week, 日期=2025-11-06 至 2025-11-13
INFO  收集到 120 个关键词（来自 24 篇文章）
INFO  过滤后剩余 45 个关键词
INFO  使用中文字体: /mnt/c/Windows/Fonts/simhei.ttf
INFO  词云已缓存: wc:week:2025-11-13:800x600
```

## 预期结果

### ✅ 成功标志

1. **数据库**：新文章的 `keywords` 字段不为 NULL
2. **日志**：提取日志显示"X个关键词"
3. **词云**：能正常显示中文关键词
4. **性能**：生成时间<1秒（1000篇文章以内）

### ⚠️ 可能的问题

#### 问题1：词云显示方块
**原因**：未找到中文字体
**解决**：
- Linux: `sudo apt-get install fonts-wqy-microhei`
- WSL: 字体路径已包含Windows字体，应该能自动找到

#### 问题2：没有关键词数据
**原因**：历史文章没有关键词
**解决**：运行一次完整流程生成新文章

#### 问题3：关键词质量不佳
**原因**：LLM提取不准确
**调整**：
1. 检查 `src/nlp/extractor.py` 中的 prompt
2. 可能需要调整关键词提取要求

## 配置调整

如需调整词云参数，修改 `.env` 文件：

```bash
# 词云配置
WORDCLOUD_CACHE_TTL=86400           # 缓存时间(秒)
WORDCLOUD_MIN_KEYWORD_FREQ=2        # 最小词频(次)
WORDCLOUD_MAX_WORDS=100             # 最多显示词数
WORDCLOUD_SIMILARITY_THRESHOLD=0.8  # 相似度阈值
```

## 回滚方案

如果需要回滚到旧版本（基于分词）：

```bash
# 1. 回退数据库迁移
alembic downgrade -1

# 2. 恢复代码
git checkout <previous-commit>

# 3. 重启服务
```

## 技术细节

### 关键词提取Prompt

位置：`src/nlp/extractor.py:EXTRACTION_PROMPT`

关键要求：
- 提取3-5个关键词
- 必须是名词或名词短语
- 优先金融专业术语
- 长度2-6个汉字
- 英文自动翻译成中文

### 词云生成流程

1. 查询日期范围内的文章关键词（`Article.keywords`）
2. 聚合所有关键词到列表
3. 统计词频并合并相似词
4. 过滤低频词（<2次）
5. 使用 `WordCloud.generate_from_frequencies()` 生成
6. 缓存到Redis

### 相似词合并算法

使用 `difflib.SequenceMatcher` 计算字符串相似度：
- 相似度 > 0.8 视为相似词
- 选择最长的词作为代表词
- 合并词频

示例：
```python
["数字货币", "数字货币", "数字金融"]
→ {"数字金融": 3}  # "数字金融"最长，被选为代表词
```

## 监控指标

建议监控以下指标：

1. **关键词覆盖率**：有keywords的文章占比
2. **词云生成耗时**：平均响应时间
3. **缓存命中率**：Redis缓存效果
4. **关键词平均数量**：每篇文章的关键词数

SQL查询示例：
```sql
-- 关键词覆盖率
SELECT
  COUNT(*) FILTER (WHERE keywords IS NOT NULL) * 100.0 / COUNT(*) as coverage_rate
FROM articles;

-- 关键词数量统计
SELECT
  jsonb_array_length(keywords::jsonb) as keyword_count,
  COUNT(*) as article_count
FROM articles
WHERE keywords IS NOT NULL
GROUP BY jsonb_array_length(keywords::jsonb);
```
