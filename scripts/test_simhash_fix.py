"""
测试 SimHash 修复是否生效
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.deduplicator import Deduplicator
from src.utils.logger import logger


def test_simhash_range():
    """测试 SimHash 值是否在 PostgreSQL BIGINT 范围内"""

    logger.info("=" * 80)
    logger.info("测试 SimHash 值范围")
    logger.info("=" * 80)

    dedup = Deduplicator()

    # 测试文本（这个文本之前产生了溢出的 SimHash）
    test_texts = [
        "新智元报道 编辑：元宇 【新智元导读】 近日，Meta员工priiir（网名）发帖，称团队中除自己之外全是华人...",
        "全球十大AI杀入美股！最新战况曝光，第一名太意外...",
        "谷歌Gemini闹乌龙：我家狗子，竟被AI开除了「狗籍」！...",
        "A" * 1000,  # 长文本
        "测试" * 500,  # 中文重复
    ]

    MAX_BIGINT = 9223372036854775807  # 2^63 - 1
    MIN_BIGINT = -9223372036854775808  # -2^63

    logger.info(f"\nPostgreSQL BIGINT 范围:")
    logger.info(f"  最小值: {MIN_BIGINT:,}")
    logger.info(f"  最大值: {MAX_BIGINT:,}")
    logger.info(f"\n开始测试 {len(test_texts)} 个文本:\n")

    all_pass = True

    for idx, text in enumerate(test_texts, 1):
        hash_value = dedup.compute_simhash(text)

        in_range = MIN_BIGINT <= hash_value <= MAX_BIGINT
        status = "✅ PASS" if in_range else "❌ FAIL"

        logger.info(f"测试 {idx}: {status}")
        logger.info(f"  文本长度: {len(text)}")
        logger.info(f"  SimHash: {hash_value:,}")
        logger.info(f"  在范围内: {in_range}")

        if not in_range:
            all_pass = False
            logger.error(f"  ❌ 超出范围！")

        logger.info("")

    logger.info("=" * 80)
    if all_pass:
        logger.info("✅ 所有测试通过！SimHash 值都在 PostgreSQL BIGINT 范围内")
    else:
        logger.error("❌ 有测试失败！存在超出范围的 SimHash 值")
    logger.info("=" * 80)

    return all_pass


def test_duplicate_detection():
    """测试去重功能是否正常"""

    logger.info("\n" + "=" * 80)
    logger.info("测试去重功能")
    logger.info("=" * 80)

    dedup = Deduplicator()

    # 相同文本
    text1 = "这是一篇测试文章，用于验证去重功能是否正常工作。"
    text2 = "这是一篇测试文章，用于验证去重功能是否正常工作。"

    # 相似文本（汉明距离应该 ≤ 3）
    text3 = "这是一篇测试文章，用于验证去重功能是否正常工作！"

    # 不同文本
    text4 = "完全不同的文章内容，应该不会被判定为重复。"

    hash1 = dedup.compute_simhash(text1)
    hash2 = dedup.compute_simhash(text2)
    hash3 = dedup.compute_simhash(text3)
    hash4 = dedup.compute_simhash(text4)

    logger.info(f"\n文本1 SimHash: {hash1:,}")
    logger.info(f"文本2 SimHash: {hash2:,}")
    logger.info(f"文本3 SimHash: {hash3:,}")
    logger.info(f"文本4 SimHash: {hash4:,}")

    is_dup_12 = dedup.is_duplicate(hash1, hash2)
    is_dup_13 = dedup.is_duplicate(hash1, hash3)
    is_dup_14 = dedup.is_duplicate(hash1, hash4)

    logger.info(f"\n文本1 vs 文本2 (相同): {is_dup_12} {'✅' if is_dup_12 else '❌'}")
    logger.info(f"文本1 vs 文本3 (相似): {is_dup_13} {'✅' if is_dup_13 else '❌'}")
    logger.info(f"文本1 vs 文本4 (不同): {not is_dup_14} {'✅' if not is_dup_14 else '❌'}")

    all_pass = is_dup_12 and is_dup_13 and not is_dup_14

    logger.info("\n" + "=" * 80)
    if all_pass:
        logger.info("✅ 去重功能测试通过！")
    else:
        logger.error("❌ 去重功能测试失败！")
    logger.info("=" * 80)

    return all_pass


def main():
    logger.info("🔍 测试 SimHash 修复方案\n")

    test1_pass = test_simhash_range()
    test2_pass = test_duplicate_detection()

    logger.info("\n" + "=" * 80)
    logger.info("测试总结")
    logger.info("=" * 80)
    logger.info(f"范围测试: {'✅ PASS' if test1_pass else '❌ FAIL'}")
    logger.info(f"去重测试: {'✅ PASS' if test2_pass else '❌ FAIL'}")
    logger.info("=" * 80)

    if test1_pass and test2_pass:
        logger.info("\n🎉 所有测试通过！修复方案有效！")
        return 0
    else:
        logger.error("\n❌ 测试失败，需要进一步检查")
        return 1


if __name__ == "__main__":
    exit(main())
