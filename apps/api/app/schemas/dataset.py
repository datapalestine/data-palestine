"""Dataset Pydantic schemas."""

from datetime import date, datetime

from pydantic import BaseModel


class DatasetResponse(BaseModel):
    """Dataset API response."""

    id: int
    slug: str
    name_en: str
    name_ar: str
    description_en: str | None = None
    description_ar: str | None = None
    status: str
    update_frequency: str | None = None
    temporal_coverage_start: date | None = None
    temporal_coverage_end: date | None = None
    geographic_coverage: list[str] | None = None
    methodology_en: str | None = None
    methodology_ar: str | None = None
    license: str
    version: int
    tags: list[str] | None = None
    featured: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
