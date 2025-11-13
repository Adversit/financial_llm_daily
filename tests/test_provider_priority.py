"""
测试 Provider 优先级顺序
"""

from src.nlp.provider_router import ProviderRouter


def test_provider_priority_order():
    """测试 Provider 的加载顺序是否正确"""
    router = ProviderRouter()

    # 验证至少加载了一个provider
    assert len(router.providers) > 0, "至少应该加载一个 Provider"

    # 验证优先级顺序(如果所有provider都成功加载)
    if len(router.providers) == 3:
        # 优先级1: qwen-plus
        assert router.providers[0].name == "qwen", "第一优先级应该是 Qwen"
        assert router.providers[0].model == "qwen-plus", "第一优先级应该使用 qwen-plus 模型"

        # 优先级2: deepseek
        assert router.providers[1].name == "deepseek", "第二优先级应该是 DeepSeek"
        assert router.providers[1].model == "deepseek-chat", "第二优先级应该使用 deepseek-chat 模型"

        # 优先级3: qwen-max
        assert router.providers[2].name == "qwen", "第三优先级应该是 Qwen"
        assert router.providers[2].model == "qwen-max", "第三优先级应该使用 qwen-max 模型"

        print("✅ Provider优先级顺序正确: qwen-plus → deepseek → qwen-max")
    else:
        print(f"⚠️ 部分Provider加载失败,当前可用: {[f'{p.name}/{p.model}' for p in router.providers]}")


def test_provider_cost_comparison():
    """对比不同provider的成本"""
    from src.utils.cost_calculator import calculate_cost

    # 标准测试: 10k输入 + 5k输出
    input_tokens = 10000
    output_tokens = 5000

    qwen_plus_cost = calculate_cost("qwen", "qwen-plus", input_tokens, output_tokens)
    deepseek_cost = calculate_cost("deepseek", "deepseek-chat", input_tokens, output_tokens)
    qwen_max_cost = calculate_cost("qwen", "qwen-max", input_tokens, output_tokens)

    print(f"\n成本对比 (10k输入 + 5k输出):")
    print(f"  Qwen-plus:  ¥{qwen_plus_cost:.4f}")
    print(f"  DeepSeek:   ¥{deepseek_cost:.4f}")
    print(f"  Qwen-max:   ¥{qwen_max_cost:.4f}")

    # 验证成本顺序
    assert qwen_plus_cost < deepseek_cost, "Qwen-plus应该比DeepSeek便宜"
    assert deepseek_cost < qwen_max_cost, "DeepSeek应该比Qwen-max便宜"

    # 计算节省百分比
    savings = ((deepseek_cost - qwen_plus_cost) / deepseek_cost) * 100
    print(f"\n💰 使用Qwen-plus替代DeepSeek可节省: {savings:.1f}%")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
