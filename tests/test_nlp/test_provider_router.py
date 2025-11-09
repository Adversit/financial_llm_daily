"""
LLM Provider 路由器测试
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

import src.nlp.provider_router as router_module
from src.nlp.provider_router import (
    ConcurrencyController,
    DeepSeekProvider,
    ProviderRouter,
    QwenProvider,
)


@pytest.fixture(autouse=True)
def patch_async_openai(monkeypatch):
    """避免真实初始化 AsyncOpenAI 客户端"""

    class DummyOpenAIClient:
        def __init__(self, *args, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=AsyncMock())
            )

    monkeypatch.setattr(
        router_module,
        "AsyncOpenAI",
        lambda *args, **kwargs: DummyOpenAIClient(),
    )

    # 重置全局单例，避免测试之间互相影响
    monkeypatch.setattr(router_module, "_provider_router", None)
    monkeypatch.setattr(router_module, "_concurrency_controller", None)


def _success_response():
    return {
        "content": "ok",
        "model": "stub-model",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
        "finish_reason": "stop",
    }


@pytest.mark.asyncio
async def test_call_with_primary_provider(monkeypatch):
    async def deepseek_chat(self, *args, **kwargs):
        return _success_response()

    monkeypatch.setattr(DeepSeekProvider, "chat_completion", deepseek_chat)
    monkeypatch.setattr(QwenProvider, "chat_completion", AsyncMock())

    router = ProviderRouter()
    response, provider = await router.call_with_fallback(
        messages=[{"role": "user", "content": "hi"}],
        retries=0,
    )

    assert response["content"] == "ok"
    assert provider == "deepseek"


@pytest.mark.asyncio
async def test_call_with_fallback(monkeypatch):
    async def deepseek_fail(self, *args, **kwargs):
        raise httpx.TimeoutException("timeout")

    async def qwen_success(self, *args, **kwargs):
        return _success_response()

    monkeypatch.setattr(DeepSeekProvider, "chat_completion", deepseek_fail)
    monkeypatch.setattr(QwenProvider, "chat_completion", qwen_success)

    router = ProviderRouter()
    response, provider = await router.call_with_fallback(
        messages=[{"role": "user", "content": "hi"}],
        retries=0,
    )

    assert provider == "qwen"
    assert response["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_call_with_fallback_all_fail(monkeypatch):
    async def fail(self, *args, **kwargs):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(DeepSeekProvider, "chat_completion", fail)
    monkeypatch.setattr(QwenProvider, "chat_completion", fail)

    router = ProviderRouter()

    with pytest.raises(RuntimeError):
        await router.call_with_fallback(
            messages=[{"role": "user", "content": "hi"}],
            retries=0,
        )


@pytest.mark.asyncio
async def test_concurrency_controller_limits_parallel_calls():
    controller = ConcurrencyController(max_inflight=1)
    active = 0
    max_active = 0

    class DummyRouter:
        async def call_with_fallback(self, *args, **kwargs):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1
            return _success_response(), "deepseek"

    dummy_router = DummyRouter()

    await asyncio.gather(
        controller.call(dummy_router, messages=[]),
        controller.call(dummy_router, messages=[]),
    )

    assert max_active == 1
