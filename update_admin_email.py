#!/usr/bin/env python3
"""更新管理员邮箱为 xtyydsf"""

from sqlalchemy import create_engine, text
from src.config.settings import settings

def main():
    engine = create_engine(settings.DATABASE_URL)

    with engine.connect() as conn:
        # 更新管理员邮箱为 xtyydsf@system
        result = conn.execute(
            text("UPDATE users SET email = 'xtyydsf@system' WHERE role = 'admin'")
        )
        conn.commit()
        print(f"✓ 已更新 {result.rowcount} 条管理员记录")

        # 验证更新
        result = conn.execute(
            text("SELECT email, role, is_active FROM users WHERE role = 'admin'")
        )

        print("\n管理员账号信息:")
        for row in result:
            print(f"  邮箱: {row[0]}")
            print(f"  角色: {row[1]}")
            print(f"  状态: {'激活' if row[2] else '未激活'}")

        print("\n✓ 管理员登录凭证:")
        print("  账号: xtyydsf （系统会自动补全为 xtyydsf@system）")
        print("  密码: xtyydsf")

if __name__ == "__main__":
    main()
