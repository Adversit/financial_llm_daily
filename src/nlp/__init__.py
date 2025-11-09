# -*- coding: utf-8 -*-
"""
NLP module - LLM extraction and processing
"""

from .chunking import (
    ChunkPlan,
    detect_language,
    estimate_tokens,
    pack_sentences_into_chunks,
    plan_chunks,
    split_by_semantics,
)
from .extractor import EXTRACTION_PROMPT, ExtractResult, extract_article, extract_from_chunk
from .merger import (
    deduplicate_facts,
    filter_low_quality_items,
    merge_extraction_results,
    normalize_fact,
    resolve_conflicts,
)
from .provider_router import (
    ConcurrencyController,
    DeepSeekProvider,
    LLMProvider,
    ProviderRouter,
    QwenProvider,
    get_concurrency_controller,
    get_provider_router,
)

__all__ = [
    # chunking
    "ChunkPlan",
    "detect_language",
    "estimate_tokens",
    "pack_sentences_into_chunks",
    "plan_chunks",
    "split_by_semantics",
    # extractor
    "EXTRACTION_PROMPT",
    "ExtractResult",
    "extract_article",
    "extract_from_chunk",
    # merger
    "deduplicate_facts",
    "filter_low_quality_items",
    "merge_extraction_results",
    "normalize_fact",
    "resolve_conflicts",
    # provider_router
    "ConcurrencyController",
    "DeepSeekProvider",
    "LLMProvider",
    "ProviderRouter",
    "QwenProvider",
    "get_concurrency_controller",
    "get_provider_router",
]
