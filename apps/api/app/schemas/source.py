"""Source Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


class SourceResponse(BaseModel):
    """Source API response."""

    id: int
    slug: str
    name_en: str
    name_ar: str | None = None
    description_en: str | None = None
    description_ar: str | None = None
    source_type: str
    website_url: str | None = None
    reliability: int | None = None

    model_config = {"from_attributes": True}
