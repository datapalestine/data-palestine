"""Curation API routes: review queue, submissions, and admin approval workflow."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.config import settings
from app.routers import localized
from app.schemas.common import paginate

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_admin(request: Request) -> None:
    """Check Authorization header for admin bearer token. Raises 401 on failure."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth.removeprefix("Bearer ").strip()
    if token != settings.admin_secret_key:
        raise HTTPException(status_code=401, detail="Invalid admin secret key")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class CurationSubmission(BaseModel):
    dataset_id: int
    reviewer_name: str
    reviewer_email: str
    changes: dict  # JSONB
    notes: str | None = None


class RejectBody(BaseModel):
    reason: str


# ---------------------------------------------------------------------------
# 1. GET /curation/queue
# ---------------------------------------------------------------------------

@router.get("/curation/queue")
async def curation_queue(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    lang: Literal["en", "ar"] = Query("en"),
) -> dict:
    """Datasets needing review, ordered by observation count descending."""
    pool = request.app.state.pool

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM datasets WHERE quality_status = 'needs_review'"
        )

        rows = await conn.fetch("""
            SELECT
                d.id,
                d.name_en, d.name_ar,
                c.name_en AS category_name_en,
                c.name_ar AS category_name_ar,
                (SELECT COUNT(*) FROM indicators i WHERE i.dataset_id = d.id) AS indicator_count,
                (SELECT COUNT(*) FROM observations o
                    JOIN indicators i2 ON o.indicator_id = i2.id
                    WHERE i2.dataset_id = d.id) AS observation_count
            FROM datasets d
            LEFT JOIN categories c ON d.category_id = c.id
            WHERE d.quality_status = 'needs_review'
            ORDER BY observation_count DESC
            LIMIT $1 OFFSET $2
        """, per_page, (page - 1) * per_page)

        # For each dataset, grab the first 5 indicator names
        data = []
        for r in rows:
            sample_indicators = await conn.fetch("""
                SELECT name_en FROM indicators
                WHERE dataset_id = $1
                ORDER BY sort_order, name_en
                LIMIT 5
            """, r["id"])

            data.append({
                "id": r["id"],
                "name": localized(r, "name", lang),
                "category_name": localized(r, "category_name", lang),
                "indicator_count": r["indicator_count"],
                "observation_count": r["observation_count"],
                "sample_indicators": [si["name_en"] for si in sample_indicators],
            })

    return {"data": data, "meta": paginate(total, page, per_page).model_dump()}


# ---------------------------------------------------------------------------
# 2. GET /curation/dataset/{dataset_id}
# ---------------------------------------------------------------------------

