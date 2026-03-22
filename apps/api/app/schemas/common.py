"""Common schemas matching docs/API_REFERENCE.md envelope format."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated API response: { data: [...], meta: {...} }"""

    data: list[T]
    meta: PaginationMeta


class SingleResponse(BaseModel, Generic[T]):
    """Single resource response: { data: {...} }"""

    data: T


class ErrorDetail(BaseModel):
    """Error detail object."""

    code: str
    message: str
    detail: str | None = None


class ErrorResponse(BaseModel):
    """Error response: { error: {...} }"""

    error: ErrorDetail


def paginate(total: int, page: int, per_page: int) -> PaginationMeta:
    """Build pagination meta."""
    total_pages = max(1, (total + per_page - 1) // per_page)
    return PaginationMeta(total=total, page=page, per_page=per_page, total_pages=total_pages)
