"""
投递相关模型
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON, Float, Index
from sqlalchemy.orm import relationship
import enum
from .base import Base, TimestampMixin
from src.utils.time_utils import get_local_now_naive


class RecipientType(str, enum.Enum):
    """收件人类型"""
    WHITELIST = "whitelist"
    RECIPIENT = "recipient"


class DeliveryStatus(str, enum.Enum):
    """投递状态"""
    OK = "ok"
    FAILED = "failed"
    PARTIAL = "partial"


class ReportRecipient(Base, TimestampMixin):
    """报告收件人表"""
    __tablename__ = "report_recipients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(200), nullable=False, comment="邮箱地址")
    display_name = Column(String(100), nullable=True, comment="显示名称")
    type = Column(SQLEnum(RecipientType, native_enum=True, values_callable=lambda x: [e.value for e in x]), default=RecipientType.RECIPIENT, nullable=False, comment="类型")
    enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")

    __table_args__ = (
        Index("idx_recipients_email", "email"),
        Index("idx_recipients_type_enabled", "type", "enabled"),
        Index("idx_recipients_email_type", "email", "type", unique=True),
    )

    def __repr__(self):
        return f"<ReportRecipient(id={self.id}, email={self.email}, type={self.type})>"


class DeliveryLog(Base):
    """投递日志表"""
    __tablename__ = "delivery_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, comment="报告ID")
    batch_no = Column(Integer, default=1, comment="批次号")
    recipients_snapshot = Column(JSON, nullable=True, comment="收件人快照")
    message_id = Column(String(200), nullable=True, comment="邮件消息ID")
    status = Column(SQLEnum(DeliveryStatus, native_enum=True, values_callable=lambda x: [e.value for e in x]), nullable=False, comment="投递状态")
    error_code = Column(String(50), nullable=True, comment="错误代码")
    error_message = Column(Text, nullable=True, comment="错误信息")
    sent_at = Column(DateTime, default=get_local_now_naive, nullable=False, comment="发送时间")
    duration_ms = Column(Integer, default=0, comment="耗时(毫秒)")
    created_at = Column(DateTime, default=get_local_now_naive, nullable=False)

    # 关系
    report = relationship("Report", backref="delivery_logs")

    __table_args__ = (
        Index("idx_delivery_log_report_id", "report_id"),
        Index("idx_delivery_log_sent_at", "sent_at"),
        Index("idx_delivery_log_status", "status"),
    )

    def __repr__(self):
        return f"<DeliveryLog(id={self.id}, report_id={self.report_id}, status={self.status})>"


class ProviderUsage(Base):
    """Provider使用统计表"""
    __tablename__ = "provider_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_name = Column(String(50), nullable=False, comment="Provider名称")
    model_name = Column(String(50), nullable=False, comment="模型名称")
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True, comment="文章ID")
    prompt_tokens = Column(Integer, default=0, comment="输入Token数")
    completion_tokens = Column(Integer, default=0, comment="输出Token数")
    total_tokens = Column(Integer, default=0, comment="总Token数")
    cost = Column(Float, default=0.0, comment="费用")
    created_at = Column(DateTime, default=get_local_now_naive, nullable=False, comment="创建时间")

    # 关系
    article = relationship("Article", backref="provider_usages")

    __table_args__ = (
        Index("idx_provider_usage_provider", "provider_name"),
        Index("idx_provider_usage_article_id", "article_id"),
        Index("idx_provider_usage_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<ProviderUsage(id={self.id}, provider={self.provider_name}, model={self.model_name})>"
