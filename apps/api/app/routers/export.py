"""Data export API routes: CSV download for datasets."""

import csv
import io

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.get("/export/{dataset_slug}")
async def export_dataset(
    request: Request,
    dataset_slug: str,
    geography: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> StreamingResponse:
    """Export all observations for a dataset as CSV download."""
    pool = request.app.state.pool

    async with pool.acquire() as conn:
        # Verify dataset exists
        ds = await conn.fetchrow(
            "SELECT id, name_en FROM datasets WHERE slug = $1", dataset_slug
        )
        if not ds:
            raise HTTPException(status_code=404, detail=f"Dataset '{dataset_slug}' not found")

        # Build query
        conditions = ["i.dataset_id = $1", "o.is_latest = TRUE"]
        params: list = [ds["id"]]
        idx = 2

        if geography:
            conditions.append(f"o.geography_code = ${idx}")
            params.append(geography)
            idx += 1

        if year_from:
            conditions.append(f"o.time_period >= make_date(${idx}, 1, 1)")
            params.append(year_from)
            idx += 1

        if year_to:
            conditions.append(f"o.time_period <= make_date(${idx}, 12, 31)")
            params.append(year_to)
            idx += 1

        where = "WHERE " + " AND ".join(conditions)

        rows = await conn.fetch(f"""
            SELECT
                i.code AS indicator_code,
                i.name_en AS indicator_name,
                i.unit_en AS unit,
                o.geography_code,
                g.name_en AS geography_name,
                o.time_period,
                o.time_precision,
                o.value,
                o.status AS value_status,
                s.name_en AS source
            FROM observations o
            JOIN indicators i ON o.indicator_id = i.id
            JOIN geographies g ON o.geography_code = g.code
            LEFT JOIN source_documents sd ON o.source_document_id = sd.id
            LEFT JOIN sources s ON sd.source_id = s.id
            {where}
            ORDER BY i.code, o.time_period
            LIMIT 500000
        """, *params)

    # Build CSV
    output = io.StringIO()
    output.write("# Data Palestine (datapalestine.org) - Extracted from official sources.\n")
    output.write("# Verify against originals for critical use. Report issues: github.com/datapalestine/data-palestine/issues\n")
    writer = csv.writer(output)
    writer.writerow([
        "indicator_code", "indicator_name", "unit",
        "geography_code", "geography_name",
        "time_period", "time_precision", "value", "value_status", "source",
    ])
    for r in rows:
        writer.writerow([
            r["indicator_code"],
            r["indicator_name"],
            r["unit"],
            r["geography_code"],
            r["geography_name"],
            r["time_period"].isoformat(),
            r["time_precision"],
            float(r["value"]) if r["value"] is not None else "",
            r["value_status"],
            r["source"],
        ])

    output.seek(0)
    filename = f"datapalestine_{dataset_slug}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
