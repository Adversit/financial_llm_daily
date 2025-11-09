"""
抽取相关模型
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .base import Base, TimestampMixin


class QueueStatus(str, enum.Enum):
    """队列状态"""
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Region(str, enum.Enum):
    """区域枚举"""
    DOMESTIC = "国内"
    FOREIGN = "国外"
    UNKNOWN = "未知"


class Layer(str, enum.Enum):
    """层级枚举"""
    FINANCIAL_POLICY = "金融政策监管"
    FINANCIAL_ECONOMY = "金融经济"
    FINTECH_AI = "金融大模型技术"
    FINTECH = "金融科技应用"
    UNKNOWN = "未知"


class ExtractionQueue(Base, TimestampMixin):
    """抽取队列表"""
    __tablename__ = "extraction_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, unique=True, comment="文章ID")
    provider_hint = Column(String(50), nullable=True, comment="Provider提示")
    priority = Column(Integer, default=0, comment="优先级")
    attempts = Column(Integer, default=0, comment="尝试次数")
    status = Column(SQLEnum(QueueStatus, native_enum=True, values_callable=lambda x: [e.value for e in x]), default=QueueStatus.QUEUED, nullable=False, comment="状态")
    last_error = Column(Text, nullable=True, comment="最后错误信息")
    processing_started_at = Column(DateTime, nullable=True, comment="开始处理时间")
    processing_finished_at = Column(DateTime, nullable=True, comment="完成处理时间")

    # 关系
    article = relationship("Article", backref="extraction_queue")

    __table_args__ = (
        Index("idx_extraction_queue_status", "status"),
        Index("idx_extraction_queue_priority", "priority"),
        Index("idx_extraction_queue_article_id", "article_id"),
    )

    def __repr__(self):
        return f"<ExtractionQueue(id={self.id}, article_id={self.article_id}, status={self.status})>"


class ExtractionItem(Base, TimestampMixin):
    """抽取结果表"""
    __tablename__ = "extraction_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, comment="文章ID")
    fact = Column(Text, nullable=False, comment="事实描述")
    opinion = Column(Text, nullable=True, comment="观点描述")
    region = Column(SQLEnum(Region, native_enum=True, values_callable=lambda x: [e.value for e in x]), nullable=False, comment="区域")
    layer = Column(SQLEnum(Layer, native_enum=True, values_callable=lambda x: [e.value for e in x]), nullable=False, comment="层级")
    evidence_span = Column(Text, nullable=True, comment="证据片段")
    confidence = Column(Float, nullable=False, comment="置信度")
    finance_relevance = Column(Float, nullable=True, default=1.0, comment="金融相关性评分(0-1)")

    # 关系
    article = relationship("Article", backref="extraction_items")

    __table_args__ = (
        Index("idx_extraction_items_article_id", "article_id"),
        Index("idx_extraction_items_region_layer", "region", "layer"),
        Index("idx_extraction_items_confidence", "confidence"),
        Index("idx_extraction_items_finance_relevance", "finance_relevance"),
    )

    def __repr__(self):
        return f"<ExtractionItem(id={self.id}, article_id={self.article_id}, region={self.region}, layer={self.layer})>"
