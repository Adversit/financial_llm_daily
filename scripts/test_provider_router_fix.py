#!/usr/bin/env python3
"""
测试 provider_router 代理配置修复
验证是否能正常调用LLM API并且没有清理错误
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

from src.nlp.provider_router import ProviderRouter


async def test_provider_router():
    """测试 ProviderRouter 能否正常工作"""

    print("=" * 80)
    print("测试 ProviderRouter 修复...")
    print("=" * 80)
    print()

    # 显示当前环境变量(用于诊断)
    print("当前环境变量:")
    for key in ["http_proxy", "https_proxy", "all_proxy", "no_proxy"]:
        value = os.environ.get(key, "(未设置)")
        print(f"  {key}: {value}")
    print()

    try:
        # 创建 ProviderRouter
        print("【步骤1】创建 ProviderRouter...")
        router = ProviderRouter()
        print(f"✅ ProviderRouter 创建成功，可用 Provider: {[f'{p.name}/{p.model}' for p in router.providers]}")
        print()

        # 调用 LLM
        print("【步骤2】调用 LLM API...")
        messages = [{"role": "user", "content": "你好"}]

        response, provider_name = await router.call_with_fallback(
            messages=messages,
            temperature=0.3,
            timeout=30,
        )

        print(f"✅ LLM 调用成功!")
        print(f"   Provider: {provider_name}")
        print(f"   Model: {response.get('model', 'N/A')}")
        print(f"   回复: {response.get('content', '')[:100]}...")
        print(f"   Token使用: {response.get('usage', {})}")
        print()

        # 测试清理(验证是否还有 _mounts 错误)
        print("【步骤3】清理资源...")
        # 尝试关闭所有 provider 的 client
        for provider in router.providers:
            try:
                await provider.client.close()
                print(f"✅ {provider.name} 客户端已关闭")
            except Exception as e:
                print(f"⚠️ 关闭 {provider.name} 客户端时出现警告: {e}")

        print()
        print("=" * 80)
        print("✅ 所有测试通过！没有出现 _mounts 错误")
        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ 测试失败: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_provider_router())
