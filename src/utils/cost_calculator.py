"""
LLM 成本计算工具模块

根据 API 返回的 token 使用量和配置的定价计算实际成本
"""

from loguru import logger

from src.config.settings import settings


def calculate_cost(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """
    根据 provider、model 和 token 使用量计算成本

    Args:
        provider: Provider 名称 (如: deepseek, qwen)
        model: 模型名称 (如: deepseek-chat, qwen-max)
        prompt_tokens: 输入 token 数量
        completion_tokens: 输出 token 数量

    Returns:
        float: 成本(人民币元),保留 6 位小数

    Examples:
        >>> calculate_cost("deepseek", "deepseek-chat", 1000, 500)
        0.002  # (1000/1000000)*1.0 + (500/1000000)*2.0

        >>> calculate_cost("qwen", "qwen-max", 2000, 1000)
        0.0036  # (2000/1000000)*0.8 + (1000/1000000)*2.0
    """
    # 标准化 provider 名称
    provider = provider.lower()

    # 尝试获取精确的模型定价
    pricing_key = f"{provider}:{model}"
    pricing = settings.LLM_PRICING.get(pricing_key)

    # 如果没有精确模型定价,使用该 provider 的默认定价
    if not pricing:
        default_key = f"{provider}:default"
        pricing = settings.LLM_PRICING.get(default_key)

        if pricing:
            logger.debug(
                f"模型 {model} 未配置定价,使用 {provider} 默认定价: "
                f"输入={pricing['input']}/M, 输出={pricing['output']}/M"
            )
        else:
            # 如果连默认定价都没有,使用通用默认值
            logger.warning(
                f"Provider {provider} 未配置定价,使用通用默认定价: "
                f"输入=1.0/M, 输出=2.0/M"
            )
            pricing = {"input": 1.0, "output": 2.0}

    # 计算成本 (定价单位: 元/百万tokens)
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost

    logger.debug(
        f"成本计算: {provider}/{model}, "
        f"输入={prompt_tokens}tokens(¥{input_cost:.6f}), "
        f"输出={completion_tokens}tokens(¥{output_cost:.6f}), "
        f"总计=¥{total_cost:.6f}"
    )

    return round(total_cost, 6)


def get_pricing_info(provider: str, model: str) -> dict:
    """
    获取指定 provider 和 model 的定价信息

    Args:
        provider: Provider 名称
        model: 模型名称

    Returns:
        dict: 定价信息 {"input": float, "output": float, "source": str}
              source 可能是 "exact"(精确匹配), "default"(默认), "fallback"(通用)
    """
    provider = provider.lower()

    # 尝试精确匹配
    pricing_key = f"{provider}:{model}"
    pricing = settings.LLM_PRICING.get(pricing_key)
    if pricing:
        return {
            "input": pricing["input"],
            "output": pricing["output"],
            "source": "exact",
        }

    # 尝试 provider 默认值
    default_key = f"{provider}:default"
    pricing = settings.LLM_PRICING.get(default_key)
    if pricing:
        return {
            "input": pricing["input"],
            "output": pricing["output"],
            "source": "default",
        }

    # 使用通用默认值
    return {
        "input": 1.0,
        "output": 2.0,
        "source": "fallback",
    }


def estimate_cost(
    provider: str,
    model: str,
    estimated_tokens: int,
    input_output_ratio: float = 0.7,
) -> float:
    """
    估算成本(用于预算规划)

    Args:
        provider: Provider 名称
        model: 模型名称
        estimated_tokens: 预估的总 token 数
        input_output_ratio: 输入 token 占比(默认 0.7,即 70% 输入 + 30% 输出)

    Returns:
        float: 估算成本(人民币元)
    """
    prompt_tokens = int(estimated_tokens * input_output_ratio)
    completion_tokens = int(estimated_tokens * (1 - input_output_ratio))

    return calculate_cost(provider, model, prompt_tokens, completion_tokens)
