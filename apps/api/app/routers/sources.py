"""Source API routes: uses asyncpg pool like all other routers."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


@router.get("/sources")
async def list_sources(
    request: Request,
    lang: Literal["en", "ar"] = Query("en"),
) -> dict:
    """List all data sources."""
    pool = request.app.state.pool

    name_key = "name_en" if lang == "en" else "name_ar"

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, slug, name_en, name_ar, description_en, description_ar,
                   source_type, website_url, reliability
            FROM sources ORDER BY name_en
        """)

    data = [
        {
            "id": r["id"],
            "slug": r["slug"],
            "name": r[name_key] or r["name_en"],
            "description": r[f"description_{lang}"] or r["description_en"],
            "type": r["source_type"],
            "website": r["website_url"],
            "reliability": r["reliability"],
        }
        for r in rows
    ]

    return {"data": data}


@router.get("/sources/{source_id}")
async def get_source(
    request: Request,
    source_id: int,
    lang: Literal["en", "ar"] = Query("en"),
) -> dict:
    """Get a single source by ID."""
    pool = request.app.state.pool

    name_key = "name_en" if lang == "en" else "name_ar"

    async with pool.acquire() as conn:
        r = await conn.fetchrow(
            "SELECT * FROM sources WHERE id = $1", source_id
        )

    if not r:
        raise HTTPException(status_code=404, detail="Source not found")

    return {
        "data": {
            "id": r["id"],
            "slug": r["slug"],
            "name": r[name_key] or r["name_en"],
            "description": r[f"description_{lang}"] or r["description_en"],
            "type": r["source_type"],
            "website": r["website_url"],
            "reliability": r["reliability"],
        }
    }
