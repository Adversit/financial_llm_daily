#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接测试LLM API连接

测试不同的httpx配置,找到正确禁用代理的方法
"""
import os
import asyncio
import httpx
from openai import AsyncOpenAI

# 显示当前环境变量
print("=" * 80)
print("当前环境变量:")
print(f"http_proxy: {os.environ.get('http_proxy', '未设置')}")
print(f"https_proxy: {os.environ.get('https_proxy', '未设置')}")
print(f"all_proxy: {os.environ.get('all_proxy', '未设置')}")
print(f"no_proxy: {os.environ.get('no_proxy', '未设置')}")
print("=" * 80)
print()

# Qwen API配置
QWEN_API_KEY = "sk-928962503a5943b99f428cec8f89b420"
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


async def test_method_1():
    """方法1: proxies=None"""
    print("【测试1】使用 proxies=None")
    try:
        client = AsyncOpenAI(
            api_key=QWEN_API_KEY,
            base_url=QWEN_BASE_URL,
            timeout=30,
            http_client=httpx.AsyncClient(
                proxies=None,
                timeout=30,
            ),
        )

        response = await client.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.3,
        )

        print(f"✅ 成功! 回复: {response.choices[0].message.content}")
        await client.close()
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


async def test_method_2():
    """方法2: proxies={}"""
    print("\n【测试2】使用 proxies={}")
    try:
        client = AsyncOpenAI(
            api_key=QWEN_API_KEY,
            base_url=QWEN_BASE_URL,
            timeout=30,
            http_client=httpx.AsyncClient(
                proxies={},
                timeout=30,
            ),
        )

        response = await client.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.3,
        )

        print(f"✅ 成功! 回复: {response.choices[0].message.content}")
        await client.close()
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


async def test_method_3():
    """方法3: trust_env=False"""
    print("\n【测试3】使用 trust_env=False")
    try:
        client = AsyncOpenAI(
            api_key=QWEN_API_KEY,
            base_url=QWEN_BASE_URL,
            timeout=30,
            http_client=httpx.AsyncClient(
                trust_env=False,
                timeout=30,
            ),
        )

        response = await client.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.3,
        )

        print(f"✅ 成功! 回复: {response.choices[0].message.content}")
        await client.close()
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


async def test_method_4():
    """方法4: proxies={} + trust_env=False"""
    print("\n【测试4】使用 proxies={} + trust_env=False")
    try:
        client = AsyncOpenAI(
            api_key=QWEN_API_KEY,
            base_url=QWEN_BASE_URL,
            timeout=30,
            http_client=httpx.AsyncClient(
                proxies={},
                trust_env=False,
                timeout=30,
            ),
        )

        response = await client.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.3,
        )

        print(f"✅ 成功! 回复: {response.choices[0].message.content}")
        await client.close()
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


async def test_method_5():
    """方法5: 默认配置(不传http_client)"""
    print("\n【测试5】默认配置(继承环境变量)")
    try:
        client = AsyncOpenAI(
            api_key=QWEN_API_KEY,
            base_url=QWEN_BASE_URL,
            timeout=30,
        )

        response = await client.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.3,
        )

        print(f"✅ 成功! 回复: {response.choices[0].message.content}")
        await client.close()
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


async def main():
    print("\n开始测试LLM API连接...\n")

    results = []

    # 测试所有方法
    results.append(("方法1: proxies=None", await test_method_1()))
    results.append(("方法2: proxies={}", await test_method_2()))
    results.append(("方法3: trust_env=False", await test_method_3()))
    results.append(("方法4: proxies={} + trust_env=False", await test_method_4()))
    results.append(("方法5: 默认配置", await test_method_5()))

    # 总结
    print("\n" + "=" * 80)
    print("测试结果汇总:")
    print("=" * 80)
    for method, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{method}: {status}")

    # 推荐方案
    print("\n" + "=" * 80)
    successful_methods = [method for method, success in results if success]
    if successful_methods:
        print(f"推荐使用: {successful_methods[0]}")
    else:
        print("⚠️  所有方法都失败了,可能是:")
        print("  1. API Key 不正确")
        print("  2. 网络连接问题")
        print("  3. 代理配置问题")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
