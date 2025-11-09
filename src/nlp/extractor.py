"""
LLM 抽取器模块

使用 LLM 从文章中抽取事实和观点。
"""

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.models.article import Article
from src.nlp.chunking import ChunkPlan, detect_language, plan_chunks
from src.nlp.provider_router import get_provider_router


def clean_json_string(content: str) -> str:
    """
    清理 JSON 字符串中可能导致解析失败的字符

    Args:
        content: 原始 JSON 字符串

    Returns:
        清理后的 JSON 字符串
    """
    # 1. 替换中文引号为英文引号
    content = content.replace('"', '"').replace('"', '"')
    content = content.replace(''', "'").replace(''', "'")

    # 2. 移除可能的 BOM 标记
    content = content.replace('\ufeff', '')

    return content


# 抽取 Prompt 模板
EXTRACTION_PROMPT = """你是一个专业的金融情报分析师。请从以下文章中抽取与金融行业强相关的情报。

**核心原则：本系统为金融情报日报，所有内容必须与金融行业强相关**

请抽取以下信息：

1. **客观事实（fact）**：重要事件、数据、发布等，必选
2. **观点（opinion）**：作者/机构的观点、预测、评论，可选
3. **区域（region）**：国内 | 国外 | 未知
4. **层级（layer）**：金融政策监管 | 金融经济 | 金融大模型技术 | 金融科技应用 | 未知
5. **置信度（confidence）**：0.0-1.0，根据原文明确程度评估
6. **金融相关性（finance_relevance）**：0.0-1.0，评估与金融行业的关联度

**层级定义（必须严格遵守）**：
- **金融政策监管**：央行政策、金融监管、资本市场监管、金融法规等
- **金融经济**：股市、债市、汇市、投融资、IPO、并购、金融机构业绩、金融市场数据等
- **金融大模型技术**：大模型技术本身的最新进展和影响，包括技术突破、模型发布、性能提升等（金融相关性要求可以放宽）
- **金融科技应用**：AI/大数据/区块链在金融场景的应用、金融科技公司动态、支付创新等

**金融相关性评估标准**：
- 1.0：直接金融内容（如：IPO、央行政策、金融科技产品）
- 0.7-0.9：间接金融影响（如：大模型商业化潜力、科技公司估值）
- 0.4-0.6：弱金融关联（如：技术进展可能影响金融应用）
- 0.2-0.3：大模型技术本身（即使金融关联弱，但技术重要）
- 0.0-0.1：无关联内容（应直接过滤）

**过滤规则**：
- **金融政策监管、金融经济、金融科技应用层级**：金融相关性 < 0.4 的内容直接丢弃
- **金融大模型技术层级**：金融相关性 < 0.2 的内容丢弃（技术本身重要，阈值可以更低）
- 纯政治事件（无金融监管内容）→ 过滤
- 社会新闻（刑事案件、医疗事故等）→ 过滤

**返回格式**（严格的 JSON）：

```json
{{
  "items": [
    {{
      "fact": "具体的客观事实描述",
      "opinion": "相关的观点或评论（可为空字符串）",
      "region": "国内|国外|未知",
      "layer": "金融政策监管|金融经济|金融大模型技术|金融科技应用|未知",
      "evidence_span": "原文句段（支持该事实/观点的原文片段）",
      "confidence": 0.85,
      "finance_relevance": 0.9
    }}
  ]
}}
```

**重要要求**：
- 每条必须包含清晰的事实描述
- 观点字段可以为空字符串，但不要省略该字段
- evidence_span 应引用原文的关键句段
- 如果文章完全无金融相关内容，返回空数组 {{"items": []}}
- **严格使用标准 JSON 格式，所有字符串必须使用英文双引号 "，不要使用中文引号 " " ' '**
- **evidence_span 中如果原文包含引号，请将其替换为单引号或直接省略**

---

**文章内容**：

{content}

---

请返回严格的 JSON 格式抽取结果（只返回JSON，不要其他说明文字）：
"""


@dataclass
class ExtractResult:
    """抽取结果"""
    status: str  # 'success', 'failed', 'partial'
    items: List[Dict]  # 抽取的事实观点列表
    metadata: Dict  # 元数据
    error: Optional[str] = None


async def extract_from_chunk(
    chunk: str,
    chunk_index: int,
    total_chunks: int,
) -> Dict:
    """
    对单个分块调用 LLM 抽取

    Args:
        chunk: 文本分块
        chunk_index: 分块索引（从0开始）
        total_chunks: 总分块数

    Returns:
        抽取结果字典
    """
    router = get_provider_router()

    # 构建消息
    prompt = EXTRACTION_PROMPT.format(content=chunk)
    messages = [
        {"role": "system", "content": "你是一个专业的金融情报分析师，擅长从文章中提取关键信息。"},
        {"role": "user", "content": prompt}
    ]

    try:
        logger.info(f"开始抽取分块 {chunk_index + 1}/{total_chunks}，长度: {len(chunk)} 字符")

        # 调用 LLM
        response, provider_name = await router.call_with_fallback(
            messages=messages,
            temperature=0.3,
            retries=settings.LLM_RETRIES,
            timeout=settings.LLM_TIMEOUT_SEC,
        )

        content = response["content"].strip()

        # 解析 JSON
        # 尝试提取 JSON（可能包含在 markdown 代码块中）
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # 清理 JSON 字符串（处理中文引号等问题）
        content = clean_json_string(content)

        result = json.loads(content)

        items = result.get("items", [])

        logger.success(
            f"✅ 分块 {chunk_index + 1}/{total_chunks} 抽取成功，"
            f"抽取了 {len(items)} 条，使用 Provider: {provider_name}"
        )

        return {
            "chunk_index": chunk_index,
            "items": items,
            "provider": provider_name,
            "usage": response.get("usage", {}),
            "status": "success"
        }

    except json.JSONDecodeError as e:
        logger.error(f"❌ 分块 {chunk_index + 1} JSON 解析失败: {e}")
        logger.warning(f"原始响应（已清理）: {content}")  # 保留为 warning 方便调试
        return {
            "chunk_index": chunk_index,
            "items": [],
            "error": f"JSON解析失败: {str(e)}",
            "status": "failed"
        }

    except Exception as e:
        logger.error(f"❌ 分块 {chunk_index + 1} 抽取失败: {e}")
        return {
            "chunk_index": chunk_index,
            "items": [],
            "error": str(e),
            "status": "failed"
        }


