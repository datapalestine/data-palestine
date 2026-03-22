"""Pagination utilities."""

import math


def calculate_pagination(total: int, page: int, per_page: int) -> dict:
    """Calculate pagination metadata."""
    total_pages = max(1, math.ceil(total / per_page))
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
