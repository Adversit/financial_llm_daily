"""
分块引擎测试
"""

from src.nlp.chunking import (
    ChunkPlan,
    detect_language,
    estimate_tokens,
    pack_sentences_into_chunks,
    plan_chunks,
    split_by_semantics,
)


def test_estimate_tokens_for_languages():
    zh_text = "这是一个中文句子"
    en_text = "This is an English sentence."

    assert estimate_tokens(zh_text, lang_hint="zh") == len(zh_text)
    # 英文会按照 1.3 倍词数估算
    assert estimate_tokens(en_text, lang_hint="en") == int(len(en_text.split()) * 1.3)


def test_split_by_semantics_handles_paragraphs():
    text = "第一段。\n\n第二段。"

    paragraphs = split_by_semantics(text)

    assert paragraphs == ["第一段。", "第二段。"]


def test_pack_sentences_respects_overlap():
    sentences = ["段落一。", "段落二。", "段落三。"]
    chunks = pack_sentences_into_chunks(
        sentences,
        target_tokens=5,
        overlap_chars=2,
        lang_hint="zh",
    )

    assert len(chunks) >= 2
    if len(chunks) >= 2:
        overlap = chunks[0][-2:]
        assert chunks[1].startswith(overlap)


def test_plan_chunks_triggers_degrade():
    # 构造足够长的文本触发降级
    text = "\n\n".join(f"段落 {i} 内容" * 20 for i in range(10))

    result = plan_chunks(
        text=text,
        lang_hint="zh",
        model_input_limit=200,
        budget=0.2,
        overlap_chars=10,
        max_chunks=3,
        strategy="summary_then_extract",
    )

    assert isinstance(result, ChunkPlan)
    assert result.strategy == "summary_then_extract"
    assert result.metadata["total_chunks"] > result.metadata["selected_chunks"]


def test_detect_language_outputs_expected_labels():
    assert detect_language("这是中文") == "zh"
    assert detect_language("This is English") == "en"
    assert detect_language("中文 English 混合") == "mixed"