async def extract_article(
    article_id: int,
    db: Session,
) -> ExtractResult:
    """
    对文章进行抽取

    Args:
        article_id: 文章ID
        db: 数据库会话

    Returns:
        抽取结果
    """
    try:
        # 读取文章
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            logger.error(f"文章不存在: {article_id}")
            return ExtractResult(
                status="failed",
                items=[],
                metadata={},
                error="文章不存在"
            )

        content = article.content_text
        if not content or len(content.strip()) < settings.MIN_CONTENT_LEN:
            logger.warning(f"文章内容过短或为空: {article_id}")
            return ExtractResult(
                status="failed",
                items=[],
                metadata={"reason": "content_too_short"},
                error="文章内容过短"
            )

        logger.info(f"开始处理文章 {article_id}: {article.title}")

        # 检测语言
        lang_hint = detect_language(content)
        logger.info(f"检测到语言: {lang_hint}")

        # 估算文章 token 数，判断是否需要分块
        from src.nlp.chunking import estimate_tokens

        estimated_tokens = estimate_tokens(content, lang_hint)
        # 模型输入限制，预留一些空间给 prompt
        # DeepSeek: 64K tokens, Qwen: 128K tokens
        # 保守起见使用 64K 作为限制
        model_limit = 64000
        safe_limit = int(model_limit * settings.LLM_CHUNK_BUDGET)  # 默认 0.7 * 64000 = 44800

        logger.info(f"文章估算 token 数: {estimated_tokens}, 安全限制: {safe_limit}")

        # 只有在文章超过安全限制时才分块
        if estimated_tokens > safe_limit:
            logger.warning(
                f"⚠️ 文章较长（{estimated_tokens} tokens），启动分块处理"
            )

            # 规划分块
            chunks_or_plan = plan_chunks(
                text=content,
                lang_hint=lang_hint,
                model_input_limit=model_limit,
                budget=settings.LLM_CHUNK_BUDGET,
                overlap_chars=settings.LLM_CHUNK_OVERLAP_CHARS,
                max_chunks=settings.LLM_MAX_CHUNKS_PER_ARTICLE,
                strategy=settings.LLM_LONGFORM_STRATEGY,
            )

            # 处理降级策略
            if isinstance(chunks_or_plan, ChunkPlan):
                logger.warning(f"触发降级策略: {chunks_or_plan.strategy}")
                chunks = chunks_or_plan.chunks
                metadata = chunks_or_plan.metadata
                metadata["degraded"] = True
                metadata["strategy"] = chunks_or_plan.strategy
            else:
                chunks = chunks_or_plan
                metadata = {"degraded": False}
        else:
            # 正常情况：整篇文章作为一个块处理
            logger.info("✅ 文章长度正常，直接整篇处理")
            chunks = [content]
            metadata = {"degraded": False, "chunked": False}

        total_chunks = len(chunks)
        logger.info(f"共 {total_chunks} 个分块")

        # 逐块抽取
        all_items = []
        chunk_results = []
        failed_chunks = 0

        for i, chunk in enumerate(chunks):
            result = await extract_from_chunk(chunk, i, total_chunks)
            chunk_results.append(result)

            if result["status"] == "success":
                all_items.extend(result["items"])
            else:
                failed_chunks += 1

        # 计算总 usage
        total_usage = {
            "prompt_tokens": sum(r.get("usage", {}).get("prompt_tokens", 0) for r in chunk_results),
            "completion_tokens": sum(r.get("usage", {}).get("completion_tokens", 0) for r in chunk_results),
            "total_tokens": sum(r.get("usage", {}).get("total_tokens", 0) for r in chunk_results),
        }

        # 确定状态
        if failed_chunks == 0:
            status = "success"
        elif failed_chunks < total_chunks:
            status = "partial"
        else:
            status = "failed"

        metadata.update({
            "total_chunks": total_chunks,
            "failed_chunks": failed_chunks,
            "total_items": len(all_items),
            "usage": total_usage,
            "article_length": len(content),
        })

        logger.info(
            f"文章 {article_id} 抽取完成: 状态={status}, "
            f"抽取了 {len(all_items)} 条，失败 {failed_chunks} 块"
        )

        return ExtractResult(
            status=status,
            items=all_items,
            metadata=metadata,
            error=None if status != "failed" else "所有分块抽取失败"
        )

    except Exception as e:
        logger.error(f"文章 {article_id} 抽取异常: {e}")
        return ExtractResult(
            status="failed",
            items=[],
            metadata={},
            error=str(e)
        )
