"""
SMTP 客户端测试
"""

from email.mime.multipart import MIMEMultipart

import pytest
from unittest.mock import AsyncMock

from src.mailer.smtp_client import SMTPClient


@pytest.mark.asyncio
async def test_send_email_success(monkeypatch):
    client = SMTPClient(
        host="smtp.test",
        port=465,
        user="sender@test.com",
        password="secret",
    )

    send_mock = AsyncMock()
    monkeypatch.setattr(client, "_send_smtp", send_mock)
    monkeypatch.setattr(SMTPClient, "_generate_message_id", lambda self: "msg-id")

    result = await client.send_email(
        to=["user@test.com"],
        subject="测试邮件",
        html_body="<p>正文</p>",
        bcc=["hidden@test.com"],
    )

    send_mock.assert_awaited_once()
    msg_arg, to_arg, bcc_arg = send_mock.await_args.args
    assert isinstance(msg_arg, MIMEMultipart)
    assert to_arg == ["user@test.com"]
    assert bcc_arg == ["hidden@test.com"]

    assert result["status"] == "ok"
    assert result["message_id"] == "msg-id"
    assert result["to_count"] == 1
    assert result["bcc_count"] == 1


@pytest.mark.asyncio
async def test_send_email_failure(monkeypatch):
    client = SMTPClient(
        host="smtp.test",
        port=465,
        user="sender@test.com",
        password="secret",
    )

    send_mock = AsyncMock(side_effect=RuntimeError("smtp error"))
    monkeypatch.setattr(client, "_send_smtp", send_mock)
    monkeypatch.setattr(SMTPClient, "_generate_message_id", lambda self: "msg-id")

    result = await client.send_email(
        to=["user@test.com"],
        subject="测试邮件",
        html_body="<p>正文</p>",
    )

    assert result["status"] == "failed"
    assert result["error"] == "smtp error"
    assert result["message_id"] == "msg-id"


def test_build_message_excludes_bcc_header(monkeypatch):
    client = SMTPClient(
        host="smtp.test",
        port=465,
        user="sender@test.com",
        password="secret",
    )

    html_attachment = "<html>附件</html>".encode("utf-8")
    msg = client._build_message(
        to=["user@test.com"],
        subject="测试",
        html_body="<p>正文</p>",
        bcc=["hidden@test.com"],
        attachments=[("report.html", html_attachment)],
        message_id="msg-id",
    )

    assert msg["Message-ID"] == "<msg-id>"
    assert msg["Subject"].encode("utf-8")
    assert msg["Bcc"] is None

    payload = msg.get_payload()
    assert any(part.get_content_subtype() == "html" for part in payload)
