"""Observation Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ObservationResponse(BaseModel):
    """Observation API response."""

    id: int
    indicator_id: int
    geography_code: str
    time_period: date
    time_precision: str
    value: Decimal | None = None
    value_text: str | None = None
    dimensions: dict = {}
    status: str
    notes_en: str | None = None
    notes_ar: str | None = None
    data_version: int = 1

    model_config = {"from_attributes": True}
