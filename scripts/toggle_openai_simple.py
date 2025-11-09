#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单的OpenAI数据源启用/禁用脚本"""
import os
import sys
from sqlalchemy import create_engine, text

# 从环境变量获取数据库URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://fin_user:fin_pass@localhost:5432/fin_daily_report")

def toggle_openai(enable: bool):
    """切换OpenAI数据源状态"""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # 查询当前状态
        result = conn.execute(
            text("SELECT id, name, type, url, enabled FROM sources WHERE name = 'OpenAI'")
        )
        row = result.fetchone()

        if not row:
            print("❌ 未找到名为'OpenAI'的数据源")
            return False

        print(f"\n当前状态:")
        print(f"  ID: {row[0]}")
        print(f"  名称: {row[1]}")
        print(f"  类型: {row[2]}")
        print(f"  URL: {row[3]}")
        print(f"  启用状态: {row[4]}")

        # 更新状态
        conn.execute(
            text("UPDATE sources SET enabled = :enabled WHERE name = 'OpenAI'"),
            {"enabled": enable}
        )
        conn.commit()

        # 确认更新
        result = conn.execute(
            text("SELECT enabled FROM sources WHERE name = 'OpenAI'")
        )
        new_status = result.fetchone()[0]

        action = "启用" if enable else "禁用"
        print(f"\n✅ 成功{action}OpenAI数据源 (新状态: {new_status})")
        return True

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["enable", "disable"]:
        print("用法: python toggle_openai_simple.py [enable|disable]")
        sys.exit(1)

    enable = sys.argv[1] == "enable"
    success = toggle_openai(enable)
    sys.exit(0 if success else 1)
