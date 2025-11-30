"""
启动自检模块

在应用启动时执行一系列检查，确保环境配置正确。
"""

import sys
from loguru import logger

from src.config.settings import settings


def check_required_env_vars() -> bool:
    """
    检查必需的环境变量

    Returns:
        是否通过检查
    """
    logger.info("检查环境变量...")

    required_vars = {
        "DATABASE_URL": settings.DATABASE_URL,
        "REDIS_URL": settings.REDIS_URL,
        "SMTP_USER": settings.SMTP_USER,
        "SMTP_PASS": settings.SMTP_PASS,
        "PROVIDER_DEEPSEEK_API_KEY": settings.PROVIDER_DEEPSEEK_API_KEY,
    }

    missing_vars = []
    for var_name, var_value in required_vars.items():
        if not var_value or var_value == "":
            missing_vars.append(var_name)
            logger.error(f"  ❌ 缺少必需环境变量: {var_name}")

    if missing_vars:
        logger.error(f"❌ 环境变量检查失败，缺少 {len(missing_vars)} 个变量")
        return False

    logger.success(f"✅ 环境变量检查通过（共 {len(required_vars)} 个）")
    return True


def check_database() -> bool:
    """
    检查数据库连接

    Returns:
        是否通过检查
    """
    logger.info("检查数据库连接...")

    try:
        from src.db.session import get_db
        from sqlalchemy import text

        db = next(get_db())
        result = db.execute(text("SELECT 1"))
        result.fetchone()

        logger.success("✅ 数据库连接正常")
        return True

    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return False


def check_redis() -> bool:
    """
    检查 Redis 连接

    Returns:
        是否通过检查
    """
    logger.info("检查 Redis 连接...")

    try:
        import redis

        r = redis.from_url(settings.REDIS_URL)
        r.ping()

        logger.success("✅ Redis 连接正常")
        return True

    except Exception as e:
        logger.error(f"❌ Redis 连接失败: {e}")
        return False


def check_database_tables() -> bool:
    """
    检查数据库表结构

    Returns:
        是否通过检查
    """
    logger.info("检查数据库表结构...")

    try:
        from src.db.session import get_db
        from sqlalchemy import inspect

        db = next(get_db())
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()

        required_tables = [
            "sources",
            "articles",
            "extraction_queue",
            "extraction_items",
            "reports",
            "report_recipients",
            "delivery_log",
        ]

        missing_tables = [t for t in required_tables if t not in tables]

        if missing_tables:
            logger.error(f"❌ 缺少数据库表: {missing_tables}")
            return False

        logger.success(f"✅ 数据库表结构完整（共 {len(required_tables)} 个核心表）")
        return True

    except Exception as e:
        logger.error(f"❌ 数据库表检查失败: {e}")
        return False


def check_llm_providers() -> bool:
    """
    检查 LLM Provider 配置

    Returns:
        是否通过检查
    """
    logger.info("检查 LLM Provider 配置...")

    checks_passed = True

    # 检查 DeepSeek
    if settings.PROVIDER_DEEPSEEK_API_KEY:
        logger.info(f"  ✓ DeepSeek 配置: {settings.PROVIDER_DEEPSEEK_BASE_URL}")
    else:
        logger.warning("  ⚠️ DeepSeek API Key 未配置")
        checks_passed = False

    # 检查 Qwen
    if settings.PROVIDER_QWEN_API_KEY and settings.PROVIDER_QWEN_API_KEY != "sk-xxx":
        logger.info(f"  ✓ Qwen 配置: {settings.PROVIDER_QWEN_BASE_URL}")
    else:
        logger.warning("  ⚠️ Qwen API Key 未配置（将使用 DeepSeek 作为唯一 Provider）")

    if checks_passed:
        logger.success("✅ LLM Provider 配置正常")
    else:
        logger.warning("⚠️ 部分 LLM Provider 未配置")

    return True  # 不强制要求所有 Provider 都配置


