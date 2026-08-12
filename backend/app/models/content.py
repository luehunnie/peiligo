"""contents 表模型：五个内容板块的统一存储。"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # JSONB：板块专属字段，非空，DB 默认空对象
    extra_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    # 时间字段均为 timestamptz，DB 默认 now()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        # 冻结的 content_type 白名单
        CheckConstraint(
            "content_type IN ('campus-story', 'campus-activity', "
            "'learning-resource', 'software-resource', 'college-guide')",
            name="ck_contents_content_type",
        ),
        # 冻结的 status 白名单
        CheckConstraint(
            "status IN ('draft', 'published', 'offline')",
            name="ck_contents_status",
        ),
        Index("ix_contents_content_type", "content_type"),
        Index("ix_contents_status", "status"),
        Index("ix_contents_published_at", "published_at"),
    )
