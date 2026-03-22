"""Indicator ORM model."""

from datetime import datetime

from sqlalchemy import Integer, SmallInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Indicator(Base):
    __tablename__ = "indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(500), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(500), nullable=False)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_en: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit_ar: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decimals: Mapped[int] = mapped_column(SmallInteger, default=2)
    dimensions: Mapped[dict] = mapped_column(JSONB, default=dict)
    sdg_indicator: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    dataset: Mapped["Dataset"] = relationship(back_populates="indicators")  # noqa: F821
    observations: Mapped[list["Observation"]] = relationship(  # noqa: F821
        back_populates="indicator", cascade="all, delete-orphan"
    )
