"""
SMTP 客户端模块

实现异步邮件发送，支持 SSL/TLS、附件、UTF-8 编码。
"""

import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from typing import Optional

import aiosmtplib
from loguru import logger

from src.config.settings import settings
from src.utils.time_utils import get_local_now


class SMTPClient:
    """
    SMTP 客户端

    支持：
    - SSL/TLS 加密连接
    - 异步发送
    - HTML 邮件
    - HTML 附件
    - UTF-8 编码
    - 密送（BCC）
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        from_name: str = "金融情报系统"
    ):
        """
        初始化 SMTP 客户端

        Args:
            host: SMTP 服务器地址
            port: SMTP 端口（465 for SSL）
            user: 发件人邮箱
            password: 授权码或密码
            from_name: 发件人昵称
        """
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.user = user or settings.SMTP_USER
        self.password = password or settings.SMTP_PASS
        self.from_name = from_name

        logger.info(f"初始化 SMTP 客户端: {self.host}:{self.port}")

    async def send_email(
        self,
        to: list[str],
        subject: str,
        html_body: str,
        bcc: Optional[list[str]] = None,
        attachments: Optional[list[tuple[str, bytes]]] = None
    ) -> dict:
        """
        发送邮件

        Args:
            to: 收件人列表（显示在 To 字段）
            subject: 邮件主题
            html_body: HTML 邮件正文
            bcc: 密送列表（不显示在邮件头）
            attachments: 附件列表，格式 [(filename, bytes_content), ...]

        Returns:
            发送结果字典:
            {
                "message_id": str,      # 邮件唯一ID
                "status": "ok"|"failed", # 发送状态
                "error": str|None,       # 错误信息
                "sent_at": str,          # 发送时间
                "to_count": int,         # 收件人数量
                "bcc_count": int         # 密送数量
            }
        """
        try:
            # 生成唯一邮件 ID
            message_id = self._generate_message_id()

            # 创建邮件
            msg = self._build_message(
                to=to,
                subject=subject,
                html_body=html_body,
                bcc=bcc,
                attachments=attachments,
                message_id=message_id
            )

            # 发送邮件
            await self._send_smtp(msg, to, bcc)

            logger.success(
                f"✅ 邮件发送成功: {message_id} | "
                f"To: {len(to)}, BCC: {len(bcc) if bcc else 0}"
            )

            return {
                "message_id": message_id,
                "status": "ok",
                "error": None,
                "sent_at": get_local_now().isoformat(),
                "to_count": len(to),
                "bcc_count": len(bcc) if bcc else 0,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 邮件发送失败: {error_msg}", exc_info=True)

            return {
                "message_id": message_id if 'message_id' in locals() else None,
                "status": "failed",
                "error": error_msg,
                "sent_at": get_local_now().isoformat(),
                "to_count": len(to),
                "bcc_count": len(bcc) if bcc else 0,
            }

    def _generate_message_id(self) -> str:
        """生成唯一的邮件 ID"""
        return f"{uuid.uuid4().hex}@{self.host}"

    def _build_message(
        self,
        to: list[str],
        subject: str,
        html_body: str,
        bcc: Optional[list[str]],
        attachments: Optional[list[tuple[str, bytes]]],
        message_id: str
    ) -> MIMEMultipart:
        """
        构建 MIME 邮件对象

        Args:
            to: 收件人列表
            subject: 邮件主题
            html_body: HTML 正文
            bcc: 密送列表
            attachments: 附件列表
            message_id: 邮件 ID

        Returns:
            MIMEMultipart 邮件对象
        """
        # 创建邮件对象
        msg = MIMEMultipart('mixed')

        # 设置基本字段
        msg['From'] = formataddr((self.from_name, self.user))
        msg['To'] = ', '.join(to)
        msg['Subject'] = Header(subject, 'utf-8')
        msg['Message-ID'] = f"<{message_id}>"
        msg['Date'] = get_local_now().strftime('%a, %d %b %Y %H:%M:%S +0800')

        # BCC 不写入邮件头（隐私保护）
        # 但在发送时会传递给 SMTP 服务器

        # 添加 HTML 正文
        html_part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(html_part)

        # 添加附件
        if attachments:
            for filename, content in attachments:
                # HTML 附件
                if filename.endswith('.html'):
                    attachment = MIMEText(content.decode('utf-8'), 'html', 'utf-8')
                    attachment.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=('utf-8', '', filename)
                    )
                else:
                    # 其他类型附件（未来扩展）
                    from email.mime.base import MIMEBase
                    from email import encoders

                    attachment = MIMEBase('application', 'octet-stream')
                    attachment.set_payload(content)
                    encoders.encode_base64(attachment)
                    attachment.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=('utf-8', '', filename)
                    )

                msg.attach(attachment)

        return msg

    async def _send_smtp(
        self,
        msg: MIMEMultipart,
        to: list[str],
        bcc: Optional[list[str]]
    ):
        """
        通过 SMTP 服务器发送邮件

        Args:
            msg: MIME 邮件对象
            to: 收件人列表
            bcc: 密送列表
        """
        # 合并所有收件人（To + BCC）
        all_recipients = to + (bcc if bcc else [])

        # 连接并发送
        async with aiosmtplib.SMTP(
            hostname=self.host,
            port=self.port,
            use_tls=True,  # SSL 加密（465 端口）
            timeout=30,
        ) as smtp:
            # 登录
            await smtp.login(self.user, self.password)

            # 发送邮件
            await smtp.send_message(
                msg,
                sender=self.user,
                recipients=all_recipients
            )

    async def test_connection(self) -> bool:
        """
        测试 SMTP 连接和认证

        Returns:
            是否连接成功
        """
        try:
            async with aiosmtplib.SMTP(
                hostname=self.host,
                port=self.port,
                use_tls=True,
                timeout=10,
            ) as smtp:
                await smtp.login(self.user, self.password)

            logger.success(f"✅ SMTP 连接测试成功: {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"❌ SMTP 连接测试失败: {e}")
            return False
