"""
报告构建器模块

用于生成 HTML 格式的报告正文和附件。
"""

import asyncio
import os
from datetime import date, datetime
from typing import Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

from src.composer.llm_report_generator import generate_section_report_with_llm
from src.config.settings import settings
from src.utils.time_utils import get_local_now, to_local


def _limit_attachment_items(
    sections: Dict[str, Dict[str, List[Dict]]],
    max_items: int
) -> Dict[str, Dict[str, List[Dict]]]:
    """
    限制附件中的条目数量，按评分保留前 N 条

    Args:
        sections: 分区字典
        max_items: 最大条目数

    Returns:
        截断后的分区字典
    """
    # 收集所有条目并按评分排序
    all_items = []
    for region, layers in sections.items():
        for layer, items in layers.items():
            for item in items:
                all_items.append((region, layer, item))

    # 按评分降序排序
    all_items.sort(key=lambda x: x[2].get("score", 0), reverse=True)

    # 截断
    limited_items = all_items[:max_items]

    # 重新组织为分区结构
    limited_sections: Dict[str, Dict[str, List[Dict]]] = {}
    for region, layer, item in limited_items:
        if region not in limited_sections:
            limited_sections[region] = {}
        if layer not in limited_sections[region]:
            limited_sections[region][layer] = []
        limited_sections[region][layer].append(item)

    logger.info(
        f"附件截断完成：{len(all_items)} 条 -> {len(limited_items)} 条"
    )

    return limited_sections


def generate_section_reports(
    sections: Dict[str, Dict[str, List[Dict]]],
    use_llm: bool = None
) -> Dict[str, Dict[str, str]]:
    """
    生成分区报告（8个分区：国内/国外 × 4个层级）

    Args:
        sections: 分区字典（包含全量事实观点）
        use_llm: 是否使用 LLM 生成（None=使用配置默认值）

    Returns:
        分区报告字典 {region: {layer: report_text}}
    """
    if not sections:
        return {}

    # 确定使用哪种模式
    if use_llm is None:
        use_llm = settings.REPORT_USE_LLM_SECTIONS

    if use_llm:
        logger.info("使用 LLM 生成分区报告")
        return _generate_section_reports_with_llm(sections)
    else:
        logger.info("不生成分区报告，仅展示事实观点卡片")
        return {}


def _generate_section_reports_with_llm(sections: Dict[str, Dict[str, List[Dict]]]) -> Dict[str, Dict[str, str]]:
    """
    使用 LLM 生成所有分区的报告

    Args:
        sections: 分区字典

    Returns:
        分区报告字典
    """
    section_reports = {}

    # 对每个分区调用 LLM
    for region, layers in sections.items():
        section_reports[region] = {}

        for layer, items in layers.items():
            if not items:
                continue

            logger.info(f"生成【{region}-{layer}】报告，共 {len(items)} 条事实观点")

            try:
                # 调用 LLM（使用 asyncio.run）
                try:
                    # 尝试获取现有事件循环
                    loop = asyncio.get_running_loop()
                    # 如果已经在事件循环中，使用 ThreadPoolExecutor
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            generate_section_report_with_llm(region, layer, items)
                        )
                        report = future.result()
                except RuntimeError:
                    # 没有运行中的事件循环，直接使用 asyncio.run
                    report = asyncio.run(generate_section_report_with_llm(region, layer, items))

                if report:
                    section_reports[region][layer] = report
                    logger.success(f"【{region}-{layer}】报告生成成功，长度: {len(report)} 字符")
                else:
                    logger.warning(f"【{region}-{layer}】报告生成失败")

            except Exception as e:
                logger.error(f"【{region}-{layer}】报告生成异常: {e}", exc_info=True)

    return section_reports


