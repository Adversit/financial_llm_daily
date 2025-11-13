"""
统计与可视化路由
"""
from __future__ import annotations

import platform
from collections import Counter
from datetime import date, timedelta
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path
from typing import Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session
from wordcloud import WordCloud

from src.config.settings import settings
from src.db.session import get_db
from src.models.article import Article
from src.models.extraction import ExtractionItem
from src.models.report import Report
from src.models.system import SystemSetting
from src.models.user import User
from src.web.deps import get_current_user

router = APIRouter(prefix="/stats", tags=["Stats"])


def _templates(request: Request):
    return request.app.state.templates

# Redis 客户端
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=False)


@router.get("/summary")
async def stats_summary(
    current_user: User = Depends(get_current_user),
    target_date: Optional[date] = Query(default=None, description="统计日期（可选）"),
    db: Session = Depends(get_db),
):
    """提供基础统计数据（占位实现）"""
    total_reports = db.query(func.count(Report.id)).scalar() or 0
    total_items = db.query(func.count(ExtractionItem.id)).scalar() or 0

    region_rows = db.query(ExtractionItem.region, func.count(ExtractionItem.id)).group_by(ExtractionItem.region).all()
    layer_rows = db.query(ExtractionItem.layer, func.count(ExtractionItem.id)).group_by(ExtractionItem.layer).all()

    region_counts = {region: count for region, count in region_rows}
    layer_counts = {layer: count for layer, count in layer_rows}

    return {
        "date": target_date.isoformat() if target_date else None,
        "reports_total": total_reports,
        "items_total": total_items,
        "region_distribution": region_counts,
        "layer_distribution": layer_counts,
    }


def _get_date_range(scope: str, base_date: date) -> tuple[date, date]:
    """根据范围计算日期区间"""
    if scope == "day":
        return base_date, base_date
    elif scope == "week":
        start_date = base_date - timedelta(days=6)
        return start_date, base_date
    elif scope == "month":
        start_date = base_date - timedelta(days=29)
        return start_date, base_date
    else:
        return base_date, base_date


def _merge_similar_keywords(keywords: list[str]) -> dict[str, int]:
    """
    合并相似关键词并统计词频

    Args:
        keywords: 关键词列表

    Returns:
        合并后的词频字典 {关键词: 频次}
    """
    # 词频统计
    freq = Counter(keywords)

    # 相似度合并(阈值 0.8)
    merged = {}
    used = set()

    for word in freq:
        if word in used:
            continue

        # 查找相似词
        similar_group = [word]
        for other in freq:
            if other != word and other not in used:
                similarity = SequenceMatcher(None, word, other).ratio()
                if similarity > 0.8:
                    similar_group.append(other)
                    used.add(other)

        # 选择最长的作为代表词
        representative = max(similar_group, key=len)
        merged[representative] = sum(freq[w] for w in similar_group)
        used.add(word)

    return merged


def _find_chinese_font() -> Optional[str]:
    """
    查找系统可用的中文字体

    Returns:
        字体路径或字体名称，找不到返回 None
    """
    system = platform.system()

    # Windows 字体
    if system == "Windows":
        candidates = [
            "C:/Windows/Fonts/simhei.ttf",  # 黑体
            "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
            "SimHei",
            "Microsoft YaHei",
        ]
    # Linux 字体(WSL)
    elif system == "Linux":
        candidates = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/mnt/c/Windows/Fonts/simhei.ttf",  # WSL 访问 Windows 字体
        ]
    # macOS 字体
    else:
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "PingFang SC",
            "Heiti SC",
        ]

    # 查找可用字体
    for font in candidates:
        if font.startswith("/") or font.startswith("C:"):
            if Path(font).exists():
                logger.info(f"使用中文字体: {font}")
                return font
        else:
            try:
                from matplotlib import font_manager
                found = font_manager.findfont(font, fallback_to_default=False)
                if found:
                    logger.info(f"使用中文字体: {font}")
                    return font
            except Exception:
                continue

    # 降级: 使用 matplotlib 默认字体(可能显示方块)
    logger.warning("未找到中文字体，使用默认字体（可能显示为方块）")
    return None


@router.get("/wordcloud/view", response_class=HTMLResponse)
async def wordcloud_view(request: Request, current_user: User = Depends(get_current_user)):
    """词云展示页面"""
    return _templates(request).TemplateResponse(
        "stats/wordcloud.html",
        {"request": request, "current_user": current_user}
    )


