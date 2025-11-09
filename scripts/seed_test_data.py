"""
测试数据初始化脚本

读取 `tests/data/e2e_sources_and_recipients.json`，将信息源与收件人写入数据库。

用法:
    python scripts/seed_test_data.py
    python scripts/seed_test_data.py --data ./custom.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from loguru import logger
from sqlalchemy import select

from src.db.session import SessionLocal
from src.models.source import Source, SourceType
from src.models.delivery import ReportRecipient, RecipientType


DEFAULT_DATA_PATH = Path("tests/data/e2e_sources_and_recipients.json")


def load_payload(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def seed_sources(session, sources: list[dict]) -> tuple[int, int]:
    inserted = 0
    skipped = 0

    for item in sources:
        source_url = item["url"].strip()
        exists = session.execute(
            select(Source).where(Source.url == source_url)
        ).scalar_one_or_none()

        if exists:
            skipped += 1
            continue

        source = Source(
            name=item["name"],
            type=SourceType(item["type"]),
            url=source_url,
            enabled=item.get("enabled", True),
            concurrency=item.get("concurrency", 1),
            timeout_sec=item.get("timeout_sec", 30),
            parser=item.get("parser"),
        )

        session.add(source)
        inserted += 1

    session.commit()
    return inserted, skipped


def seed_recipients(session, recipients: list[str]) -> tuple[int, int]:
    inserted = 0
    skipped = 0

    for email in recipients:
        email_norm = email.strip().lower()
        exists = session.execute(
            select(ReportRecipient).where(ReportRecipient.email == email_norm)
        ).scalar_one_or_none()

        if exists:
            skipped += 1
            continue

        recipient = ReportRecipient(
            email=email_norm,
            display_name=email_norm.split("@")[0],
            type=RecipientType.RECIPIENT,
            enabled=True,
        )

        session.add(recipient)
        inserted += 1

    session.commit()
    return inserted, skipped


def main():
    parser = argparse.ArgumentParser(description="导入测试信息源与收件人数据")
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="JSON 数据文件路径 (默认: tests/data/e2e_sources_and_recipients.json)",
    )

    args = parser.parse_args()

    payload = load_payload(args.data)
    sources = payload.get("sources", [])
    recipients = payload.get("recipients", [])

    if not sources:
        logger.warning("数据文件未包含 sources 字段或为空")
    if not recipients:
        logger.warning("数据文件未包含 recipients 字段或为空")

    session = SessionLocal()
    try:
        new_sources, skipped_sources = seed_sources(session, sources)
        new_recipients, skipped_recipients = seed_recipients(session, recipients)
    finally:
        session.close()

    logger.success(
        "信息源导入完成: 新增 {} 条, 已存在 {} 条",
        new_sources,
        skipped_sources,
    )
    logger.success(
        "收件人导入完成: 新增 {} 条, 已存在 {} 条",
        new_recipients,
        skipped_recipients,
    )


if __name__ == "__main__":
    main()
