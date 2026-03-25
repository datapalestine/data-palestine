"""Indicator API routes: wired to real PostgreSQL data."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from app.routers import localized
from app.schemas.common import paginate

router = APIRouter()


@router.get("/indicators")
async def list_indicators(
    request: Request,
    dataset: str | None = None,
    category: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    lang: Literal["en", "ar"] = Query("en"),
) -> dict:
    """List indicators with filters. Includes latest_value for each."""
    pool = request.app.state.pool

    conditions = []
    params = []
    idx = 1

    if dataset:
        conditions.append(f"d.slug = ${idx}")
        params.append(dataset)
        idx += 1

    if category:
        conditions.append(f"c.slug = ${idx}")
        params.append(category)
        idx += 1

    if search:
        conditions.append(
            f"(i.name_en ILIKE ${idx} OR i.name_ar ILIKE ${idx} "
            f"OR i.code ILIKE ${idx})"
        )
        params.append(f"%{search}%")
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    async with pool.acquire() as conn:
        count_sql = f"""
            SELECT COUNT(*)
            FROM indicators i
            JOIN datasets d ON i.dataset_id = d.id
            LEFT JOIN categories c ON d.category_id = c.id
            {where}
        """
        total = await conn.fetchval(count_sql, *params)

        data_sql = f"""
            SELECT
                i.id, i.code, i.name_en, i.name_ar,
                i.description_en, i.description_ar,
                i.unit_en, i.unit_ar, i.unit_symbol, i.decimals,
                i.dimensions,
                d.slug AS dataset_slug,
                d.name_en AS dataset_name_en, d.name_ar AS dataset_name_ar,
                latest.value AS latest_value,
                latest.time_period AS latest_time_period,
                latest.geography_code AS latest_geography
            FROM indicators i
            JOIN datasets d ON i.dataset_id = d.id
            LEFT JOIN categories c ON d.category_id = c.id
            LEFT JOIN LATERAL (
                SELECT o.value, o.time_period, o.geography_code
                FROM observations o
                WHERE o.indicator_id = i.id AND o.is_latest = TRUE
                ORDER BY o.time_period DESC
                LIMIT 1
            ) latest ON TRUE
            {where}
            ORDER BY d.name_en, i.sort_order, i.name_en
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        params.extend([per_page, (page - 1) * per_page])
        rows = await conn.fetch(data_sql, *params)

    data = []
    for r in rows:
        item = {
            "id": r["id"],
            "code": r["code"],
            "name": localized(r, "name", lang),
            "description": localized(r, "description", lang),
            "dataset": {
                "slug": r["dataset_slug"],
                "name": localized(r, "dataset_name", lang),
            },
            "unit": localized(r, "unit", lang),
            "unit_symbol": r["unit_symbol"],
            "decimals": r["decimals"],
        }
        if r["latest_value"] is not None:
            item["latest_value"] = {
                "value": float(r["latest_value"]),
                "time_period": r["latest_time_period"].isoformat(),
                "geography": r["latest_geography"],
            }
        else:
            item["latest_value"] = None
        data.append(item)

    return {"data": data, "meta": paginate(total, page, per_page).model_dump()}


@router.get("/indicators/{indicator_id}")
async def get_indicator(
    request: Request, indicator_id: int, lang: str = Query("en")
) -> dict:
    """Get a single indicator by ID."""
    pool = request.app.state.pool

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT i.*, d.slug AS dataset_slug,
                   d.name_en AS dataset_name_en, d.name_ar AS dataset_name_ar
            FROM indicators i
            JOIN datasets d ON i.dataset_id = d.id
            WHERE i.id = $1
        """, indicator_id)

        if not row:
            raise HTTPException(status_code=404, detail="Indicator not found")

    return {
        "data": {
            "id": row["id"],
            "code": row["code"],
            "name": localized(row, "name", lang),
            "description": localized(row, "description", lang),
            "dataset": {
                "slug": row["dataset_slug"],
                "name": localized(row, "dataset_name", lang),
            },
            "unit": localized(row, "unit", lang),
            "unit_symbol": row["unit_symbol"],
            "decimals": row["decimals"],
            "dimensions": row["dimensions"],
        }
    }
