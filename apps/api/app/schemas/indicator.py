"""Indicator Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


class IndicatorResponse(BaseModel):
    """Indicator API response."""

    id: int
    dataset_id: int
    code: str
    name_en: str
    name_ar: str
    description_en: str | None = None
    description_ar: str | None = None
    unit_en: str | None = None
    unit_ar: str | None = None
    unit_symbol: str | None = None
    decimals: int = 2
    dimensions: dict = {}
    sdg_indicator: str | None = None

    model_config = {"from_attributes": True}
