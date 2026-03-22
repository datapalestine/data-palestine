"""Dataset and Category ORM models."""

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Integer, String, Text, Enum, DateTime, Date, ForeignKey,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DatasetStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class UpdateFrequency(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    annual = "annual"
    irregular = "irregular"
    one_time = "one_time"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="category")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(500), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(500), nullable=False)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True
    )
    primary_source_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sources.id"), nullable=True
    )
    status: Mapped[DatasetStatus] = mapped_column(
        Enum(DatasetStatus, name="dataset_status", create_type=False),
        default=DatasetStatus.draft,
    )
    update_frequency: Mapped[UpdateFrequency | None] = mapped_column(
        Enum(UpdateFrequency, name="update_frequency", create_type=False), nullable=True
    )
    temporal_coverage_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    temporal_coverage_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    geographic_coverage: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(20)), nullable=True
    )
    methodology_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    methodology_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    license: Mapped[str] = mapped_column(String(100), default="CC-BY-4.0")
    version: Mapped[int] = mapped_column(Integer, default=1)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String(100)), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    category: Mapped["Category | None"] = relationship(back_populates="datasets")
    indicators: Mapped[list["Indicator"]] = relationship(  # noqa: F821
        back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetSource(Base):
    __tablename__ = "dataset_sources"

    dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("datasets.id"), primary_key=True
    )
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sources.id"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
