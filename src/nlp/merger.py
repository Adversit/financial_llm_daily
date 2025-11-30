"""
合并去重器模块

对抽取的多个结果进行合并、去重和冲突解决。
"""

import re
from collections import Counter
from typing import Dict, List

from loguru import logger
from simhash import Simhash


def normalize_fact(fact: str) -> str:
    """
    归一化事实文本

    Args:
        fact: 原始事实文本

    Returns:
        归一化后的文本
    """
    if not fact:
        return ""

    # 去除首尾空白
    text = fact.strip()

    # 全角转半角
    text = text.replace('。', '.').replace('，', ',').replace('！', '!') \
               .replace('？', '?').replace('：', ':').replace('；', ';') \
               .replace('"', '"').replace('"', '"').replace(''', "'") \
               .replace(''', "'").replace('（', '(').replace('）', ')')

    # 去除多余空白
    text = re.sub(r'\s+', ' ', text)

    # 中文数字转阿拉伯数字（简化版）
    chinese_num_map = {
        '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
        '六': '6', '七': '7', '八': '8', '九': '9', '十': '10',
        '零': '0', '〇': '0'
    }

    for cn, num in chinese_num_map.items():
        text = text.replace(cn, num)

    # 合并数字之间的空格，例如 "3 10" -> "30"
    text = re.sub(r'(\d)\s+10', lambda m: str(int(m.group(1)) * 10), text)
    text = re.sub(r'(?<=\d)\s+(?=\d)', '', text)

    return text


def calculate_edit_distance(s1: str, s2: str) -> int:
    """
    计算编辑距离（Levenshtein距离）

    Args:
        s1: 字符串1
        s2: 字符串2

    Returns:
        编辑距离
    """
    if s1 == s2:
        return 0

    len1, len2 = len(s1), len(s2)

    # 创建 DP 表
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

    # 初始化
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j

    # 填表
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(
                    dp[i - 1][j] + 1,      # 删除
                    dp[i][j - 1] + 1,      # 插入
                    dp[i - 1][j - 1] + 1   # 替换
                )

    return dp[len1][len2]


def is_similar_fact(fact1: str, fact2: str, threshold: int = 3) -> bool:
    """
    判断两个事实是否相似

    Args:
        fact1: 事实1
        fact2: 事实2
        threshold: SimHash 汉明距离阈值（默认3）

    Returns:
        是否相似
    """
    if not fact1 or not fact2:
        return False

    # 归一化
    norm1 = normalize_fact(fact1)
    norm2 = normalize_fact(fact2)

    # 完全相同
    if norm1 == norm2:
        return True

    # 使用 SimHash 计算相似度
    try:
        hash1 = Simhash(norm1)
        hash2 = Simhash(norm2)
        distance = hash1.distance(hash2)

        return distance <= threshold

    except Exception as e:
        logger.warning(f"SimHash 计算失败，回退到编辑距离: {e}")

        # 回退到编辑距离（适用于短文本）
        if len(norm1) < 50 and len(norm2) < 50:
            edit_dist = calculate_edit_distance(norm1, norm2)
            max_len = max(len(norm1), len(norm2))
            similarity = 1 - (edit_dist / max_len) if max_len > 0 else 0
            return similarity > 0.85

        return False


def deduplicate_facts(items: List[Dict]) -> List[Dict]:
    """
    对事实进行去重

    Args:
        items: 抽取项列表

    Returns:
        去重后的列表
    """
    if not items:
        return []

    deduped = []
    seen_facts = []

    for item in items:
        fact = item.get("fact", "")
        if not fact:
            continue

        # 检查是否与已有事实相似
        is_duplicate = False
        for existing_fact, existing_item in seen_facts:
            if is_similar_fact(fact, existing_fact):
                is_duplicate = True

                # 保留置信度更高的
                if item.get("confidence", 0) > existing_item.get("confidence", 0):
                    # 替换为置信度更高的
                    deduped.remove(existing_item)
                    deduped.append(item)
                    seen_facts.remove((existing_fact, existing_item))
                    seen_facts.append((fact, item))
                    logger.debug(f"替换重复事实（置信度更高）: {fact[:50]}...")

                break

        if not is_duplicate:
            deduped.append(item)
            seen_facts.append((fact, item))

    logger.info(f"去重完成: {len(items)} -> {len(deduped)}")
    return deduped


def resolve_conflicts(items: List[Dict]) -> List[Dict]:
    """
    解决 region 和 layer 的冲突

    Args:
        items: 抽取项列表

    Returns:
        解决冲突后的列表
    """
    if not items:
        return []

    # 统计各个字段的频次
    region_counter = Counter(item.get("region", "未知") for item in items)
    layer_counter = Counter(item.get("layer", "未知") for item in items)

    # 获取最常见的值
    most_common_region = region_counter.most_common(1)[0][0] if region_counter else "未知"
    most_common_layer = layer_counter.most_common(1)[0][0] if layer_counter else "未知"

    logger.info(
        f"最常见的 region: {most_common_region}, layer: {most_common_layer}"
    )

    # 对于 "未知" 的项，使用最常见的值填充
    for item in items:
        if item.get("region") == "未知" or not item.get("region"):
            item["region"] = most_common_region

        if item.get("layer") == "未知" or not item.get("layer"):
            item["layer"] = most_common_layer

    return items


def merge_extraction_results(chunk_results: List[Dict]) -> Dict:
    """
    合并多个分块的抽取结果

    Args:
        chunk_results: 分块结果列表

    Returns:
        合并后的结果字典
    """
    if not chunk_results:
        return {
            "items": [],
            "metadata": {
                "total_chunks": 0,
                "merged_count": 0,
                "dedup_count": 0
            }
        }

    # 收集所有项
    all_items = []
    for result in chunk_results:
        items = result.get("items", [])
        all_items.extend(items)

    original_count = len(all_items)
    logger.info(f"合并前总共 {original_count} 条")

    # 去重
    deduped_items = deduplicate_facts(all_items)
    dedup_count = original_count - len(deduped_items)

    # 解决冲突
    resolved_items = resolve_conflicts(deduped_items)

    logger.success(
        f"合并完成: 原始 {original_count} 条 -> "
        f"去重后 {len(deduped_items)} 条 -> "
        f"最终 {len(resolved_items)} 条"
    )

    return {
        "items": resolved_items,
        "metadata": {
            "total_chunks": len(chunk_results),
            "original_count": original_count,
            "merged_count": len(resolved_items),
            "dedup_count": dedup_count
        }
    }


def filter_low_quality_items(
    items: List[Dict],
    min_confidence: float = 0.6,
    min_fact_length: int = 10
) -> List[Dict]:
    """
    过滤低质量的抽取项

    Args:
        items: 抽取项列表
        min_confidence: 最小置信度
        min_fact_length: 最小事实长度

    Returns:
        过滤后的列表
    """
    filtered = []

    for item in items:
        # 检查置信度
        confidence = item.get("confidence", 0)
        if confidence < min_confidence:
            logger.debug(f"过滤低置信度项: {confidence}")
            continue

        # 检查事实长度
        fact = item.get("fact", "")
        if len(fact) < min_fact_length:
            logger.debug(f"过滤短事实: {fact}")
            continue

        # 检查必需字段
        if not fact or not item.get("region") or not item.get("layer"):
            logger.debug("过滤缺失字段的项")
            continue

        filtered.append(item)

    logger.info(f"质量过滤: {len(items)} -> {len(filtered)}")
    return filtered