def check_smtp_config() -> bool:
    """
    检查 SMTP 配置

    Returns:
        是否通过检查
    """
    logger.info("检查 SMTP 配置...")

    try:
        from src.mailer.smtp_client import SMTPClient
        import asyncio

        client = SMTPClient()

        # 测试连接（异步）
        async def test_connection():
            return await client.test_connection()

        result = asyncio.run(test_connection())

        if result:
            logger.success("✅ SMTP 连接测试成功")
            return True
        else:
            logger.error("❌ SMTP 连接测试失败")
            return False

    except Exception as e:
        logger.error(f"❌ SMTP 配置检查失败: {e}")
        return False


def check_directories() -> bool:
    """
    检查必需的目录

    Returns:
        是否通过检查
    """
    logger.info("检查目录结构...")

    from pathlib import Path

    required_dirs = [
        "logs",
        "src/composer/templates",
    ]

    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            logger.warning(f"  ⚠️ 目录不存在，自动创建: {dir_path}")
            path.mkdir(parents=True, exist_ok=True)

    logger.success("✅ 目录结构检查完成")
    return True


def bootstrap(
    strict: bool = False,
    skip_smtp: bool = False,
    skip_llm: bool = False
) -> bool:
    """
    启动自检

    Args:
        strict: 严格模式，任何检查失败都退出
        skip_smtp: 跳过 SMTP 检查
        skip_llm: 跳过 LLM 检查

    Returns:
        是否所有检查都通过
    """
    logger.info("=" * 60)
    logger.info("🚀 启动自检开始...")
    logger.info("=" * 60)

    checks = []

    # 1. 环境变量检查（必须）
    checks.append(("环境变量", check_required_env_vars(), True))

    # 2. 数据库检查（必须）
    checks.append(("数据库连接", check_database(), True))

    # 3. 数据库表检查（必须）
    checks.append(("数据库表", check_database_tables(), True))

    # 4. Redis 检查（必须）
    checks.append(("Redis", check_redis(), True))

    # 5. 目录检查（必须）
    checks.append(("目录结构", check_directories(), True))

    # 6. LLM Provider 检查（可选）
    if not skip_llm:
        checks.append(("LLM Provider", check_llm_providers(), False))

    # 7. SMTP 检查（可选）
    if not skip_smtp:
        checks.append(("SMTP", check_smtp_config(), False))

    # 统计结果
    logger.info("=" * 60)
    logger.info("📊 自检结果汇总:")
    logger.info("=" * 60)

    all_passed = True
    critical_failed = False

    for check_name, passed, is_critical in checks:
        status = "✅ 通过" if passed else "❌ 失败"
        criticality = "【必须】" if is_critical else "【可选】"

        if passed:
            logger.success(f"  {status} {criticality} {check_name}")
        else:
            logger.error(f"  {status} {criticality} {check_name}")
            all_passed = False
            if is_critical:
                critical_failed = True

    logger.info("=" * 60)

    if critical_failed:
        logger.error("❌ 启动自检失败：存在必需项检查未通过")
        if strict:
            logger.error("严格模式：应用将退出")
            sys.exit(1)
        return False
    elif all_passed:
        logger.success("✅ 启动自检完成：所有检查通过")
        return True
    else:
        logger.warning("⚠️ 启动自检完成：部分可选项检查未通过，但不影响核心功能")
        return True


if __name__ == "__main__":
    # 命令行测试
    import argparse

    parser = argparse.ArgumentParser(description="启动自检")
    parser.add_argument("--strict", action="store_true", help="严格模式")
    parser.add_argument("--skip-smtp", action="store_true", help="跳过 SMTP 检查")
    parser.add_argument("--skip-llm", action="store_true", help="跳过 LLM 检查")

    args = parser.parse_args()

    success = bootstrap(
        strict=args.strict,
        skip_smtp=args.skip_smtp,
        skip_llm=args.skip_llm
    )

    sys.exit(0 if success else 1)
