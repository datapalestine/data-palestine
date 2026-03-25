"""Dataset API routes: wired to real PostgreSQL data."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from app.routers import localized
from app.schemas.common import paginate

router = APIRouter()


@router.get("/datasets")
async def list_datasets(
    request: Request,
    category: str | None = None,
    status: str | None = Query(None),
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=1000),
    sort: str = Query("name"),
    order: Literal["asc", "desc"] = Query("asc"),
    lang: Literal["en", "ar"] = Query("en"),
) -> dict:
    """List all datasets with pagination, search, and category filter."""
    pool = request.app.state.pool

    # Build query
    conditions = []
    params = []
    idx = 1

    if category:
        conditions.append(f"c.slug = ${idx}")
        params.append(category)
        idx += 1

    if status:
        conditions.append(f"d.status = ${idx}")
        params.append(status)
        idx += 1
    else:
        conditions.append("d.status = 'published'")

    if search:
        conditions.append(
            f"(d.name_en ILIKE ${idx} OR d.name_ar ILIKE ${idx} "
            f"OR d.description_en ILIKE ${idx} OR d.description_ar ILIKE ${idx})"
        )
        params.append(f"%{search}%")
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Sort mapping (whitelisted values only, never user input in SQL)
    # Always sort by name_en — name_ar contains unclean data (long English titles, not translations)
    sort_col = {
        "name": "d.name_en",
        "updated": "d.updated_at",
        "created": "d.created_at",
    }.get(sort, "d.name_en")
    order_dir = "ASC" if order == "asc" else "DESC"

    async with pool.acquire() as conn:
        # Count
        count_sql = f"""
            SELECT COUNT(*) FROM datasets d
            LEFT JOIN categories c ON d.category_id = c.id
            {where}
        """
        total = await conn.fetchval(count_sql, *params)

        # Fetch
        data_sql = f"""
            SELECT
                d.id, d.slug,
                d.name_en, d.name_ar,
                d.description_en, d.description_ar,
                d.status, d.update_frequency,
                d.temporal_coverage_start, d.temporal_coverage_end,
                d.license, d.tags, d.featured,
                d.updated_at,
                c.slug AS category_slug,
                c.name_en AS category_name_en,
                c.name_ar AS category_name_ar,
                s.name_en AS source_name,
                s.website_url AS source_url,
                (SELECT COUNT(*) FROM indicators i WHERE i.dataset_id = d.id) AS indicator_count
            FROM datasets d
            LEFT JOIN categories c ON d.category_id = c.id
            LEFT JOIN sources s ON d.primary_source_id = s.id
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
            "slug": r["slug"],
            "name": localized(r, "name", lang),
            "description": localized(r, "description", lang),
            "category": {
                "slug": r["category_slug"],
                "name": localized(r, "category_name", lang),
            } if r["category_slug"] else None,
            "source": {
                "organization": r["source_name"],
                "url": r["source_url"],
            } if r["source_name"] else None,
            "update_frequency": r["update_frequency"],
            "temporal_coverage": {
                "start": r["temporal_coverage_start"].isoformat() if r["temporal_coverage_start"] else None,
                "end": r["temporal_coverage_end"].isoformat() if r["temporal_coverage_end"] else None,
            },
            "indicator_count": r["indicator_count"],
            "tags": r["tags"] or [],
            "featured": r["featured"],
            "last_updated": r["updated_at"].isoformat() if r["updated_at"] else None,
        }
        data.append(item)

    return {"data": data, "meta": paginate(total, page, per_page).model_dump()}