def build_email_body(
    report_date: date,
    sections_topn: Dict[str, Dict[str, List[Dict]]],
    section_reports: Dict[str, Dict[str, str]] = None,
    template_path: Optional[str] = None,
) -> str:
    """
    生成邮件正文 HTML

    Args:
        report_date: 报告日期
        sections_topn: TopN 分区字典（用于展示卡片）
        section_reports: 分区报告字典（LLM 生成的分析报告）
        template_path: 模板路径（可选）

    Returns:
        HTML 字符串
    """
    logger.info("开始生成邮件正文 HTML")

    # 设置模板路径
    if template_path is None:
        template_dir = os.path.join(
            os.path.dirname(__file__), "templates"
        )
    else:
        template_dir = os.path.dirname(template_path)

    # 初始化 Jinja2 环境
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"])
    )

    # 加载模板
    template = env.get_template("email_body.html")

    # 格式化日期
    date_str = report_date.strftime("%Y年%m月%d日")

    # 渲染模板
    html = template.render(
        report_date=date_str,
        sections=sections_topn,
        section_reports=section_reports or {},
    )

    logger.success("邮件正文 HTML 生成完成")
    return html


def build_attachment(
    report_date: date,
    sections_full: Dict[str, Dict[str, List[Dict]]],
    template_path: Optional[str] = None,
) -> str:
    """
    生成附件 HTML

    Args:
        report_date: 报告日期
        sections_full: 全量分区字典
        template_path: 模板路径（可选）

    Returns:
        HTML 字符串
    """
    logger.info("开始生成附件 HTML")

    # 检查总条目数，如果超过限制，进行截断
    total_items = sum(
        len(items)
        for layers in sections_full.values()
        for items in layers.values()
    )

    max_items = settings.ATTACHMENT_MAX_ITEMS
    if total_items > max_items:
        logger.warning(
            f"⚠️ 附件内容过多 ({total_items} 条)，超过限制 ({max_items} 条)，将按评分截断"
        )
        # 截断到前 N 条（按评分排序）
        sections_full = _limit_attachment_items(sections_full, max_items)

    # 设置模板路径
    if template_path is None:
        template_dir = os.path.join(
            os.path.dirname(__file__), "templates"
        )
    else:
        template_dir = os.path.dirname(template_path)

    # 初始化 Jinja2 环境
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"])
    )

    # 加载模板
    template = env.get_template("attachment.html")

    # 格式化日期
    date_str = report_date.strftime("%Y年%m月%d日")

    # 渲染模板
    html = template.render(
        report_date=date_str,
        sections_full=sections_full,
    )

    logger.success("附件 HTML 生成完成")
    return html


def build_metadata(
    sections: Dict[str, Dict[str, List[Dict]]],
    topn_sections: Dict[str, Dict[str, List[Dict]]],
    build_time_ms: int,
) -> Dict:
    """
    生成元数据

    Args:
        sections: 完整分区字典
        topn_sections: TopN 分区字典
        build_time_ms: 构建耗时（毫秒）

    Returns:
        元数据字典
    """
    # 统计总数
    total_items = sum(
        len(items)
        for layers in sections.values()
        for items in layers.values()
    )

    topn_items = sum(
        len(items)
        for layers in topn_sections.values()
        for items in layers.values()
    )

    # 分区统计
    sections_count = {}
    for region, layers in sections.items():
        sections_count[region] = {}
        for layer, items in layers.items():
            sections_count[region][layer] = len(items)

    metadata = {
        "total_items": total_items,
        "topn_items": topn_items,
        "sections_count": sections_count,
        "build_time_ms": build_time_ms,
        "generated_at": get_local_now().isoformat(),
    }

    return metadata


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """
    格式化日期时间

    Args:
        dt: datetime 对象
        fmt: 格式字符串

    Returns:
        格式化后的字符串
    """
    if dt is None:
        return ""

    return to_local(dt).strftime(fmt)


# 注册 Jinja2 过滤器
def register_filters(env: Environment):
    """注册自定义 Jinja2 过滤器"""
    env.filters["format_datetime"] = format_datetime
