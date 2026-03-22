"""Ingest parsed XLSX data into the database."""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

from packages.pipeline.pcbs.xlsx_parser import parse_xlsx, ParsedSheet

logger = logging.getLogger(__name__)

import os
DB_URL = os.environ.get("DATABASE_URL", "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine")


def slugify(text: str) -> str:
    """Generate a URL slug from text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")[:200]


def ingest_xlsx(filepath: str | Path, dataset_name_en: str | None = None):
    """Parse and ingest a single XLSX file."""
    filepath = Path(filepath)
    print(f"\nParsing {filepath.name}...")

    result = parse_xlsx(filepath)

    if result.errors:
        for err in result.errors:
            print(f"  ERROR: {err}")

    if not result.observations:
        print(f"  No observations extracted from {filepath.name}")
        return 0

    # Determine dataset name
    name_en = dataset_name_en or result.title_en or filepath.stem
    name_ar = result.title_ar or name_en
    slug = slugify(name_en)

    print(f"  Title: {name_en}")
    print(f"  Observations: {len(result.observations)}")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Get PCBS source
    cur.execute("SELECT id FROM sources WHERE slug = 'pcbs'")
    source_id = cur.fetchone()[0]

    # Create/update dataset
    cur.execute("""
        INSERT INTO datasets (slug, name_en, name_ar, description_en, category_id,
                              primary_source_id, status, update_frequency)
        VALUES (%s, %s, %s, %s,
                (SELECT id FROM categories WHERE slug = 'economy'),
                %s, 'published', 'monthly')
        ON CONFLICT (slug) DO UPDATE SET
            name_en = EXCLUDED.name_en,
            name_ar = EXCLUDED.name_ar
        RETURNING id
    """, (slug, name_en, name_ar,
          f"PCBS industrial production indices. {result.base_year_note}",
          source_id))
    dataset_id = cur.fetchone()[0]

    # Link source
    cur.execute("""
        INSERT INTO dataset_sources (dataset_id, source_id, is_primary)
        VALUES (%s, %s, true) ON CONFLICT (dataset_id, source_id) DO NOTHING
    """, (dataset_id, source_id))

    # Source document
    cur.execute("""
        INSERT INTO source_documents (source_id, title_en, document_url, file_type, access_date)
        VALUES (%s, %s, %s, 'excel', CURRENT_DATE)
        RETURNING id
    """, (source_id, name_en, f"file://{filepath.resolve()}"))
    source_doc_id = cur.fetchone()[0]

    # Create indicators
    indicator_ids = {}
    seen_indicators = set()
    for obs in result.observations:
        key = (obs.indicator_name_en, obs.indicator_name_ar)
        if key not in seen_indicators:
            seen_indicators.add(key)
            code = slugify(obs.indicator_name_en)[:100]
            cur.execute("""
                INSERT INTO indicators (dataset_id, code, name_en, name_ar, unit_en, decimals)
                VALUES (%s, %s, %s, %s, 'index points', 2)
                ON CONFLICT ON CONSTRAINT indicators_dataset_id_code_key
                DO UPDATE SET name_en = EXCLUDED.name_en, name_ar = EXCLUDED.name_ar
                RETURNING id
            """, (dataset_id, code, obs.indicator_name_en, obs.indicator_name_ar))
            indicator_ids[key] = cur.fetchone()[0]

    conn.commit()

    # Delete existing observations for this dataset
    cur.execute("""
        DELETE FROM observations WHERE indicator_id IN (
            SELECT id FROM indicators WHERE dataset_id = %s
        )
    """, (dataset_id,))

    # Insert observations
    obs_rows = []
    for obs in result.observations:
        key = (obs.indicator_name_en, obs.indicator_name_ar)
        ind_id = indicator_ids[key]
        obs_rows.append((
            ind_id,
            "PS",  # National level
            obs.time_period,
            obs.time_precision,
            obs.value,
            source_doc_id,
        ))

    if obs_rows:
        execute_values(cur, """
            INSERT INTO observations (indicator_id, geography_code, time_period,
                                      time_precision, value, source_document_id)
            VALUES %s
        """, obs_rows)

    # Update temporal coverage
    cur.execute("""
        UPDATE datasets SET
            temporal_coverage_start = sub.min_t,
            temporal_coverage_end = sub.max_t
        FROM (
            SELECT MIN(o.time_period) as min_t, MAX(o.time_period) as max_t
            FROM observations o JOIN indicators i ON o.indicator_id = i.id
            WHERE i.dataset_id = %s
        ) sub WHERE datasets.id = %s
    """, (dataset_id, dataset_id))

    conn.commit()
    print(f"  Inserted {len(obs_rows)} observations into dataset '{name_en}'")

    cur.close()
    conn.close()
    return len(obs_rows)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python xlsx_ingest.py <file.xlsx> [dataset_name]")
        sys.exit(1)

    filepath = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else None
    count = ingest_xlsx(filepath, name)
    print(f"\nTotal: {count} observations ingested")
