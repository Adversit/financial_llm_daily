"""
统计与可视化路由
"""
from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO
from typing import Optional

import jieba
import redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from loguru import logger
from matplotlib import font_manager
from sqlalchemy import func
from sqlalchemy.orm import Session
from wordcloud import WordCloud

from src.config.settings import settings
from src.db.session import get_db
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


def _load_stopwords(db: Session) -> set:
    """加载停用词列表（系统设置 + 内置默认）"""
    default_stopwords = {
        "的", "是", "在", "了", "和", "有", "与", "等", "将", "中",
        "为", "对", "以", "及", "个", "也", "被", "从", "并", "由",
        "或", "到", "可", "该", "上", "下", "其", "而", "但", "这",
        "那", "来", "去", "年", "月", "日", "时", "分", "秒"
    }

    # 从数据库加载自定义停用词
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.key == "stopwords").first()
        if setting and setting.value_json:
            custom_words = set(setting.value_json)
            return default_stopwords.union(custom_words)
    except Exception as e:
        logger.warning(f"Failed to load custom stopwords: {e}")

    return default_stopwords


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
    """生成词云图片（PNG格式）"""

    # 默认使用今天
    if not target_date:
        target_date = date.today()

    # 生成缓存键
    cache_key = f"wc:{scope}:{target_date.isoformat()}:{width}x{height}"

    # 检查缓存
    try:
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"Wordcloud cache hit: {cache_key}")
            return Response(content=cached, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        logger.warning(f"Redis cache check failed: {e}")

    # 计算日期范围
    start_date, end_date = _get_date_range(scope, target_date)

    # 查询数据 - 使用正确的join和filter语法
    from src.models.article import Article
    items = (
        db.query(ExtractionItem)
        .join(Article, ExtractionItem.article_id == Article.id)
        .filter(
            func.date(Article.published_at) >= start_date,
            func.date(Article.published_at) <= end_date
        )
        .all()
    )

    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for date range {start_date} - {end_date}"
        )

    # 合并所有文本
    texts = []
    for item in items:
        if item.fact:
            texts.append(item.fact)
        if item.opinion:
            texts.append(item.opinion)

    combined_text = " ".join(texts)

    if not combined_text.strip():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No valid text content found"
        )

    # 中文分词
    stopwords = _load_stopwords(db)
    words = jieba.cut(combined_text)
    filtered_words = [w for w in words if len(w.strip()) > 1 and w not in stopwords]
    segmented_text = " ".join(filtered_words)

    # 生成词云
    try:
        # 尝试使用系统中文字体
        font_path = None
        try:
            # 常见中文字体路径
            possible_fonts = [
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "SimHei",  # Windows
            ]
            for fp in possible_fonts:
                try:
                    font_manager.findfont(fp, fallback_to_default=False)
                    font_path = fp
                    break
                except:
                    continue
        except:
            pass

        wc_kwargs = {
            "width": width,
            "height": height,
            "background_color": "white",
            "max_words": 200,
            "relative_scaling": 0.5,
            "min_font_size": 10,
        }

        if font_path:
            wc_kwargs["font_path"] = font_path

        wc = WordCloud(**wc_kwargs)
        wc.generate(segmented_text)

        # 转换为 PNG
        image = wc.to_image()
        img_buffer = BytesIO()
        image.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()

        # 缓存到 Redis
        try:
            redis_client.setex(cache_key, settings.WORDCLOUD_CACHE_TTL, img_bytes)
            logger.info(f"Wordcloud cached: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache wordcloud: {e}")

        return Response(
            content=img_bytes,
            media_type="image/png",
            headers={
                "Cache-Control": f"public, max-age={settings.WORDCLOUD_CACHE_TTL}",
                "Content-Disposition": f'inline; filename="wordcloud_{scope}_{target_date}.png"'
            }
        )

    except Exception as e:
        logger.error(f"Wordcloud generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate wordcloud: {str(e)}"
        )