@router.get("/datasets/{slug}")
async def get_dataset(request: Request, slug: str, lang: Literal["en", "ar"] = Query("en")) -> dict:
    """Get a single dataset with its metadata, source info, and indicators."""
    pool = request.app.state.pool

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                d.*,
                c.slug AS category_slug,
                c.name_en AS category_name_en, c.name_ar AS category_name_ar,
                s.slug AS source_slug, s.name_en AS source_name_en,
                s.name_ar AS source_name_ar, s.website_url AS source_url
            FROM datasets d
            LEFT JOIN categories c ON d.category_id = c.id
            LEFT JOIN sources s ON d.primary_source_id = s.id
            WHERE d.slug = $1
        """, slug)

        if not row:
            raise HTTPException(status_code=404, detail=f"No dataset with slug '{slug}' exists")

        # Get indicators for this dataset
        indicators = await conn.fetch("""
            SELECT i.id, i.code, i.name_en, i.name_ar,
                   i.unit_en, i.unit_ar, i.unit_symbol, i.decimals
            FROM indicators i
            WHERE i.dataset_id = $1
            ORDER BY i.sort_order, i.name_en
        """, row["id"])

    data = {
        "id": row["id"],
        "slug": row["slug"],
        "name": localized(row, "name", lang),
        "description": localized(row, "description", lang),
        "category": {
            "slug": row["category_slug"],
            "name": localized(row, "category_name", lang),
        } if row["category_slug"] else None,
        "source": {
            "organization": localized(row, "source_name", lang),
            "url": row["source_url"],
        } if row["source_name_en"] else None,
        "update_frequency": row["update_frequency"],
        "temporal_coverage": {
            "start": row["temporal_coverage_start"].isoformat() if row["temporal_coverage_start"] else None,
            "end": row["temporal_coverage_end"].isoformat() if row["temporal_coverage_end"] else None,
        },
        "methodology": localized(row, "methodology", lang),
        "license": row["license"],
        "version": row["version"],
        "tags": row["tags"] or [],
        "featured": row["featured"],
        "last_updated": row["updated_at"].isoformat() if row["updated_at"] else None,
        "indicators": [
            {
                "id": i["id"],
                "code": i["code"],
                "name": localized(i, "name", lang),
                "unit": localized(i, "unit", lang),
                "unit_symbol": i["unit_symbol"],
                "decimals": i["decimals"],
            }
            for i in indicators
        ],
    }

    return {"data": data}


@router.get("/datasets/{slug}/geographies")
async def get_dataset_geographies(
    request: Request, slug: str, lang: Literal["en", "ar"] = Query("en")
) -> dict:
    """Return geographies that have observations in this dataset, as a tree."""
    pool = request.app.state.pool

    async with pool.acquire() as conn:
        # Get dataset ID
        ds = await conn.fetchrow("SELECT id FROM datasets WHERE slug = $1", slug)
        if not ds:
            raise HTTPException(status_code=404, detail=f"Dataset '{slug}' not found")

        # Find distinct geography codes that have observations in this dataset
        rows = await conn.fetch("""
            SELECT DISTINCT g.code, g.name_en, g.name_ar, g.level, g.parent_code
            FROM observations o
            JOIN indicators i ON o.indicator_id = i.id
            JOIN geographies g ON o.geography_code = g.code
            WHERE i.dataset_id = $1 AND o.is_latest = TRUE
            ORDER BY g.level, g.name_en
        """, ds["id"])

    # Build a set of codes that have data
    data_codes = {r["code"] for r in rows}

    if not data_codes:
        return {"data": []}

    # Walk up the parent chain from the DB to build a connected tree
    all_codes = set(data_codes)
    async with pool.acquire() as conn:
        # Recursively find all ancestors
        ancestors = await conn.fetch("""
            WITH RECURSIVE ancestors AS (
                SELECT code, parent_code FROM geographies WHERE code = ANY($1::text[])
                UNION
                SELECT g.code, g.parent_code FROM geographies g
                JOIN ancestors a ON g.code = a.parent_code
            )
            SELECT code FROM ancestors
        """, list(data_codes))
        for a in ancestors:
            all_codes.add(a["code"])

        geo_rows = await conn.fetch("""
            SELECT code, name_en, name_ar, level, parent_code
            FROM geographies
            WHERE code = ANY($1::text[])
            ORDER BY level, name_en
        """, list(all_codes))

    # Build tree
    items = [
        {
            "code": r["code"],
            "name": localized(r, "name", lang),
            "level": r["level"],
            "parent_code": r["parent_code"],
            "has_data": r["code"] in data_codes,
        }
        for r in geo_rows
    ]

    by_parent: dict[str | None, list] = {}
    for item in items:
        by_parent.setdefault(item["parent_code"], []).append(item)

    def build_children(code: str) -> list:
        children = by_parent.get(code, [])
        for child in children:
            child["children"] = build_children(child["code"])
        return children

    roots = by_parent.get(None, [])
    for root in roots:
        root["children"] = build_children(root["code"])

    return {"data": roots}
