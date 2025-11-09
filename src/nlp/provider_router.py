"""
LLM Provider 路由器模块

支持多个 LLM Provider 的统一接口和自动回退机制。
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

import httpx
from loguru import logger
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import settings


class LLMProvider(ABC):
    """LLM Provider 抽象基类"""

    def __init__(self, name: str, api_key: str, base_url: str, model: str):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=settings.LLM_TIMEOUT_SEC,
        )

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict],
        temperature: float = 0.3,
        timeout: Optional[int] = None,
    ) -> Dict:
        """
        执行聊天补全

        Args:
            messages: 消息列表
            temperature: 温度参数
            timeout: 超时时间（秒）

        Returns:
            标准化响应字典
        """
        pass


class DeepSeekProvider(LLMProvider):
    """DeepSeek Provider"""

    def __init__(self):
        super().__init__(
            name="deepseek",
            api_key=settings.PROVIDER_DEEPSEEK_API_KEY,
            base_url=settings.PROVIDER_DEEPSEEK_BASE_URL,
            model=settings.PROVIDER_DEEPSEEK_MODEL,
        )

    async def chat_completion(
        self,
        messages: List[Dict],
        temperature: float = 0.3,
        timeout: Optional[int] = None,
    ) -> Dict:
        """执行 DeepSeek 聊天补全"""
        try:
            timeout = timeout or settings.LLM_TIMEOUT_SEC

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                timeout=timeout,
            )

            # 标准化返回格式
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "finish_reason": response.choices[0].finish_reason,
            }

        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            raise


class QwenProvider(LLMProvider):
    """Qwen (通义千问) Provider"""

    def __init__(self):
        super().__init__(
            name="qwen",
            api_key=settings.PROVIDER_QWEN_API_KEY,
            base_url=settings.PROVIDER_QWEN_BASE_URL,
            model=settings.PROVIDER_QWEN_MODEL,
        )

    async def chat_completion(
        self,
        messages: List[Dict],
        temperature: float = 0.3,
        timeout: Optional[int] = None,
    ) -> Dict:
        """执行 Qwen 聊天补全"""
        try:
            timeout = timeout or settings.LLM_TIMEOUT_SEC

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                timeout=timeout,
            )

            # 标准化返回格式
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "finish_reason": response.choices[0].finish_reason,
            }

        except Exception as e:
            logger.error(f"Qwen API 调用失败: {e}")
            raise


class ProviderRouter:
    """Provider 路由器，支持自动回退"""

    def __init__(self):
        """初始化所有可用的 Provider"""
        self.providers: List[LLMProvider] = []

        # 按优先级顺序初始化 Provider
        try:
            self.providers.append(DeepSeekProvider())
            logger.info("✅ DeepSeek Provider 已加载")
        except Exception as e:
            logger.warning(f"⚠️ DeepSeek Provider 加载失败: {e}")

        try:
            self.providers.append(QwenProvider())
            logger.info("✅ Qwen Provider 已加载")
        except Exception as e:
            logger.warning(f"⚠️ Qwen Provider 加载失败: {e}")

        if not self.providers:
            raise RuntimeError("没有可用的 LLM Provider")

        logger.info(f"Provider 路由器初始化完成，可用 Provider: {[p.name for p in self.providers]}")

    async def call_with_fallback(
        self,
        messages: List[Dict],
        temperature: float = 0.3,
        retries: int = 2,
        timeout: Optional[int] = None,
    ) -> Tuple[Dict, str]:
        """
        调用 LLM，支持自动回退

        Args:
            messages: 消息列表
            temperature: 温度参数
            retries: 每个 Provider 的重试次数
            timeout: 超时时间（秒）

        Returns:
            (响应字典, provider_name)

        Raises:
            RuntimeError: 所有 Provider 都失败时抛出
        """
        last_error = None

        for provider in self.providers:
            try:
                logger.info(f"尝试使用 Provider: {provider.name}")

                # 使用 tenacity 进行重试
                @retry(
                    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPError)),
                    stop=stop_after_attempt(retries + 1),
                    wait=wait_exponential(multiplier=1, min=2, max=10),
                    reraise=True,
                )
                async def _call_with_retry():
                    return await provider.chat_completion(
                        messages=messages,
                        temperature=temperature,
                        timeout=timeout,
                    )

                response = await _call_with_retry()
                logger.success(f"✅ {provider.name} 调用成功")
                return response, provider.name

            except Exception as e:
                last_error = e
                logger.warning(
                    f"⚠️ Provider {provider.name} 失败 (已重试 {retries} 次): {e}"
                )
                # 继续尝试下一个 Provider
                continue

        # 所有 Provider 都失败
        error_msg = f"所有 Provider 均失败，最后错误: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


class ConcurrencyController:
    """并发控制器"""

    def __init__(self, max_inflight: int = 2):
        """
        初始化并发控制器

        Args:
            max_inflight: 最大并发数
        """
        self.semaphore = asyncio.Semaphore(max_inflight)
        self.max_inflight = max_inflight
        logger.info(f"并发控制器初始化，最大并发数: {max_inflight}")

    async def call(
        self,
        provider_router: ProviderRouter,
        messages: List[Dict],
        temperature: float = 0.3,
        timeout: Optional[int] = None,
    ) -> Tuple[Dict, str]:
        """
        在并发控制下调用 Provider

        Args:
            provider_router: Provider 路由器
            messages: 消息列表
            temperature: 温度参数
            timeout: 超时时间

        Returns:
            (响应字典, provider_name)
        """
        async with self.semaphore:
            return await provider_router.call_with_fallback(
                messages=messages,
                temperature=temperature,
                timeout=timeout,
            )


# 全局单例
_provider_router: Optional[ProviderRouter] = None
_concurrency_controller: Optional[ConcurrencyController] = None


def get_provider_router() -> ProviderRouter:
    """获取全局 Provider 路由器单例"""
    global _provider_router
    if _provider_router is None:
        _provider_router = ProviderRouter()
    return _provider_router


def get_concurrency_controller() -> ConcurrencyController:
    """获取全局并发控制器单例"""
    global _concurrency_controller
    if _concurrency_controller is None:
        max_inflight = 2 if settings.LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING else 1
        _concurrency_controller = ConcurrencyController(max_inflight=max_inflight)
    return _concurrency_controller
