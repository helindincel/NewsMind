from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ArticleModel(Base):
    __tablename__ = "articles"

    id = Column(String(36), primary_key=True)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    content = Column(Text)
    image_url = Column(Text)
    source = Column(String(255))
    keyword = Column(String(100))
    published_at = Column(DateTime(timezone=True), nullable=False)
    fetched_at = Column(DateTime(timezone=True), default=_now)

    summaries = relationship(
        "SummaryModel", back_populates="article", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("url", name="uq_articles_url"),
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_keyword", "keyword"),
    )


class SummaryModel(Base):
    __tablename__ = "summaries"

    id = Column(String(36), primary_key=True)
    article_id = Column(
        String(36), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    model_version = Column(String(255), nullable=False)
    summary_text = Column(Text)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), default=_now)
    duration_ms = Column(Integer)
    error = Column(Text)

    article = relationship("ArticleModel", back_populates="summaries")

    __table_args__ = (
        UniqueConstraint(
            "article_id", "model_version", name="uq_summaries_article_model"
        ),
        Index("ix_summaries_status", "status"),
    )


class SearchQueryModel(Base):
    __tablename__ = "search_queries"

    id = Column(String(36), primary_key=True)
    keyword = Column(String(100), nullable=False)
    result_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=_now)

    __table_args__ = (Index("ix_search_queries_keyword", "keyword"),)
