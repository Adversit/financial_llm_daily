"""
测试 LLM Provider 配置和连接

用于验证 DeepSeek 和 Qwen API 配置是否正确
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from openai import AsyncOpenAI

from src.config.settings import settings


async def test_deepseek_api():
    """测试 DeepSeek API 连接"""
    logger.info("=" * 60)
    logger.info("开始测试 DeepSeek API")
    logger.info("=" * 60)

    logger.info(f"Base URL: {settings.PROVIDER_DEEPSEEK_BASE_URL}")
    logger.info(f"Model: {settings.PROVIDER_DEEPSEEK_MODEL}")
    logger.info(f"API Key: {settings.PROVIDER_DEEPSEEK_API_KEY[:20]}...")

    try:
        client = AsyncOpenAI(
            api_key=settings.PROVIDER_DEEPSEEK_API_KEY,
            base_url=settings.PROVIDER_DEEPSEEK_BASE_URL,
            timeout=30.0,
        )

        logger.info("正在调用 DeepSeek API...")

        response = await client.chat.completions.create(
            model=settings.PROVIDER_DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是一个测试助手"},
                {"role": "user", "content": "请用一句话介绍你自己"}
            ],
            temperature=0.3,
        )

        content = response.choices[0].message.content
        model = response.model
        usage = response.usage

        logger.success("✅ DeepSeek API 测试成功!")
        logger.info(f"模型: {model}")
        logger.info(f"响应内容: {content}")
        logger.info(f"Token 使用: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")

        return True

    except Exception as e:
        logger.error(f"❌ DeepSeek API 测试失败: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        return False


async def test_qwen_api():
    """测试 Qwen API 连接"""
    logger.info("=" * 60)
    logger.info("开始测试 Qwen API")
    logger.info("=" * 60)

    logger.info(f"Base URL: {settings.PROVIDER_QWEN_BASE_URL}")
    logger.info(f"Model: {settings.PROVIDER_QWEN_MODEL}")
    logger.info(f"API Key: {settings.PROVIDER_QWEN_API_KEY[:20]}...")

    try:
        client = AsyncOpenAI(
            api_key=settings.PROVIDER_QWEN_API_KEY,
            base_url=settings.PROVIDER_QWEN_BASE_URL,
            timeout=30.0,
        )

        logger.info("正在调用 Qwen API...")

        response = await client.chat.completions.create(
            model=settings.PROVIDER_QWEN_MODEL,
            messages=[
                {"role": "system", "content": "你是一个测试助手"},
                {"role": "user", "content": "请用一句话介绍你自己"}
            ],
            temperature=0.3,
        )

        content = response.choices[0].message.content
        model = response.model
        usage = response.usage

        logger.success("✅ Qwen API 测试成功!")
        logger.info(f"模型: {model}")
        logger.info(f"响应内容: {content}")
        logger.info(f"Token 使用: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")

        return True

    except Exception as e:
        logger.error(f"❌ Qwen API 测试失败: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        return False


async def main():
    """主测试函数"""
    logger.info("🚀 开始测试 LLM Provider 配置")
    logger.info("")

    # 测试 DeepSeek
    deepseek_ok = await test_deepseek_api()
    logger.info("")

    # 测试 Qwen
    qwen_ok = await test_qwen_api()
    logger.info("")

    # 总结
    logger.info("=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    logger.info(f"DeepSeek: {'✅ 通过' if deepseek_ok else '❌ 失败'}")
    logger.info(f"Qwen:     {'✅ 通过' if qwen_ok else '❌ 失败'}")
    logger.info("")

    if deepseek_ok and qwen_ok:
        logger.success("🎉 所有 Provider 测试通过！")
        return 0
    elif deepseek_ok or qwen_ok:
        logger.warning("⚠️ 部分 Provider 测试失败，但至少有一个可用")
        return 1
    else:
        logger.error("❌ 所有 Provider 测试失败，请检查配置")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
