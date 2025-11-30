"""
报告相关模型
"""
from sqlalchemy import Column, Integer, String, Text, Date, JSON, DateTime, Index
from datetime import datetime
from .base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    """报告表"""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(Date, nullable=False, unique=True, comment="报告日期")
    version = Column(String(20), default="1.0", comment="版本号")
    overview_summary = Column(Text, nullable=True, comment="总览摘要")
    sections_json = Column(JSON, nullable=True, comment="分区统计JSON")
    html_body = Column(Text, nullable=False, comment="邮件正文HTML")
    html_attachment = Column(Text, nullable=False, comment="附件HTML")
    build_meta = Column(JSON, nullable=True, comment="构建元数据")
    build_ms = Column(Integer, default=0, comment="构建耗时(毫秒)")

    __table_args__ = (
        Index("idx_reports_date", "report_date"),
    )

    def __repr__(self):
        return f"<Report(id={self.id}, date={self.report_date})>"
