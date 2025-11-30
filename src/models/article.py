"""
文章模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, ForeignKey, Enum as SQLEnum, Index, JSON
from sqlalchemy.orm import relationship
import enum
from .base import Base, TimestampMixin
from src.utils.time_utils import get_local_now_naive


class ProcessingStatus(str, enum.Enum):
    """处理状态"""
    RAW = "raw"
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    PARTIAL = "partial"


class Article(Base, TimestampMixin):
    """文章表"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, comment="信息源ID")
    title = Column(String(500), nullable=False, comment="文章标题")
    url = Column(String(1000), nullable=False, unique=True, comment="文章URL")
    published_at = Column(DateTime, nullable=True, comment="发布时间")
    fetched_at = Column(DateTime, default=get_local_now_naive, nullable=False, comment="采集时间")
    content_text = Column(Text, nullable=True, comment="文章正文")
    content_len = Column(Integer, default=0, comment="正文长度")
    section = Column(String(100), nullable=True, comment="文章分类")
    region_tag = Column(String(20), nullable=True, comment="区域标签:国内/国外/未知")
    lang = Column(String(10), default="zh", comment="语言")
    simhash = Column(BigInteger, nullable=True, comment="SimHash指纹")
    canonical_url = Column(String(1000), nullable=True, comment="规范化URL")
    dedup_key = Column(String(200), nullable=True, comment="去重键")
    processing_status = Column(
        SQLEnum(ProcessingStatus, native_enum=True, values_callable=lambda x: [e.value for e in x]),
        default=ProcessingStatus.RAW,
        nullable=False,
        comment="处理状态"
    )
    keywords = Column(JSON, nullable=True, comment="文章关键词(3-5个名词,LLM提取)")

    # 关系
    source = relationship("Source", backref="articles")

    __table_args__ = (
        Index("idx_articles_url", "url"),
        Index("idx_articles_published_at", "published_at"),
        Index("idx_articles_processing_status", "processing_status"),
        Index("idx_articles_simhash", "simhash"),
    )

    def __repr__(self):
        return f"<Article(id={self.id}, title={self.title[:30]}, status={self.processing_status})>"
