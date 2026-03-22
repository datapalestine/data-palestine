#!/usr/bin/env python3
"""Download all PCBS XLSX files from discovery data and ingest them."""

import json
import logging
import re
import sys
import time
from datetime import date
from pathlib import Path

import httpx
import psycopg2
from psycopg2.extras import execute_values

sys.path.insert(0, str(Path(__file__).parent.parent))
from packages.pipeline.pcbs.xlsx_parser import parse_xlsx, ParsedObservation

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

import os
DB_URL = os.environ.get("DATABASE_URL", "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine")
DOWNLOAD_DIR = Path("data/raw/pcbs_xlsx")
DELAY = 2  # seconds between requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 DataPalestine/1.0",
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")[:200]


def download_xlsx_files():
    """Download all XLSX files from discovery data."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    all_tables = []
    for fname in ["data/pcbs_discovery.json", "data/pcbs_discovery_200_5000.json"]:
        p = Path(fname)
        if p.exists():
            with open(p) as f:
                all_tables.extend(json.load(f))

    xlsx_tables = [t for t in all_tables if t.get("xlsx_url")]
    print(f"Found {len(xlsx_tables)} tables with XLSX links")

    downloaded = 0
    skipped = 0
    failed = 0

    for t in xlsx_tables:
        table_id = t["table_id"]
        url = t["xlsx_url"]

        # Determine filename from URL
        url_filename = url.split("/")[-1]
        dest = DOWNLOAD_DIR / f"table_{table_id}_{url_filename}"

        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
            continue

        print(f"  Downloading table_{table_id}: {url_filename}...", end=" ", flush=True)
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            print(f"OK ({len(resp.content):,} bytes)")
            downloaded += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

        time.sleep(DELAY)

    print(f"\nDownload complete: {downloaded} new, {skipped} already had, {failed} failed")
    return downloaded


def ingest_all_xlsx():
    """Parse and ingest all XLSX files in the download directory."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Get PCBS source ID
    cur.execute("SELECT id FROM sources WHERE slug = 'pcbs'")
    source_id = cur.fetchone()[0]

    xlsx_files = sorted(DOWNLOAD_DIR.glob("*.xlsx"))
    print(f"\n{'='*60}")
    print(f"Ingesting {len(xlsx_files)} XLSX files")
    print(f"{'='*60}")

    total_obs = 0
    success = 0
    failed_files = []

    for filepath in xlsx_files:
        try:
            result = parse_xlsx(filepath)
        except Exception as e:
            failed_files.append((filepath.name, str(e)))
            continue

        if not result.observations:
            continue

        name_en = result.title_en or filepath.stem.replace("_", " ").replace("-", " ").title()
        name_ar = result.title_ar or name_en
        slug = slugify(name_en)

        # Check if slug already exists (avoid duplicates with CSV-ingested data)
        cur.execute("SELECT id FROM datasets WHERE slug = %s", (slug,))
        existing = cur.fetchone()
        if existing:
            # Skip if we already have this dataset from CSV
            continue

        # Also check by similar name
        cur.execute("SELECT id FROM datasets WHERE LOWER(name_en) = LOWER(%s)", (name_en,))
        existing = cur.fetchone()
        if existing:
            continue

        # Create dataset
        cur.execute("""
            INSERT INTO datasets (slug, name_en, name_ar, description_en,
                                  primary_source_id, status)
            VALUES (%s, %s, %s, %s, %s, 'published')
            ON CONFLICT (slug) DO UPDATE SET name_en = EXCLUDED.name_en
            RETURNING id
        """, (slug, name_en, name_ar,
              f"PCBS data from Excel file. {result.base_year_note}".strip(),
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
        seen = set()
        for obs in result.observations:
            key = (obs.indicator_name_en, obs.indicator_name_ar)
            if key not in seen:
                seen.add(key)
                code = slugify(obs.indicator_name_en)[:100]
                # Handle code conflicts
                cur.execute("SELECT COUNT(*) FROM indicators WHERE dataset_id = %s AND code = %s",
                            (dataset_id, code))
                if cur.fetchone()[0] > 0:
                    code = f"{code}-{len(seen)}"
                cur.execute("""
                    INSERT INTO indicators (dataset_id, code, name_en, name_ar, unit_en, decimals)
                    VALUES (%s, %s, %s, %s, %s, 2)
                    ON CONFLICT ON CONSTRAINT indicators_dataset_id_code_key
                    DO UPDATE SET name_en = EXCLUDED.name_en
                    RETURNING id
                """, (dataset_id, code, obs.indicator_name_en, obs.indicator_name_ar,
                      "percent" if "% Change" in obs.indicator_name_en else "index points"))
                indicator_ids[key] = cur.fetchone()[0]

        # Insert observations
        obs_rows = []
        for obs in result.observations:
            key = (obs.indicator_name_en, obs.indicator_name_ar)
            obs_rows.append((
                indicator_ids[key], "PS", obs.time_period,
                obs.time_precision, obs.value, source_doc_id,
            ))

        if obs_rows:
            # Deduplicate within batch
            seen_obs = set()
            unique_rows = []
            for row in obs_rows:
                key = (row[0], row[1], row[2], row[3])
                if key not in seen_obs:
                    seen_obs.add(key)
                    unique_rows.append(row)

            execute_values(cur, """
                INSERT INTO observations (indicator_id, geography_code, time_period,
                                          time_precision, value, source_document_id)
                VALUES %s
                ON CONFLICT DO NOTHING
            """, unique_rows)
            total_obs += len(unique_rows)

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
        success += 1
        print(f"  ✓ {name_en[:70]}: {len(unique_rows)} obs")

    # Remove datasets with 0 observations (failed parses)
    cur.execute("""
        DELETE FROM datasets WHERE id IN (
            SELECT d.id FROM datasets d
            LEFT JOIN indicators i ON i.dataset_id = d.id
            LEFT JOIN observations o ON o.indicator_id = i.id
            WHERE o.id IS NULL AND d.slug LIKE '%table-%'
            GROUP BY d.id
        )
    """)

    conn.commit()

    print(f"\n{'='*60}")
    print(f"XLSX Ingestion Complete")
    print(f"{'='*60}")
    print(f"  Files processed: {success}")
    print(f"  Files failed: {len(failed_files)}")
    print(f"  New observations: {total_obs:,}")

    if failed_files:
        print(f"\n  Failed files:")
        for name, err in failed_files[:10]:
            print(f"    {name}: {err}")

    # Final counts
    cur.execute("SELECT COUNT(*) FROM datasets")
    ds = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM indicators")
    inds = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM observations")
    obs = cur.fetchone()[0]
    print(f"\n  Database totals: {ds} datasets, {inds:,} indicators, {obs:,} observations")

    cur.close()
    conn.close()
    return total_obs


if __name__ == "__main__":
    downloaded = download_xlsx_files()
    ingested = ingest_all_xlsx()
