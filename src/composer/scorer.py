"""
评分器模块

用于对抽取的事实和观点进行过滤、评分和排序。
"""

from datetime import datetime, timedelta
from typing import Dict, List

from loguru import logger
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.models.article import Article, ProcessingStatus
from src.models.extraction import ExtractionItem, Layer, Region
from src.models.source import Source
from src.utils.time_utils import get_local_now, to_local


def filter_items(db: Session, report_date: datetime.date) -> List[Dict]:
    """
    过滤抽取项

    Args:
        db: 数据库会话
        report_date: 报告日期

    Returns:
        过滤后的项列表（字典格式）
    """
    logger.info(f"开始过滤 {report_date} 的抽取项")

    # 查询当日的抽取项
    query = (
        db.query(ExtractionItem, Article, Source)
        .join(Article, ExtractionItem.article_id == Article.id)
        .join(Source, Article.source_id == Source.id)
        .filter(
            # 日期过滤：使用抓取日期而非发布日期
            Article.fetched_at >= report_date,
            Article.fetched_at < datetime.combine(
                report_date + timedelta(days=1), datetime.min.time()
            ),
            # 处理状态过滤
            Article.processing_status == ProcessingStatus.DONE,
            # 置信度过滤
            ExtractionItem.confidence >= settings.CONFIDENCE_THRESHOLD,
            # 金融相关性过滤（如果字段存在）
            # 注意：为了兼容历史数据，我们允许 finance_relevance 为 NULL
        )
    )

    results = query.all()

    filtered_items = []
    for item, article, source in results:
        # 内容长度过滤
        if article.content_len < settings.MIN_CONTENT_LEN:
            logger.debug(f"过滤短文章: {article.id}, 长度: {article.content_len}")
            continue

        # 转换为字典
        filtered_items.append({
            "id": item.id,
            "article_id": article.id,
            "article_title": article.title,
            "article_url": article.url,
            "fact": item.fact,
            "opinion": item.opinion or "",
            "region": item.region.value if hasattr(item.region, 'value') else str(item.region),
            "layer": item.layer.value if hasattr(item.layer, 'value') else str(item.layer),
            "evidence_span": item.evidence_span or "",
            "confidence": float(item.confidence),
            "finance_relevance": float(getattr(item, 'finance_relevance', 1.0) or 1.0),
            "source_id": source.id,
            "source_name": source.name,
            "source_weight": float(getattr(source, 'weight', 1.0) or 1.0),
            "published_at": article.published_at,
            "content_len": article.content_len,
        })

    logger.info(f"过滤完成: {len(filtered_items)} 条")
    return filtered_items


def calculate_score(item: Dict, current_time: datetime = None) -> float:
    """
    计算项的综合评分

    评分公式：
    score = 0.4 * 置信度 + 0.1 * 新近度 + 0.2 * 来源权威 + 0.3 * 金融相关性

    Args:
        item: 抽取项字典
        current_time: 当前时间（用于计算新近度）

    Returns:
        综合评分（0-1之间）
    """
    if current_time is None:
        current_time = get_local_now()

    # 1. 置信度
    confidence_score = item.get("confidence", 0.5)

    # 2. 新近度：发布时间距今的小时数（越近越高）
    # 金融日报场景下，数据都是昨天一天的，新近度用于区分同一天内的不同时段
    published_at = item.get("published_at")
    if published_at:
        published_at_local = to_local(published_at)
        hours_ago = (current_time - published_at_local).total_seconds() / 3600
        # 24小时内线性衰减：0小时=1.0, 24小时=0.0
        recency_score = max(0, 1 - (hours_ago / 24))
    else:
        recency_score = 0.5

    # 3. 权威性：来源权重
    authority_score = min(1.0, item.get("source_weight", 1.0))

    # 4. 金融相关性（新增）
    finance_relevance_score = item.get("finance_relevance", 1.0)

    # 综合评分（权重：置信40%、新近10%、来源20%、金融30%）
    score = (
        0.4 * confidence_score +
        0.1 * recency_score +
        0.2 * authority_score +
        0.3 * finance_relevance_score
    )

    return score


def section_and_sort(items: List[Dict]) -> Dict[str, Dict[str, List[Dict]]]:
    """
    分区并排序

    Args:
        items: 抽取项列表

    Returns:
        分区后的字典结构：
        {
            "国内": {
                "政治": [item1, item2, ...],
                "经济": [...],
                ...
            },
            "国外": { ... }
        }
    """
    if not items:
        return {}

    logger.info("开始分区和排序")

    # 计算每项的评分
    for item in items:
        item["score"] = calculate_score(item)

    # 分区
    sections: Dict[str, Dict[str, List[Dict]]] = {}

    for item in items:
        region = item.get("region", "未知")
        layer = item.get("layer", "未知")

        # 确保分区存在
        if region not in sections:
            sections[region] = {}

        if layer not in sections[region]:
            sections[region][layer] = []

        sections[region][layer].append(item)

    # 对每个分区内的项按评分降序排序
    for region in sections:
        for layer in sections[region]:
            sections[region][layer].sort(key=lambda x: x["score"], reverse=True)

    logger.info(f"分区完成，共 {len(sections)} 个区域")
    for region, layers in sections.items():
        layer_counts = {layer: len(items) for layer, items in layers.items()}
        logger.info(f"  {region}: {layer_counts}")

    return sections


def select_topn(sections: Dict[str, Dict[str, List[Dict]]], topn: int = 5) -> Dict[str, Dict[str, List[Dict]]]:
    """
    从每个分区选取 TopN

    Args:
        sections: 分区字典
        topn: 每个分区保留的最大数量

    Returns:
        筛选后的分区字典
    """
    if not sections:
        return {}

    logger.info(f"开始选取 TopN (N={topn})")

    topn_sections = {}

    for region, layers in sections.items():
        topn_sections[region] = {}
        for layer, items in layers.items():
            # 取前 N 个
            topn_sections[region][layer] = items[:topn]

            logger.debug(
                f"  {region}/{layer}: {len(items)} -> {len(topn_sections[region][layer])}"
            )

    return topn_sections


def get_all_items_sorted(sections: Dict[str, Dict[str, List[Dict]]]) -> List[Dict]:
    """
    获取所有项的排序列表（用于附件全量内容）

    Args:
        sections: 分区字典

    Returns:
        排序后的所有项列表
    """
    all_items = []

    for region, layers in sections.items():
        for layer, items in layers.items():
            all_items.extend(items)

    # 按评分降序排序
    all_items.sort(key=lambda x: x.get("score", 0), reverse=True)

    return all_items


def get_sections_statistics(sections: Dict[str, Dict[str, List[Dict]]]) -> Dict:
    """
    获取分区统计信息

    Args:
        sections: 分区字典

    Returns:
        统计信息字典
    """
    stats = {
        "total_items": 0,
        "regions": {},
    }

    for region, layers in sections.items():
        region_count = 0
        layer_stats = {}

        for layer, items in layers.items():
            count = len(items)
            layer_stats[layer] = count
            region_count += count

        stats["regions"][region] = {
            "total": region_count,
            "layers": layer_stats
        }
        stats["total_items"] += region_count

    return stats
