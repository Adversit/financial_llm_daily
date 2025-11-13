"""
测试 LLM 成本计算工具
"""

import pytest

from src.utils.cost_calculator import (
    calculate_cost,
    estimate_cost,
    get_pricing_info,
)


class TestCalculateCost:
    """测试成本计算函数"""

    def test_deepseek_chat_cost(self):
        """测试 DeepSeek-chat 模型的成本计算 (2025年最新定价)"""
        # 输入 1000 tokens, 输出 500 tokens
        # 成本 = (1000/1000000)*2.0 + (500/1000000)*3.0 = 0.002 + 0.0015 = 0.0035
        cost = calculate_cost("deepseek", "deepseek-chat", 1000, 500)
        assert cost == 0.0035

    def test_deepseek_reasoner_cost(self):
        """测试 DeepSeek-reasoner 模型的成本计算 (2025年最新定价)"""
        # 输入 1000 tokens, 输出 500 tokens
        # 成本 = (1000/1000000)*2.0 + (500/1000000)*3.0 = 0.002 + 0.0015 = 0.0035
        cost = calculate_cost("deepseek", "deepseek-reasoner", 1000, 500)
        assert cost == 0.0035

    def test_qwen_max_cost(self):
        """测试 Qwen-max 模型的成本计算 (2025年最新定价)"""
        # 输入 2000 tokens, 输出 1000 tokens
        # 成本 = (2000/1000000)*6.0 + (1000/1000000)*24.0 = 0.012 + 0.024 = 0.036
        cost = calculate_cost("qwen", "qwen-max", 2000, 1000)
        assert cost == 0.036

    def test_qwen_plus_cost(self):
        """测试 Qwen-plus 模型的成本计算 (2025年最新定价)"""
        # 输入 2000 tokens, 输出 1000 tokens
        # 成本 = (2000/1000000)*0.8 + (1000/1000000)*2.0 = 0.0016 + 0.002 = 0.0036
        cost = calculate_cost("qwen", "qwen-plus", 2000, 1000)
        assert cost == 0.0036

    def test_qwen_turbo_cost(self):
        """测试 Qwen-turbo 模型的成本计算"""
        # 输入 2000 tokens, 输出 1000 tokens
        # 成本 = (2000/1000000)*0.3 + (1000/1000000)*0.6 = 0.0006 + 0.0006 = 0.0012
        cost = calculate_cost("qwen", "qwen-turbo", 2000, 1000)
        assert cost == 0.0012

    def test_unknown_model_uses_default_pricing(self):
        """测试未知模型使用 provider 默认定价"""
        # 未知 DeepSeek 模型应使用 deepseek:default 定价 (2.0, 3.0)
        cost = calculate_cost("deepseek", "deepseek-unknown", 1000, 500)
        expected = (1000 / 1_000_000) * 2.0 + (500 / 1_000_000) * 3.0
        assert cost == expected

    def test_unknown_provider_uses_fallback_pricing(self):
        """测试未知 provider 使用通用默认定价 (1.0, 2.0)"""
        # 未知 provider 应使用通用默认定价
        cost = calculate_cost("unknown", "unknown-model", 1000, 500)
        expected = (1000 / 1_000_000) * 1.0 + (500 / 1_000_000) * 2.0
        assert cost == expected

    def test_case_insensitive(self):
        """测试 provider 名称不区分大小写"""
        cost1 = calculate_cost("DeepSeek", "deepseek-chat", 1000, 500)
        cost2 = calculate_cost("deepseek", "deepseek-chat", 1000, 500)
        assert cost1 == cost2

    def test_zero_tokens(self):
        """测试零 token 的情况"""
        cost = calculate_cost("deepseek", "deepseek-chat", 0, 0)
        assert cost == 0.0

    def test_large_token_count(self):
        """测试大量 token 的成本计算"""
        # 100万输入 + 50万输出
        cost = calculate_cost("deepseek", "deepseek-chat", 1_000_000, 500_000)
        # 成本 = 2.0 + 1.5 = 3.5
        assert cost == 3.5


class TestGetPricingInfo:
    """测试获取定价信息函数"""

    def test_exact_match(self):
        """测试精确匹配模型定价"""
        info = get_pricing_info("deepseek", "deepseek-chat")
        assert info["input"] == 2.0
        assert info["output"] == 3.0
        assert info["source"] == "exact"

    def test_default_match(self):
        """测试使用默认定价"""
        info = get_pricing_info("deepseek", "unknown-model")
        assert info["input"] == 2.0
        assert info["output"] == 3.0
        assert info["source"] == "default"

    def test_fallback_match(self):
        """测试使用通用默认定价"""
        info = get_pricing_info("unknown", "unknown-model")
        assert info["input"] == 1.0
        assert info["output"] == 2.0
        assert info["source"] == "fallback"


class TestEstimateCost:
    """测试成本估算函数"""

    def test_estimate_cost_default_ratio(self):
        """测试使用默认输入输出比例估算成本"""
        # 10000 tokens 总量, 默认 70% 输入 + 30% 输出
        # 输入: 7000, 输出: 3000
        # DeepSeek-chat 成本: (7000/1000000)*2.0 + (3000/1000000)*3.0 = 0.014 + 0.009 = 0.023
        cost = estimate_cost("deepseek", "deepseek-chat", 10000)
        assert cost == 0.023

    def test_estimate_cost_custom_ratio(self):
        """测试使用自定义输入输出比例估算成本"""
        # 10000 tokens 总量, 50% 输入 + 50% 输出
        # 输入: 5000, 输出: 5000
        # DeepSeek-chat 成本: (5000/1000000)*2.0 + (5000/1000000)*3.0 = 0.01 + 0.015 = 0.025
        cost = estimate_cost("deepseek", "deepseek-chat", 10000, input_output_ratio=0.5)
        assert cost == 0.025

    def test_estimate_cost_qwen(self):
        """测试 Qwen 模型的成本估算 (2025年最新定价)"""
        # 20000 tokens 总量, 默认 70% 输入 + 30% 输出
        # 输入: 14000, 输出: 6000
        # Qwen-max 成本: (14000/1000000)*6.0 + (6000/1000000)*24.0 = 0.084 + 0.144 = 0.228
        cost = estimate_cost("qwen", "qwen-max", 20000)
        assert cost == 0.228


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