@router.get("/curation/dataset/{dataset_id}")
async def curation_dataset_detail(
    request: Request,
    dataset_id: int,
    lang: Literal["en", "ar"] = Query("en"),
) -> dict:
    """Full curation detail for a single dataset."""
    pool = request.app.state.pool

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                d.id, d.slug, d.name_en, d.name_ar,
                d.description_en, d.description_ar,
                d.quality_status,
                c.slug AS category_slug,
                c.name_en AS category_name_en,
                c.name_ar AS category_name_ar,
                s.name_en AS source_name_en,
                s.name_ar AS source_name_ar,
                s.website_url AS source_url
            FROM datasets d
            LEFT JOIN categories c ON d.category_id = c.id
            LEFT JOIN sources s ON d.primary_source_id = s.id
            WHERE d.id = $1
        """, dataset_id)

        if not row:
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")

        # All indicators with observation counts
        indicators = await conn.fetch("""
            SELECT
                i.id, i.name_en, i.code,
                (SELECT COUNT(*) FROM observations o WHERE o.indicator_id = i.id) AS observation_count
            FROM indicators i
            WHERE i.dataset_id = $1
            ORDER BY i.sort_order, i.name_en
        """, dataset_id)

        # 10 sample observations
        sample_obs = await conn.fetch("""
            SELECT
                o.value, o.time_period,
                o.geography_code,
                i.name_en AS indicator_name_en
            FROM observations o
            JOIN indicators i ON o.indicator_id = i.id
            WHERE i.dataset_id = $1
            ORDER BY o.created_at DESC
            LIMIT 10
        """, dataset_id)

    data = {
        "dataset": {
            "id": row["id"],
            "name_en": row["name_en"],
            "name_ar": row["name_ar"],
            "description_en": row["description_en"],
            "description_ar": row["description_ar"],
            "slug": row["slug"],
            "quality_status": row["quality_status"],
        },
        "category": {
            "slug": row["category_slug"],
            "name": localized(row, "category_name", lang),
        } if row["category_slug"] else None,
        "source": {
            "name": localized(row, "source_name", lang),
            "url": row["source_url"],
        } if row["source_name_en"] else None,
        "indicators": [
            {
                "id": i["id"],
                "name_en": i["name_en"],
                "code": i["code"],
                "observation_count": i["observation_count"],
            }
            for i in indicators
        ],
        "sample_observations": [
            {
                "value": float(o["value"]) if o["value"] is not None else None,
                "time_period": o["time_period"],
                "geography_code": o["geography_code"],
                "indicator_name": o["indicator_name_en"],
            }
            for o in sample_obs
        ],
    }

    return {"data": data}


# ---------------------------------------------------------------------------
# 3. POST /curation/submit
# ---------------------------------------------------------------------------

@router.post("/curation/submit")
async def submit_curation_review(request: Request, body: CurationSubmission) -> dict:
    """Submit a curation review for a dataset. No auth required."""
    pool = request.app.state.pool

    async with pool.acquire() as conn:
        # Verify dataset exists
        ds = await conn.fetchrow("SELECT id FROM datasets WHERE id = $1", body.dataset_id)
        if not ds:
            raise HTTPException(status_code=404, detail=f"Dataset {body.dataset_id} not found")

        import json
        review_id = await conn.fetchval("""
            INSERT INTO curation_reviews
                (dataset_id, reviewer_name, reviewer_email, changes, notes, status, created_at)
            VALUES ($1, $2, $3, $4::jsonb, $5, 'pending', NOW())
            RETURNING id
        """, body.dataset_id, body.reviewer_name, body.reviewer_email,
            json.dumps(body.changes), body.notes)

    return {"data": {"id": review_id}, "message": "Review submitted successfully"}


# ---------------------------------------------------------------------------
# 4. GET /curation/reviews
# ---------------------------------------------------------------------------

@router.get("/curation/reviews")
async def list_reviews(
    request: Request,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict:
    """List curation reviews. Requires admin auth."""
    _require_admin(request)
    pool = request.app.state.pool

    conditions = []
    params: list = []
    idx = 1

    if status:
        conditions.append(f"cr.status = ${idx}")
        params.append(status)
        idx += 1
    else:
        conditions.append("cr.status = 'pending'")

    where = "WHERE " + " AND ".join(conditions)

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM curation_reviews cr {where}", *params
        )

        rows = await conn.fetch(f"""
            SELECT
                cr.id, cr.dataset_id, cr.reviewer_name,
                cr.status, cr.changes, cr.created_at,
                d.name_en AS dataset_name
            FROM curation_reviews cr
            JOIN datasets d ON cr.dataset_id = d.id
            {where}
            ORDER BY cr.created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """, *params, per_page, (page - 1) * per_page)

    import json

    data = []
    for r in rows:
        changes = r["changes"] if isinstance(r["changes"], dict) else json.loads(r["changes"]) if r["changes"] else {}
        indicator_changes = changes.get("indicators", [])
        data.append({
            "id": r["id"],
            "dataset_id": r["dataset_id"],
            "dataset_name": r["dataset_name"],
            "reviewer_name": r["reviewer_name"],
            "status": r["status"],
            "changes_summary": {
                "indicator_changes": len(indicator_changes),
            },
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })

    return {"data": data, "meta": paginate(total, page, per_page).model_dump()}


# ---------------------------------------------------------------------------
# 5. GET /curation/reviews/{review_id}
# ---------------------------------------------------------------------------

@router.get("/curation/reviews/{review_id}")
async def get_review(request: Request, review_id: int) -> dict:
    """Get a single review with full detail. Requires admin auth."""
    _require_admin(request)
    pool = request.app.state.pool

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                cr.*,
                d.name_en AS dataset_name,
                d.slug AS dataset_slug
            FROM curation_reviews cr
            JOIN datasets d ON cr.dataset_id = d.id
            WHERE cr.id = $1
        """, review_id)

    if not row:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

    import json
    changes = row["changes"] if isinstance(row["changes"], dict) else json.loads(row["changes"]) if row["changes"] else {}

    data = {
        "id": row["id"],
        "dataset_id": row["dataset_id"],
        "dataset_name": row["dataset_name"],
        "dataset_slug": row["dataset_slug"],
        "reviewer_name": row["reviewer_name"],
        "reviewer_email": row["reviewer_email"],
        "status": row["status"],
        "changes": changes,
        "notes": row["notes"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "reviewed_at": row["reviewed_at"].isoformat() if row.get("reviewed_at") else None,
    }

    return {"data": data}


# ---------------------------------------------------------------------------
# 6. POST /curation/approve/{review_id}
# ---------------------------------------------------------------------------

@router.post("/curation/approve/{review_id}")
async def approve_review(request: Request, review_id: int) -> dict:
    """Apply changes from a review and mark dataset as approved. Requires admin auth."""
    _require_admin(request)
    pool = request.app.state.pool

    import json

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM curation_reviews WHERE id = $1", review_id
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
        if row["status"] != "pending":
            raise HTTPException(status_code=400, detail=f"Review is already {row['status']}")

        changes = row["changes"] if isinstance(row["changes"], dict) else json.loads(row["changes"]) if row["changes"] else {}
        dataset_id = row["dataset_id"]
        changes_applied = 0

        async with conn.transaction():
            # --- Dataset-level changes ---
            ds_updates = {}
            for field in ("name_en", "name_ar", "description_en", "description_ar"):
                if field in changes:
                    ds_updates[field] = changes[field]

            if ds_updates:
                set_clauses = []
                params = []
                idx = 1
                for col, val in ds_updates.items():
                    set_clauses.append(f"{col} = ${idx}")
                    params.append(val)
                    idx += 1
                params.append(dataset_id)
                await conn.execute(
                    f"UPDATE datasets SET {', '.join(set_clauses)} WHERE id = ${idx}",
                    *params,
                )
                changes_applied += len(ds_updates)

            # Category change (by slug)
            if "category_slug" in changes:
                cat = await conn.fetchrow(
                    "SELECT id FROM categories WHERE slug = $1",
                    changes["category_slug"],
                )
                if cat:
                    await conn.execute(
                        "UPDATE datasets SET category_id = $1 WHERE id = $2",
                        cat["id"], dataset_id,
                    )
                    changes_applied += 1

            # --- Indicator-level changes ---
            for ind_change in changes.get("indicators", []):
                action = ind_change.get("action")
                indicator_id = ind_change.get("indicator_id")

                if not action or not indicator_id:
                    continue

                if action == "rename":
                    new_name_en = ind_change.get("new_name_en")
                    new_name_ar = ind_change.get("new_name_ar")
                    if new_name_en:
                        await conn.execute(
                            "UPDATE indicators SET name_en = $1 WHERE id = $2",
                            new_name_en, indicator_id,
                        )
                    if new_name_ar:
                        await conn.execute(
                            "UPDATE indicators SET name_ar = $1 WHERE id = $2",
                            new_name_ar, indicator_id,
                        )
                    changes_applied += 1

                elif action == "delete":
                    await conn.execute(
                        "DELETE FROM observations WHERE indicator_id = $1",
                        indicator_id,
                    )
                    await conn.execute(
                        "DELETE FROM indicators WHERE id = $1",
                        indicator_id,
                    )
                    changes_applied += 1

                elif action == "merge_into":
                    target_id = ind_change.get("target_indicator_id")
                    if not target_id:
                        continue
                    await conn.execute(
                        "UPDATE observations SET indicator_id = $1 WHERE indicator_id = $2",
                        target_id, indicator_id,
                    )
                    await conn.execute(
                        "DELETE FROM indicators WHERE id = $1",
                        indicator_id,
                    )
                    changes_applied += 1

                elif action == "keep":
                    # Optionally rename
                    new_name_en = ind_change.get("new_name_en")
                    new_name_ar = ind_change.get("new_name_ar")
                    if new_name_en:
                        await conn.execute(
                            "UPDATE indicators SET name_en = $1 WHERE id = $2",
                            new_name_en, indicator_id,
                        )
                        changes_applied += 1
                    if new_name_ar:
                        await conn.execute(
                            "UPDATE indicators SET name_ar = $1 WHERE id = $2",
                            new_name_ar, indicator_id,
                        )
                        changes_applied += 1

            # Mark dataset as approved
            await conn.execute(
                "UPDATE datasets SET quality_status = 'approved' WHERE id = $1",
                dataset_id,
            )

            # Mark review as approved
            await conn.execute(
                "UPDATE curation_reviews SET status = 'approved', reviewed_at = NOW() WHERE id = $1",
                review_id,
            )

    return {
        "data": {
            "review_id": review_id,
            "dataset_id": dataset_id,
            "status": "approved",
            "changes_applied": changes_applied,
        },
        "message": "Review approved and changes applied successfully",
    }


# ---------------------------------------------------------------------------
# 7. POST /curation/reject/{review_id}
# ---------------------------------------------------------------------------

@router.post("/curation/reject/{review_id}")
async def reject_review(request: Request, review_id: int, body: RejectBody) -> dict:
    """Reject a curation review. Requires admin auth."""
    _require_admin(request)
    pool = request.app.state.pool

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, status FROM curation_reviews WHERE id = $1", review_id
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
        if row["status"] != "pending":
            raise HTTPException(status_code=400, detail=f"Review is already {row['status']}")

        await conn.execute("""
            UPDATE curation_reviews
            SET status = 'rejected', reject_reason = $1, reviewed_at = NOW()
            WHERE id = $2
        """, body.reason, review_id)

    return {
        "data": {
            "review_id": review_id,
            "status": "rejected",
        },
        "message": "Review rejected",
    }
