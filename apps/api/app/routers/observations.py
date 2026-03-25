"""Observation API routes: the main data query endpoint."""

from typing import Literal

from fastapi import APIRouter, Query, Request

from app.routers import localized
from app.schemas.common import paginate

router = APIRouter()


@router.get("/observations")
async def list_observations(
    request: Request,
    indicator: str | None = None,
    dataset: str | None = None,
    geography: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    time_precision: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=1000),
    sort: str = Query("time"),
    order: Literal["asc", "desc"] = Query("desc"),
    lang: Literal["en", "ar"] = Query("en"),
) -> dict:
    """Query observations with multi-dimensional filtering.

    Supports filtering by indicator, dataset, geography (comma-separated),
    year range, and time precision.
    """
    pool = request.app.state.pool

    conditions = ["o.is_latest = TRUE"]
    params = []
    idx = 1

    if indicator:
        ids = [int(x.strip()) for x in indicator.split(",") if x.strip().isdigit()]
        if len(ids) == 1:
            conditions.append(f"o.indicator_id = ${idx}")
            params.append(ids[0])
            idx += 1
        elif len(ids) > 1:
            placeholders = ", ".join(f"${idx + j}" for j in range(len(ids)))
            conditions.append(f"o.indicator_id IN ({placeholders})")
            params.extend(ids)
            idx += len(ids)

    if dataset:
        conditions.append(f"d.slug = ${idx}")
        params.append(dataset)
        idx += 1

    if geography:
        codes = [c.strip() for c in geography.split(",") if c.strip()]
        if len(codes) == 1:
            conditions.append(f"o.geography_code = ${idx}")
            params.append(codes[0])
            idx += 1
        elif len(codes) > 1:
            placeholders = ", ".join(f"${idx + j}" for j in range(len(codes)))
            conditions.append(f"o.geography_code IN ({placeholders})")
            params.extend(codes)
            idx += len(codes)

    if year_from:
        conditions.append(f"o.time_period >= make_date(${idx}, 1, 1)")
        params.append(year_from)
        idx += 1

    if year_to:
        conditions.append(f"o.time_period <= make_date(${idx}, 12, 31)")
        params.append(year_to)
        idx += 1

    if time_precision:
        conditions.append(f"o.time_precision = ${idx}")
        params.append(time_precision)
        idx += 1

    where = "WHERE " + " AND ".join(conditions)

    sort_col = {
        "time": "o.time_period",
        "value": "o.value",
        "geography": "o.geography_code",
    }.get(sort, "o.time_period")
    order_dir = "ASC" if order == "asc" else "DESC"

    async with pool.acquire() as conn:
        count_sql = f"""
            SELECT COUNT(*)
            FROM observations o
            JOIN indicators i ON o.indicator_id = i.id
            JOIN datasets d ON i.dataset_id = d.id
            {where}
        """
        total = await conn.fetchval(count_sql, *params)

        data_sql = f"""
            SELECT
                o.id, o.value, o.time_period, o.time_precision, o.status,
                o.dimensions, o.notes_en, o.notes_ar,
                i.id AS indicator_id, i.code AS indicator_code,
                i.name_en AS indicator_name_en, i.name_ar AS indicator_name_ar,
                i.unit_symbol,
                g.code AS geo_code, g.name_en AS geo_name_en, g.name_ar AS geo_name_ar,
                s.name_en AS source_name, sd.document_url AS source_url
            FROM observations o
            JOIN indicators i ON o.indicator_id = i.id
            JOIN datasets d ON i.dataset_id = d.id
            JOIN geographies g ON o.geography_code = g.code
            LEFT JOIN source_documents sd ON o.source_document_id = sd.id
            LEFT JOIN sources s ON sd.source_id = s.id
            {where}
            ORDER BY {sort_col} {order_dir}
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        params.extend([per_page, (page - 1) * per_page])
        rows = await conn.fetch(data_sql, *params)

    data = []
    for r in rows:
        item = {
            "id": r["id"],
            "indicator": {
                "id": r["indicator_id"],
                "code": r["indicator_code"],
                "name": localized(r, "indicator_name", lang),
            },
            "geography": {
                "code": r["geo_code"],
                "name": localized(r, "geo_name", lang),
            },
            "time_period": r["time_period"].isoformat(),
            "time_precision": r["time_precision"],
            "value": float(r["value"]) if r["value"] is not None else None,
            "unit_symbol": r["unit_symbol"],
            "value_status": r["status"],
            "source": {
                "organization": r["source_name"],
                "url": r["source_url"],
            } if r["source_name"] else None,
        }
        data.append(item)

    return {"data": data, "meta": paginate(total, page, per_page).model_dump()}
