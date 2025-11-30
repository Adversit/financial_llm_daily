#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""禁用OpenAI数据源"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from src.db.session import get_db
from src.models.source import Source
from loguru import logger

def disable_openai():
    """禁用OpenAI数据源"""
    db = next(get_db())
    try:
        # 查找OpenAI数据源
        source = db.query(Source).filter(Source.name == "OpenAI").first()

        if not source:
            logger.warning("未找到名为'OpenAI'的数据源")
            return False

        if not source.enabled:
            logger.info(f"数据源 '{source.name}' 已经是禁用状态")
            return True

        # 禁用
        source.enabled = False
        db.commit()

        logger.success(f"成功禁用数据源: {source.name} (ID: {source.id}, URL: {source.url})")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"禁用数据源失败: {e}")
        return False
    finally:
        db.close()

def enable_openai():
    """启用OpenAI数据源"""
    db = next(get_db())
    try:
        # 查找OpenAI数据源
        source = db.query(Source).filter(Source.name == "OpenAI").first()

        if not source:
            logger.warning("未找到名为'OpenAI'的数据源")
            return False

        if source.enabled:
            logger.info(f"数据源 '{source.name}' 已经是启用状态")
            return True

        # 启用
        source.enabled = True
        db.commit()

        logger.success(f"成功启用数据源: {source.name} (ID: {source.id}, URL: {source.url})")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"启用数据源失败: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="管理OpenAI数据源的启用/禁用状态")
    parser.add_argument(
        "action",
        choices=["disable", "enable"],
        help="操作: disable(禁用) 或 enable(启用)"
    )

    args = parser.parse_args()

    if args.action == "disable":
        success = disable_openai()
    else:
        success = enable_openai()

    sys.exit(0 if success else 1)