@router.get("/wordcloud/image")
async def generate_wordcloud(
    current_user: User = Depends(get_current_user),
    scope: str = Query(default="day", description="范围: day|week|month"),
    target_date: Optional[date] = Query(default=None, description="基准日期"),
    width: int = Query(default=800, ge=400, le=2000),
    height: int = Query(default=600, ge=300, le=1500),
    db: Session = Depends(get_db),
):
    """生成词云图片（基于文章关键词，PNG格式）"""

    # 默认使用今天
    if not target_date:
        target_date = date.today()

    # 生成缓存键
    cache_key = f"wc:{scope}:{target_date.isoformat()}:{width}x{height}"

    # 检查缓存
    try:
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"词云缓存命中: {cache_key}")
            return Response(
                content=cached,
                media_type="image/png",
                headers={"Cache-Control": f"public, max-age={settings.WORDCLOUD_CACHE_TTL}"}
            )
    except Exception as e:
        logger.warning(f"Redis 缓存检查失败: {e}")

    # 计算日期范围
    start_date, end_date = _get_date_range(scope, target_date)
    logger.info(f"生成词云: 范围={scope}, 日期={start_date} 至 {end_date}")

    # 查询关键词(仅查询需要的字段)
    articles = (
        db.query(Article.keywords)
        .filter(
            func.date(Article.published_at) >= start_date,
            func.date(Article.published_at) <= end_date,
            Article.keywords.isnot(None)
        )
        .all()
    )

    if not articles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"日期范围 {start_date} 至 {end_date} 内无关键词数据，请等待文章处理完成"
        )

    # 聚合所有关键词
    all_keywords = []
    for article in articles:
        if article.keywords:
            all_keywords.extend(article.keywords)

    if not all_keywords:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到有效的关键词数据"
        )

    logger.info(f"收集到 {len(all_keywords)} 个关键词（来自 {len(articles)} 篇文章）")

    # 合并相似关键词并统计词频
    keyword_freq = _merge_similar_keywords(all_keywords)

    # 动态调整最小词频阈值
    # 数据量少时(如今日数据),自动降低阈值;数据量多时保持默认阈值
    base_min_freq = getattr(settings, 'WORDCLOUD_MIN_KEYWORD_FREQ', 2)

    if len(articles) < 10:  # 文章数少于10篇
        min_freq = 1  # 不过滤,显示所有关键词
        logger.info(f"文章数量较少({len(articles)}篇),最小词频阈值降为 {min_freq}")
    else:
        min_freq = base_min_freq

    keyword_freq = {k: v for k, v in keyword_freq.items() if v >= min_freq}

    if not keyword_freq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="关键词数量不足，无法生成词云"
        )

    logger.info(f"过滤后剩余 {len(keyword_freq)} 个关键词")

    # 生成词云
    try:
        # 查找中文字体
        font_path = _find_chinese_font()

        # 配置词云参数
        wc_kwargs = {
            "width": width,
            "height": height,
            "background_color": "white",
            "max_words": getattr(settings, 'WORDCLOUD_MAX_WORDS', 100),
            "relative_scaling": 0.5,
            "min_font_size": 10,
        }

        if font_path:
            wc_kwargs["font_path"] = font_path

        # 生成词云(使用词频字典)
        wc = WordCloud(**wc_kwargs)
        wc.generate_from_frequencies(keyword_freq)

        # 转换为 PNG
        image = wc.to_image()
        img_buffer = BytesIO()
        image.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()

        # 缓存到 Redis
        try:
            redis_client.setex(cache_key, settings.WORDCLOUD_CACHE_TTL, img_bytes)
            logger.info(f"词云已缓存: {cache_key}")
        except Exception as e:
            logger.warning(f"词云缓存失败: {e}")

        return Response(
            content=img_bytes,
            media_type="image/png",
            headers={
                "Cache-Control": f"public, max-age={settings.WORDCLOUD_CACHE_TTL}",
                "Content-Disposition": f'inline; filename="wordcloud_{scope}_{target_date}.png"'
            }
        )

    except Exception as e:
        logger.error(f"词云生成失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"词云生成失败: {str(e)}"
        )
