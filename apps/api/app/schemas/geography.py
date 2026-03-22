"""Geography Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


class GeographyBase(BaseModel):
    """Base geography schema."""

    code: str
    name_en: str
    name_ar: str
    level: str
    parent_code: str | None = None


class GeographyResponse(GeographyBase):
    """Geography API response."""

    id: int
    pcbs_code: str | None = None
    iso_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    population: int | None = None
    population_year: int | None = None

    model_config = {"from_attributes": True}
