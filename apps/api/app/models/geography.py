"""Geography ORM model."""

import enum
from datetime import datetime

from sqlalchemy import Integer, SmallInteger, String, Numeric, Enum, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GeographyLevel(str, enum.Enum):
    national = "national"
    territory = "territory"
    governorate = "governorate"
    locality = "locality"


class Geography(Base):
    __tablename__ = "geographies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[GeographyLevel] = mapped_column(
        Enum(GeographyLevel, name="geography_level", create_type=False), nullable=False
    )
    parent_code: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    pcbs_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    iso_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    population_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    observations: Mapped[list["Observation"]] = relationship(  # noqa: F821
        back_populates="geography", foreign_keys="Observation.geography_code",
        primaryjoin="Geography.code == foreign(Observation.geography_code)",
    )
