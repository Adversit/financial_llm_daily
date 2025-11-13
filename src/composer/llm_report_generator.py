"""
LLM 报告生成器模块

使用 LLM 生成总览报告和分区报告。
"""

import json
from typing import Dict, List

from loguru import logger

from src.config.settings import settings
from src.nlp.chunking import estimate_tokens, detect_language
from src.nlp.provider_router import get_provider_router


# 分区报告 Prompt 模板
SECTION_REPORT_PROMPT = """你是一名专业的金融情报分析师。根据以下【{region}-{layer}】领域今日采集的金融情报，生成一份专业的分析报告。

**核心要求：必须从金融行业视角分析**

**分析要求**：
1. **金融视角核心**：必须从金融行业视角分析，重点关注对金融市场、金融机构、金融政策的影响
2. **综合分析**：整合所有事实和观点，提炼核心趋势和关键事件
3. **影响评估**：分析对相关金融板块、机构、政策的短期和中期影响
4. **优先级排序**：优先分析高金融相关性、高置信度、高评分的情报
5. **专业表达**：语言简洁专业，字数控制在 150-250 字
6. **避免罗列**：要有深度分析和趋势判断

**特殊层级要求**：
{layer_instruction}

**【{region}-{layer}】领域情报（共 {count} 条，按评分排序）**：

{items_text}

---

请从金融行业视角输出该领域的分析报告（150-250字，不要前缀和总结性语句）：
"""

# 层级特殊指令
LAYER_INSTRUCTIONS = {
    "金融政策监管": "重点分析政策对金融机构、资本市场的直接影响，以及监管趋势变化",
    "金融经济": "关注市场表现、资金流向、机构动态，分析市场趋势和投资机会",
    "金融大模型技术": "关注技术商业化进展、融资动态、对金融行业的潜在影响",
    "金融科技应用": "分析具体应用场景、市场机会、竞争格局和商业价值",
    "未知": "综合分析该领域情报的金融影响和趋势"
}


def format_items_for_llm(items: List[Dict], max_items: int = None) -> str:
    """
    格式化事实观点为 LLM 输入文本

    Args:
        items: 事实观点列表
        max_items: 最多包含的条目数

    Returns:
        格式化的文本
    """
    if max_items:
        items = items[:max_items]

    lines = []
    for i, item in enumerate(items, 1):
        region = item.get("region", "未知")
        layer = item.get("layer", "未知")
        fact = item.get("fact", "")
        opinion = item.get("opinion", "")
        confidence = item.get("confidence", 0.0)
        score = item.get("score", 0.0)

        # 格式化单条
        item_text = f"{i}. 【{region}-{layer}】(评分: {score:.2f}, 置信度: {confidence:.2f})\n"
        item_text += f"   事实: {fact}\n"
        if opinion:
            item_text += f"   观点: {opinion}\n"

        lines.append(item_text)

    return "\n".join(lines)


def chunk_items_by_tokens(
    items: List[Dict],
    max_tokens: int,
    budget: float = 0.6
) -> List[List[Dict]]:
    """
    按 token 数量分块事实观点

    Args:
        items: 事实观点列表
        max_tokens: 最大 token 数
        budget: 可用预算比例

    Returns:
        分块后的列表
    """
    if not items:
        return []

    target_tokens = int(max_tokens * budget)
    chunks = []
    current_chunk = []
    current_tokens = 0

    for item in items:
        # 估算当前条目的 token 数
        item_text = format_items_for_llm([item])
        item_tokens = estimate_tokens(item_text, "mixed")

        # 如果单条就超过目标，单独成块
        if item_tokens > target_tokens:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0
            chunks.append([item])
            logger.warning(
                f"单条事实观点超过 token 限制: {item_tokens} > {target_tokens}"
            )
            continue

        # 如果加入当前条目会超过目标
        if current_tokens + item_tokens > target_tokens:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = [item]
            current_tokens = item_tokens
        else:
            current_chunk.append(item)
            current_tokens += item_tokens

    # 保存最后一块
    if current_chunk:
        chunks.append(current_chunk)

    logger.info(
        f"事实观点分块完成: {len(items)} 条 -> {len(chunks)} 块"
    )

    return chunks


async def generate_section_report_with_llm(
    region: str,
    layer: str,
    items: List[Dict]
) -> str:
    """
    使用 LLM 生成分区报告（处理该分区的全部数据）

    Args:
        region: 区域（国内/国外）
        layer: 层级（政治/经济/金融大模型技术/金融科技）
        items: 该分区的所有事实观点列表（已按评分排序）

    Returns:
        生成的分区报告
    """
    if not items:
        return ""

    logger.info(f"开始生成【{region}-{layer}】分区报告，输入 {len(items)} 条事实观点")

    # 获取层级特殊指令
    layer_instruction = LAYER_INSTRUCTIONS.get(layer, LAYER_INSTRUCTIONS["未知"])

    # 检查 token 数，如果超限需要分块处理
    items_text = format_items_for_llm(items)
    prompt = SECTION_REPORT_PROMPT.format(
        region=region,
        layer=layer,
        count=len(items),
        items_text=items_text,
        layer_instruction=layer_instruction
    )

    estimated_tokens = estimate_tokens(prompt, "mixed")
    logger.info(f"【{region}-{layer}】输入 token 估算: {estimated_tokens}")

    # 如果超过限制，需要分块处理
    target_tokens = int(settings.REPORT_LLM_MODEL_LIMIT * settings.REPORT_LLM_BUDGET)

    if estimated_tokens > target_tokens:
        logger.warning(
            f"【{region}-{layer}】输入超过 token 限制 ({estimated_tokens} > {target_tokens})，进行分块处理"
        )
        return await _generate_section_report_with_chunking(region, layer, items)

    # 单次调用
    return await _call_llm_for_report(prompt)


