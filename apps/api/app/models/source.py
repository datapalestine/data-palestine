"""Source and SourceDocument ORM models."""

import enum
from datetime import date, datetime

from sqlalchemy import Integer, String, Text, SmallInteger, Enum, DateTime, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SourceType(str, enum.Enum):
    government = "government"
    international_org = "international_org"
    ngo = "ngo"
    academic = "academic"
    media = "media"
    other = "other"


class FileType(str, enum.Enum):
    pdf = "pdf"
    excel = "excel"
    csv = "csv"
    html = "html"
    json = "json"
    api = "api"
    other = "other"


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type", create_type=False), nullable=False
    )
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    methodology_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    methodology_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    reliability: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    documents: Mapped[list["SourceDocument"]] = relationship(back_populates="source")


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title_ar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    archive_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_type: Mapped[FileType] = mapped_column(
        Enum(FileType, name="file_type", create_type=False), nullable=False
    )
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    access_date: Mapped[date] = mapped_column(Date, nullable=False)
    page_numbers: Mapped[str | None] = mapped_column(String(50), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    source: Mapped["Source"] = relationship(back_populates="documents")
