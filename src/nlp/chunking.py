"""
分块引擎模块

用于对长文本进行智能分块,支持语义切分和降级策略。
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from loguru import logger


@dataclass
class ChunkPlan:
    """分块计划，用于降级策略"""
    strategy: str  # 'summary_then_extract' or 'headN_plus_overall'
    chunks: List[str]
    metadata: dict


def estimate_tokens(text: str, lang_hint: str = "zh") -> int:
    """
    估算文本 Token 数量

    Args:
        text: 输入文本
        lang_hint: 语言提示 ('zh' 中文, 'en' 英文, 'mixed' 混合)

    Returns:
        估算的 token 数量
    """
    if not text:
        return 0

    # 简化估算：中文按字符数1:1，英文按1.3:1，混合按1.2:1
    char_count = len(text)

    if lang_hint == "zh":
        return char_count
    elif lang_hint == "en":
        # 英文按词数估算，平均每词约1.3个token
        word_count = len(text.split())
        return int(word_count * 1.3)
    else:  # mixed
        # 统计中文字符数和英文词数
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_text = re.sub(r'[\u4e00-\u9fff]', '', text)
        english_words = len(other_text.split())
        return chinese_chars + int(english_words * 1.3)


def split_by_semantics(text: str) -> List[str]:
    """
    按语义切分文本（段落级别）

    Args:
        text: 输入文本

    Returns:
        段落列表
    """
    if not text:
        return []

    # 按空行或多个换行符分段
    paragraphs = re.split(r'\n{2,}', text.strip())

    # 过滤空段落
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    # 如果没有明确的段落分隔，尝试按句子分割
    if len(paragraphs) == 1:
        # 按句子分割（中英文句号、问号、感叹号）
        sentences = re.split(r'([。！？!?\.]\s*)', text)

        # 重新组合句子和标点
        paragraphs = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                paragraphs.append(sentences[i] + sentences[i + 1])
            else:
                paragraphs.append(sentences[i])

        # 如果最后一个元素是不完整的，添加进去
        if len(sentences) % 2 == 1:
            paragraphs.append(sentences[-1])

    return [p for p in paragraphs if p.strip()]


def pack_sentences_into_chunks(
    sentences: List[str],
    target_tokens: int,
    overlap_chars: int = 200,
    lang_hint: str = "zh"
) -> List[str]:
    """
    将句子装箱成分块，块间重叠指定字符数

    Args:
        sentences: 句子列表
        target_tokens: 目标 token 数
        overlap_chars: 重叠字符数
        lang_hint: 语言提示

    Returns:
        分块列表
    """
    if not sentences:
        return []

    chunks = []
    current_chunk = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence, lang_hint)

        # 如果单句就超过目标，单独成块
        if sentence_tokens > target_tokens:
            if current_chunk:
                chunks.append(''.join(current_chunk))
                current_chunk = []
                current_tokens = 0
            chunks.append(sentence)
            continue

        # 如果加入当前句子会超过目标
        if current_tokens + sentence_tokens > target_tokens:
            # 保存当前块
            if current_chunk:
                chunks.append(''.join(current_chunk))

            # 创建新块，包含重叠部分
            if overlap_chars > 0 and current_chunk:
                # 从当前块末尾取重叠字符
                overlap_text = ''.join(current_chunk)[-overlap_chars:]
                current_chunk = [overlap_text, sentence]
                current_tokens = estimate_tokens(overlap_text + sentence, lang_hint)
            else:
                current_chunk = [sentence]
                current_tokens = sentence_tokens
        else:
            # 加入当前块
            current_chunk.append(sentence)
            current_tokens += sentence_tokens

    # 保存最后一块
    if current_chunk:
        chunks.append(''.join(current_chunk))

    return chunks


def plan_chunks(
    text: str,
    lang_hint: str = "zh",
    model_input_limit: int = 8000,
    budget: float = 0.7,
    overlap_chars: int = 200,
    max_chunks: int = 8,
    strategy: str = "summary_then_extract"
) -> List[str] | ChunkPlan:
    """
    规划文本分块

    Args:
        text: 输入文本
        lang_hint: 语言提示
        model_input_limit: 模型输入限制（token数）
        budget: 可用预算比例
        overlap_chars: 块间重叠字符数
        max_chunks: 最大分块数
        strategy: 降级策略 ('summary_then_extract' 或 'headN_plus_overall')

    Returns:
        分块列表或降级计划
    """
    if not text:
        return []

    # 计算目标token数
    target_tokens = int(model_input_limit * budget)
    total_tokens = estimate_tokens(text, lang_hint)

    logger.info(f"文本总token数: {total_tokens}, 目标单块token: {target_tokens}")

    # 如果文本很短，不需要分块
    if total_tokens <= target_tokens:
        return [text]

    # 按语义切分
    paragraphs = split_by_semantics(text)

    # 装箱成分块
    chunks = pack_sentences_into_chunks(
        paragraphs,
        target_tokens,
        overlap_chars,
        lang_hint
    )

    logger.info(f"初步分块数: {len(chunks)}")

    # 如果分块数超过限制，触发降级策略
    if len(chunks) > max_chunks:
        logger.warning(
            f"分块数 {len(chunks)} 超过最大限制 {max_chunks}，"
            f"触发降级策略: {strategy}"
        )

        if strategy == "summary_then_extract":
            # 策略1: 先提要，再分块抽取
            # 返回前N块 + 降级标记
            return ChunkPlan(
                strategy="summary_then_extract",
                chunks=chunks[:max_chunks],
                metadata={
                    "total_chunks": len(chunks),
                    "selected_chunks": max_chunks,
                    "overflow": len(chunks) - max_chunks
                }
            )

        elif strategy == "headN_plus_overall":
            # 策略2: 前N段 + 全文概括
            head_chunks = chunks[:max_chunks - 1]
            # 生成概括chunk（可以在后续由LLM生成）
            overall_chunk = f"[全文概括]\n前{max_chunks-1}段详细内容已处理，" \
                          f"剩余{len(chunks) - max_chunks + 1}段需要概括处理。"

            return ChunkPlan(
                strategy="headN_plus_overall",
                chunks=head_chunks + [overall_chunk],
                metadata={
                    "total_chunks": len(chunks),
                    "head_chunks": len(head_chunks),
                    "need_summary": True
                }
            )

    return chunks


def detect_language(text: str) -> str:
    """
    检测文本语言

    Args:
        text: 输入文本

    Returns:
        语言标识 ('zh', 'en', 'mixed')
    """
    if not text:
        return "zh"

    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text.strip())

    if total_chars == 0:
        return "zh"

    chinese_ratio = chinese_chars / total_chars

    if chinese_ratio > 0.7:
        return "zh"
    elif chinese_ratio < 0.3:
        return "en"
    else:
        return "mixed"