async def _generate_section_report_with_chunking(
    region: str,
    layer: str,
    items: List[Dict]
) -> str:
    """
    分块生成分区报告

    Args:
        region: 区域
        layer: 层级
        items: 所有事实观点

    Returns:
        生成的报告
    """
    # 分块：每块最多 N 条
    chunk_size = settings.REPORT_SECTION_MAX_ITEMS_PER_CHUNK
    chunks = [items[i:i+chunk_size] for i in range(0, len(items), chunk_size)]

    logger.info(f"【{region}-{layer}】分块处理: {len(items)} 条 -> {len(chunks)} 块")

    # 获取层级特殊指令
    layer_instruction = LAYER_INSTRUCTIONS.get(layer, LAYER_INSTRUCTIONS["未知"])

    # 对每块生成子报告
    sub_reports = []
    for i, chunk in enumerate(chunks, 1):
        logger.info(f"【{region}-{layer}】生成子报告 {i}/{len(chunks)}")

        chunk_text = format_items_for_llm(chunk)
        chunk_prompt = SECTION_REPORT_PROMPT.format(
            region=region,
            layer=layer,
            count=len(chunk),
            items_text=chunk_text,
            layer_instruction=layer_instruction
        )

        chunk_report = await _call_llm_for_report(chunk_prompt)
        if chunk_report:
            sub_reports.append(chunk_report)

    # 合并子报告
    if not sub_reports:
        logger.error(f"【{region}-{layer}】所有子报告生成失败")
        return f"{region}{layer}领域今日共监测到 {len(items)} 条情报，请查看详细内容。"

    if len(sub_reports) == 1:
        return sub_reports[0]

    # 多个子报告需要汇总
    logger.info(f"【{region}-{layer}】汇总 {len(sub_reports)} 个子报告")

    merge_prompt = f"""以下是【{region}-{layer}】领域的多个子报告，请汇总为一份完整的分析报告（150-250字）：

{chr(10).join([f'## 子报告 {i+1}:{chr(10)}{report}' for i, report in enumerate(sub_reports)])}

请生成汇总报告（150-250字，保留关键趋势和重要事件）：
"""

    final_report = await _call_llm_for_report(merge_prompt)
    return final_report if final_report else sub_reports[0]


async def _call_llm_for_report(prompt: str) -> str:
    """
    调用 LLM 生成报告

    Args:
        prompt: 提示词

    Returns:
        生成的报告文本
    """
    router = get_provider_router()

    messages = [
        {"role": "system", "content": "你是一名专业的金融情报分析师，擅长撰写简洁专业的情报报告。"},
        {"role": "user", "content": prompt}
    ]

    try:
        response, provider_name = await router.call_with_fallback(
            messages=messages,
            timeout=settings.LLM_TIMEOUT_SEC
        )

        content = response.get("content", "")

        if not content:
            logger.error("LLM 返回内容为空")
            return "今日金融情报报告生成失败,请查看详细内容。"

        # 记录 token 使用情况和成本
        usage = response.get("usage", {})
        model = response.get("model", "unknown")
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        if prompt_tokens > 0 or completion_tokens > 0:
            try:
                from src.db.session import SessionLocal
                from src.utils.cost_calculator import calculate_cost
                from src.models.delivery import ProviderUsage

                cost = calculate_cost(
                    provider=provider_name,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )

                # 记录到数据库
                db = SessionLocal()
                try:
                    usage_record = ProviderUsage(
                        provider_name=provider_name,
                        model_name=model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=prompt_tokens + completion_tokens,
                        cost=cost,
                    )
                    db.add(usage_record)
                    db.commit()
                    logger.debug(
                        f"报告生成成本记录: {provider_name}/{model}, "
                        f"tokens={prompt_tokens + completion_tokens}, cost=¥{cost:.6f}"
                    )
                finally:
                    db.close()

            except Exception as log_error:
                logger.error(f"记录报告生成成本失败: {log_error}")

        logger.success(f"LLM 报告生成成功，长度: {len(content)} 字符")
        return content.strip()

    except Exception as e:
        logger.error(f"LLM 报告生成失败: {e}", exc_info=True)
        return "今日金融情报报告生成失败,请查看详细内容。"
