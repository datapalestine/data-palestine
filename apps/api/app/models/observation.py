"""Observation and PipelineRun ORM models."""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, Integer, String, Text, Numeric, Enum, DateTime, Date, ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ObservationStatus(str, enum.Enum):
    preliminary = "preliminary"
    revised = "revised"
    final = "final"


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    indicator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("indicators.id", ondelete="CASCADE"), nullable=False
    )
    geography_code: Mapped[str] = mapped_column(String(20), nullable=False)
    time_period: Mapped[date] = mapped_column(Date, nullable=False)
    time_precision: Mapped[str] = mapped_column(String(20), default="annual")
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dimensions: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[ObservationStatus] = mapped_column(
        Enum(ObservationStatus, name="observation_status", create_type=False),
        default=ObservationStatus.final,
    )
    source_document_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("source_documents.id"), nullable=True
    )
    notes_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_version: Mapped[int] = mapped_column(Integer, default=1)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    indicator: Mapped["Indicator"] = relationship(back_populates="observations")  # noqa: F821
    geography: Mapped["Geography"] = relationship(  # noqa: F821
        back_populates="observations",
        foreign_keys=[geography_code],
        primaryjoin="Observation.geography_code == Geography.code",
    )


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pipeline_name: Mapped[str] = mapped_column(String(200), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="running")
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
