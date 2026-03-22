"""Geography API routes: flat list and hierarchical tree."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


@router.get("/geographies")
async def list_geographies(
    request: Request,
    level: str | None = None,
    parent: str | None = None,
    tree: bool = Query(False),
    lang: Literal["en", "ar"] = Query("en"),
) -> dict:
    """List geographies. Use ?tree=true for nested parent/children structure."""
    pool = request.app.state.pool

    conditions = []
    params = []
    idx = 1

    if level:
        conditions.append(f"level = ${idx}")
        params.append(level)
        idx += 1

    if parent:
        conditions.append(f"parent_code = ${idx}")
        params.append(parent)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    async with pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT code, name_en, name_ar, level, parent_code,
                   latitude, longitude, population, population_year
            FROM geographies
            {where}
            ORDER BY level, name_en
        """, *params)

    name_key = f"name_{lang}" if lang in ("en", "ar") else "name_en"

    items = [
        {
            "code": r["code"],
            "name": r[name_key],
            "level": r["level"],
            "parent_code": r["parent_code"],
            "latitude": float(r["latitude"]) if r["latitude"] else None,
            "longitude": float(r["longitude"]) if r["longitude"] else None,
            "population": r["population"],
            "population_year": r["population_year"],
        }
        for r in rows
    ]

    if tree and not level and not parent:
        # Build nested tree: national -> territories -> governorates
        by_parent: dict[str | None, list] = {}
        by_code: dict[str, dict] = {}
        for item in items:
            by_code[item["code"]] = item
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

    return {"data": items}


@router.get("/geographies/{code}")
async def get_geography(
    request: Request, code: str, lang: str = Query("en")
) -> dict:
    """Get a single geography by code."""
    pool = request.app.state.pool

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM geographies WHERE code = $1", code
        )

    if not row:
        raise HTTPException(status_code=404, detail="Geography not found")

    name_key = f"name_{lang}" if lang in ("en", "ar") else "name_en"

    return {
        "data": {
            "code": row["code"],
            "name": row[name_key],
            "level": row["level"],
            "parent_code": row["parent_code"],
            "latitude": float(row["latitude"]) if row["latitude"] else None,
            "longitude": float(row["longitude"]) if row["longitude"] else None,
            "population": row["population"],
            "population_year": row["population_year"],
        }
    }
