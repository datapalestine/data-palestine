"""PCBS CSV download and ingestion pipeline.

Reads the discovery JSON from Part A, downloads each CSV,
parses it, creates dataset/indicator/observation records.

Usage:
    python pcbs_csv_ingest.py [--discovery data/pcbs_discovery.json] [--limit 0]
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import re
import sys
from datetime import date, datetime
from io import StringIO
from pathlib import Path

import httpx
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)

import os
DB_URL = os.environ.get("DATABASE_URL", "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine")
PCBS_BASE = "https://www.pcbs.gov.ps"

# ─── Geography detection ─────────────────────────────────
# Maps governorate name variants → PCBS geography codes.
# Loaded from DB at runtime, but these are the known English names for fallback.
GOVERNORATE_NAME_MAP: dict[str, str] = {}  # populated by load_geography_names()


def load_geography_names(cur) -> dict[str, str]:
    """Load all geography names (EN + AR) → code mapping from the DB."""
    cur.execute("SELECT code, name_en, name_ar FROM geographies WHERE level = 'governorate'")
    name_map: dict[str, str] = {}
    for code, name_en, name_ar in cur.fetchall():
        # Map both exact and lowercase variants
        name_map[name_en.lower()] = code
        name_map[name_ar] = code
        # Also map without "& " for "Ramallah & Al-Bireh" → match "Ramallah"
        first_part = name_en.split("&")[0].strip().lower()
        if first_part != name_en.lower():
            name_map[first_part] = code
    return name_map


def detect_geography_in_name(indicator_name: str, geo_map: dict[str, str]) -> tuple[str, str]:
    """Check if an indicator name contains a governorate name.

    Returns (cleaned_name, geography_code).
    If no geography found, returns (original_name, "PS").
    """
    name_lower = indicator_name.lower().strip()

    for geo_name, geo_code in sorted(geo_map.items(), key=lambda x: -len(x[0])):
        # Check if the indicator name IS the geography name (city as row header)
        if name_lower == geo_name.lower():
            return indicator_name, geo_code

        # Check if geography name appears as a suffix or in parentheses
        # e.g., "Criminal assaults - Jenin", "Assaults (Jenin)"
        if geo_name.lower() in name_lower:
            # Clean it out of the name
            cleaned = indicator_name
            # Try common separators
            for sep in [" - ", ", ", " – ", " — "]:
                if sep + geo_name.lower() in name_lower:
                    idx = name_lower.index(sep + geo_name.lower())
                    cleaned = indicator_name[:idx].strip()
                    break
                if geo_name.lower() + sep in name_lower:
                    idx = name_lower.index(geo_name.lower() + sep)
                    cleaned = indicator_name[idx + len(geo_name + sep):].strip()
                    break
            # Try parenthetical
            import re as _re
            paren = _re.search(r'\(' + _re.escape(geo_name) + r'\)', indicator_name, _re.IGNORECASE)
            if paren:
                cleaned = indicator_name[:paren.start()].strip()

            # If cleaned is empty or same as original, just use original
            if not cleaned or cleaned == indicator_name:
                return indicator_name, geo_code

            return cleaned, geo_code

    return indicator_name, "PS"


def slugify(text: str) -> str:
    """Create a URL-safe slug from text."""
    text = text.lower().strip()
    text = re.sub(r"pcbs\s*\|\s*", "", text)
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:200].strip("-")


def clean_title(title: str) -> str:
    """Remove 'PCBS | ' prefix and clean up the title."""
    title = re.sub(r"^PCBS\s*\|\s*", "", title).strip()
    return title


def detect_header_row(lines: list[str]) -> int:
    """Find the first row that looks like a data header.

    Heuristic: the header row has multiple comma-separated non-empty values,
    does NOT start with a number, and is not a metadata line.
    """
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        parts = [p.strip().strip('"') for p in stripped.split(",")]
        non_empty = [p for p in parts if p]

        # Skip rows that are mostly empty (metadata rows like "West Bank and Gaza,,,,")
        if len(non_empty) < 2:
            continue

        # Skip rows that start with "Values in" or similar metadata
        first = non_empty[0].lower()
        if any(first.startswith(prefix) for prefix in (
            "values in", "source:", "note:", "* ", "** ", "west bank and gaza",
        )):
            continue

        # Good candidate: has multiple values and first value is text
        if len(non_empty) >= 2:
            return i

    return 0


def parse_time_period(col_name: str) -> tuple[date, str] | None:
    """Try to parse a column name as a time period.

    Returns (date, precision) or None.
    Handles: "2020", "Q1/2020", "Jun. 2020", "2020Q1", "May-2020", etc.
    """
    col = col_name.strip().strip("*").strip()

    # Year only: "2020", "2019**"
    m = re.match(r"^(\d{4})\*{0,3}$", col)
    if m:
        return date(int(m.group(1)), 1, 1), "annual"

    # Quarter: "Q1/2020", "Q1 2020", "2020Q1"
    m = re.match(r"^Q(\d)[/\s](\d{4})\*{0,3}$", col)
    if m:
        q = int(m.group(1))
        y = int(m.group(2))
        month = {1: 1, 2: 4, 3: 7, 4: 10}[q]
        return date(y, month, 1), "quarterly"

    m = re.match(r"^(\d{4})Q(\d)\*{0,3}$", col)
    if m:
        y = int(m.group(1))
        q = int(m.group(2))
        month = {1: 1, 2: 4, 3: 7, 4: 10}[q]
        return date(y, month, 1), "quarterly"

    # Quarter period: "2014Q1"
    m = re.match(r"^(\d{4})Q(\d)\*{0,3}$", col, re.IGNORECASE)
    if m:
        y = int(m.group(1))
        q = int(m.group(2))
        month = {1: 1, 2: 4, 3: 7, 4: 10}[q]
        return date(y, month, 1), "quarterly"

    # Month abbreviation: "Jun. 2020", "May 2020"
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    m = re.match(r"^(\w{3})\.?\s*(\d{4})\*{0,3}$", col)
    if m:
        abbr = m.group(1).lower()
        if abbr in month_map:
            return date(int(m.group(2)), month_map[abbr], 1), "monthly"

    return None


def parse_csv_content(content: str, title: str) -> tuple[pd.DataFrame, list[str]] | None:
    """Parse a PCBS CSV into a DataFrame, handling metadata header rows.

    Returns (dataframe, issues) or None if unparseable.
    """
    lines = content.strip().split("\n")
    issues = []

    if len(lines) < 2:
        return None

    header_idx = detect_header_row(lines)
    if header_idx > 0:
        issues.append(f"Skipped {header_idx} metadata rows")

    cleaned = "\n".join(lines[header_idx:])

    try:
        df = pd.read_csv(StringIO(cleaned), encoding="utf-8")
    except Exception as e:
        issues.append(f"CSV parse error: {e}")
        return None

    if df.empty or len(df.columns) < 2:
        issues.append("Too few columns")
        return None

    # Drop fully empty rows/columns
    df = df.dropna(how="all").dropna(axis=1, how="all")

    if df.empty:
        return None

    return df, issues


def extract_observations_from_df(
    df: pd.DataFrame, indicator_name_col: int = 0
) -> list[dict]:
    """Extract observation records from a parsed DataFrame.

    Assumes:
    - First column contains indicator/category names
    - Other columns are time periods or regional breakdowns
    """
    observations = []
    label_col = df.columns[indicator_name_col]
    value_cols = df.columns[indicator_name_col + 1:]

    for _, row in df.iterrows():
        indicator_name = str(row[label_col]).strip()

        # Skip empty/header-like rows
        if not indicator_name or indicator_name.lower() in ("", "nan", "total"):
            continue

        for col in value_cols:
            raw_value = row[col]

            # Parse the column name as a time period
            time_info = parse_time_period(str(col))

            # Try to extract a numeric value
            if pd.isna(raw_value):
                continue

            try:
                if isinstance(raw_value, str):
                    # Remove commas, percent signs, spaces
                    cleaned = raw_value.replace(",", "").replace("%", "").strip()
                    if not cleaned or cleaned in ("-", "..", "..."):
                        continue
                    value = float(cleaned)
                else:
                    value = float(raw_value)
            except (ValueError, TypeError):
                continue

            obs = {
                "indicator_name": indicator_name,
                "column_name": str(col).strip(),
                "value": value,
            }
            if time_info:
                obs["time_period"] = time_info[0]
                obs["time_precision"] = time_info[1]
            else:
                # Column might be "Palestine Jun. 2020" or "% Change" etc
                # Try to extract time from compound column names
                parts = str(col).strip().split()
                for p in parts:
                    t = parse_time_period(p)
                    if t:
                        obs["time_period"] = t[0]
                        obs["time_precision"] = t[1]
                        break
                # If it contains "Change" or "%" it's a derived metric, skip
                if "change" in str(col).lower() or "%" in str(col):
                    continue

            observations.append(obs)

    return observations


async def download_csv(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
    """Download a CSV file. Returns (content, sha256)."""
    resp = await client.get(url, follow_redirects=True)
    resp.raise_for_status()
    raw = resp.content
    sha256 = hashlib.sha256(raw).hexdigest()
    content = raw.decode("utf-8-sig", errors="replace")
    return content, sha256


def ingest_table(
    conn,
    table_info: dict,
    csv_content: str,
    csv_hash: str,
    source_id: int,
    pcbs_category_map: dict[str, int],
    geo_name_map: dict[str, str] | None = None,
) -> dict:
    """Ingest a single PCBS CSV table into the database.

    Returns a summary dict.
    """
    cur = conn.cursor()
    title = clean_title(table_info["title"])
    slug = slugify(table_info["title"])
    table_id = table_info["table_id"]

    # Parse the CSV
    result = parse_csv_content(csv_content, title)
    if result is None:
        return {"table_id": table_id, "status": "skipped", "reason": "unparseable"}

    df, issues = result

    # Extract observations
    observations = extract_observations_from_df(df)
    # Filter to only observations with a resolved time period
    dated_obs = [o for o in observations if "time_period" in o]

    if not dated_obs:
        return {
            "table_id": table_id,
            "status": "skipped",
            "reason": f"no dated observations ({len(observations)} raw, 0 with dates)",
        }

    # Guess category from title keywords
    category_id = None
    title_lower = title.lower()
    if any(k in title_lower for k in ("price index", "cpi", "consumer price")):
        category_id = pcbs_category_map.get("economy")
    elif any(k in title_lower for k in ("gdp", "national accounts", "gross domestic")):
        category_id = pcbs_category_map.get("economy")
    elif any(k in title_lower for k in ("balance of payments", "investment position", "debt")):
        category_id = pcbs_category_map.get("economy")
    elif any(k in title_lower for k in ("construction", "road cost", "water network", "sewage")):
        category_id = pcbs_category_map.get("infrastructure")
    elif any(k in title_lower for k in ("health", "expenditure on health")):
        category_id = pcbs_category_map.get("health")
    elif any(k in title_lower for k in ("greenhouse", "emission", "co2", "climate")):
        category_id = pcbs_category_map.get("environment")
    elif any(k in title_lower for k in ("crim", "theft", "narcotic", "offense")):
        category_id = pcbs_category_map.get("governance")
    elif any(k in title_lower for k in ("temperature", "weather", "rain")):
        category_id = pcbs_category_map.get("environment")
    elif any(k in title_lower for k in ("producer price", "wholesale price", "industrial")):
        category_id = pcbs_category_map.get("economy")

    # Create source_document
    cur.execute(
        """INSERT INTO source_documents
           (source_id, title_en, document_url, file_type, access_date,
            checksum_sha256, metadata)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           RETURNING id""",
        (
            source_id,
            title[:500],
            table_info["csv_url"][:1000],
            "csv",
            date.today(),
            csv_hash,
            json.dumps({"pcbs_table_id": table_id, "source_page": table_info["url"]}),
        ),
    )
    source_doc_id = cur.fetchone()[0]

    # Create dataset
    cur.execute(
        """INSERT INTO datasets
           (slug, name_en, name_ar, description_en,
            category_id, primary_source_id, status, license, featured)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (slug) DO UPDATE SET updated_at = NOW()
           RETURNING id""",
        (
            slug,
            title[:500],
            title[:500],  # Arabic title same for now — will be enriched later
            f"PCBS statistical table: {title}. Source: {table_info['url']}",
            category_id,
            source_id,
            "published",
            "CC-BY-4.0",
            False,
        ),
    )
    dataset_id = cur.fetchone()[0]

    # Link dataset to source
    cur.execute(
        """INSERT INTO dataset_sources (dataset_id, source_id, is_primary)
           VALUES (%s, %s, TRUE)
           ON CONFLICT DO NOTHING""",
        (dataset_id, source_id),
    )

    # Group observations by indicator name, detecting geography in names
    geo_map = geo_name_map or {}
    indicator_id_map = {}  # (cleaned_name, geo_code) -> indicator_id
    geo_detected_count = 0

    # First pass: determine cleaned indicator names and geography codes
    processed_obs = []
    for o in dated_obs:
        raw_name = o["indicator_name"]
        cleaned_name, geo_code = detect_geography_in_name(raw_name, geo_map)
        if geo_code != "PS":
            geo_detected_count += 1
        processed_obs.append({
            **o,
            "cleaned_indicator": cleaned_name,
            "geography_code": geo_code,
        })

    if geo_detected_count > 0:
        logger.info("  Geography detected in %d/%d observations", geo_detected_count, len(processed_obs))

    # Create indicator records (using cleaned names)
    unique_indicators = sorted(set(o["cleaned_indicator"] for o in processed_obs))
    for ind_name in unique_indicators:
        ind_code = slugify(ind_name)[:100]
        if not ind_code:
            continue

        cur.execute(
            """INSERT INTO indicators
               (dataset_id, code, name_en, name_ar)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (dataset_id, code) DO UPDATE SET updated_at = NOW()
               RETURNING id""",
            (dataset_id, ind_code, ind_name[:500], ind_name[:500]),
        )
        indicator_id_map[ind_name] = cur.fetchone()[0]

    # Bulk insert observations with proper geography codes
    obs_tuples = []
    for o in processed_obs:
        ind_id = indicator_id_map.get(o["cleaned_indicator"])
        if not ind_id:
            continue
        obs_tuples.append((
            ind_id,
            o["geography_code"],
            o["time_period"],
            o.get("time_precision", "annual"),
            o["value"],
            "final",
            source_doc_id,
            1,
            True,
        ))

    inserted = 0
    if obs_tuples:
        execute_values(
            cur,
            """INSERT INTO observations
               (indicator_id, geography_code, time_period, time_precision,
                value, status, source_document_id, data_version, is_latest)
               VALUES %s
               ON CONFLICT DO NOTHING""",
            obs_tuples,
        )
        inserted = len(obs_tuples)

    # Update dataset temporal coverage
    cur.execute(
        """UPDATE datasets SET
            temporal_coverage_start = (
                SELECT MIN(o.time_period) FROM observations o
                JOIN indicators i ON o.indicator_id = i.id
                WHERE i.dataset_id = %s
            ),
            temporal_coverage_end = (
                SELECT MAX(o.time_period) FROM observations o
                JOIN indicators i ON o.indicator_id = i.id
                WHERE i.dataset_id = %s
            ),
            published_at = COALESCE(published_at, NOW()),
            updated_at = NOW()
           WHERE id = %s""",
        (dataset_id, dataset_id, dataset_id),
    )

    return {
        "table_id": table_id,
        "status": "ingested",
        "dataset_id": dataset_id,
        "title": title[:60],
        "indicators": len(indicator_id_map),
        "observations": inserted,
        "issues": issues,
    }


def run_ingestion(discovery_path: str, limit: int = 0) -> dict:
    """Run the full PCBS CSV ingestion pipeline."""
    # Load discovery results
    with open(discovery_path) as f:
        tables = json.load(f)

    # Filter to tables with CSV links
    csv_tables = [t for t in tables if t.get("csv_url")]
    if limit > 0:
        csv_tables = csv_tables[:limit]

    logger.info("Found %d tables with CSV links (processing %d)", len(csv_tables), len(csv_tables))

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    started_at = datetime.now()
    results = []
    total_observations = 0
    total_datasets = 0

    try:
        cur = conn.cursor()

        # Get PCBS source ID
        cur.execute("SELECT id FROM sources WHERE slug = 'pcbs'")
        source_id = cur.fetchone()[0]

        # Get category map
        cur.execute("SELECT slug, id FROM categories")
        pcbs_category_map = dict(cur.fetchall())

        # Load geography name map for geo-in-indicator detection
        geo_name_map = load_geography_names(cur)

        # Process each table
        for i, table_info in enumerate(csv_tables):
            table_id = table_info["table_id"]
            logger.info(
                "[%d/%d] Downloading table_id=%d: %s",
                i + 1, len(csv_tables), table_id,
                clean_title(table_info["title"])[:60],
            )

            try:
                # Download CSV
                content, sha256 = asyncio.run(
                    _download_csv_async(table_info["csv_url"])
                )

                # Ingest
                result = ingest_table(
                    conn, table_info, content, sha256,
                    source_id, pcbs_category_map, geo_name_map,
                )
                results.append(result)

                if result["status"] == "ingested":
                    total_observations += result["observations"]
                    total_datasets += 1
                    logger.info(
                        "  -> %d indicators, %d observations",
                        result["indicators"], result["observations"],
                    )
                else:
                    logger.info("  -> skipped: %s", result.get("reason", ""))

            except Exception as e:
                logger.error("  -> ERROR: %s", e)
                results.append({
                    "table_id": table_id,
                    "status": "error",
                    "reason": str(e),
                })

            # Small delay between downloads
            asyncio.run(asyncio.sleep(1.0))

        # Record pipeline run
        completed_at = datetime.now()
        cur.execute(
            """INSERT INTO pipeline_runs
               (pipeline_name, started_at, completed_at, status,
                records_processed, records_inserted, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                "pcbs_csv_ingest",
                started_at,
                completed_at,
                "success",
                len(csv_tables),
                total_observations,
                json.dumps({"tables_ingested": total_datasets, "tables_skipped": len(csv_tables) - total_datasets}),
            ),
        )

        conn.commit()

    except Exception as e:
        conn.rollback()
        logger.error("Pipeline failed: %s", e)
        raise
    finally:
        conn.close()

    # Print summary
    ingested = [r for r in results if r["status"] == "ingested"]
    skipped = [r for r in results if r["status"] == "skipped"]
    errors = [r for r in results if r["status"] == "error"]

    print("\n" + "=" * 60)
    print("PCBS CSV INGESTION — RESULTS")
    print("=" * 60)
    print(f"  Tables processed:     {len(csv_tables)}")
    print(f"  Successfully ingested: {len(ingested)}")
    print(f"  Skipped:              {len(skipped)}")
    print(f"  Errors:               {len(errors)}")
    print(f"  Total datasets:       {total_datasets}")
    print(f"  Total observations:   {total_observations}")
    print(f"  Duration:             {(completed_at - started_at).total_seconds():.1f}s")
    print()

    if ingested:
        print("Ingested tables:")
        for r in ingested:
            print(f"  [{r['table_id']}] {r['title']}: {r['indicators']} ind, {r['observations']} obs")
        print()

    if skipped:
        print("Skipped tables:")
        for r in skipped:
            print(f"  [{r['table_id']}] {r.get('reason', '')}")
        print()

    if errors:
        print("Errors:")
        for r in errors:
            print(f"  [{r['table_id']}] {r.get('reason', '')}")

    return {
        "ingested": len(ingested),
        "skipped": len(skipped),
        "errors": len(errors),
        "total_observations": total_observations,
    }


async def _download_csv_async(url: str) -> tuple[str, str]:
    """Async wrapper for CSV download."""
    async with httpx.AsyncClient(
        timeout=60,
        headers={"User-Agent": "DataPalestine/0.1 (open data platform)"},
    ) as client:
        return await download_csv(client, url)


def reprocess_geography(db_url: str = DB_URL) -> dict:
    """Re-run geography detection on existing observations.

    Finds indicators whose names contain governorate names,
    updates the observation geography_code from 'PS' to the correct governorate,
    and optionally cleans the indicator name.
    """
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    geo_map = load_geography_names(cur)
    logger.info("Loaded %d geography name mappings", len(geo_map))

    # Get all PCBS indicators
    cur.execute("""
        SELECT i.id, i.dataset_id, i.name_en, i.code
        FROM indicators i
        JOIN datasets d ON i.dataset_id = d.id
        JOIN dataset_sources ds ON d.id = ds.dataset_id
        JOIN sources s ON ds.source_id = s.id
        WHERE s.slug = 'pcbs'
    """)
    indicators = cur.fetchall()
    logger.info("Checking %d PCBS indicators for geography in names", len(indicators))

    updated_obs = 0
    updated_ind = 0
    renamed = []

    for ind_id, dataset_id, name_en, code in indicators:
        cleaned_name, geo_code = detect_geography_in_name(name_en, geo_map)

        if geo_code == "PS":
            continue

        # Update observations for this indicator: set geography_code
        cur.execute(
            """UPDATE observations SET geography_code = %s
               WHERE indicator_id = %s AND geography_code = 'PS'""",
            (geo_code, ind_id),
        )
        count = cur.rowcount
        if count > 0:
            updated_obs += count

        # If the indicator name was cleaned, update it
        if cleaned_name != name_en:
            new_code = slugify(cleaned_name)[:100]
            # Check for code collision before renaming
            cur.execute(
                "SELECT id FROM indicators WHERE dataset_id = %s AND code = %s AND id != %s",
                (dataset_id, new_code, ind_id),
            )
            if cur.fetchone() is None:
                cur.execute(
                    "UPDATE indicators SET name_en = %s, name_ar = %s, code = %s WHERE id = %s",
                    (cleaned_name, cleaned_name, new_code, ind_id),
                )
                updated_ind += 1
                renamed.append(f"{name_en} -> {cleaned_name} ({geo_code})")

    # Record pipeline run
    cur.execute(
        """INSERT INTO pipeline_runs
           (pipeline_name, started_at, completed_at, status,
            records_processed, records_updated, metadata)
           VALUES (%s, NOW(), NOW(), %s, %s, %s, %s)""",
        (
            "pcbs_geo_reprocess",
            "success",
            len(indicators),
            updated_obs,
            json.dumps({"indicators_renamed": updated_ind, "observations_updated": updated_obs}),
        ),
    )

    conn.commit()
    conn.close()

    print(f"\nGeography reprocessing complete:")
    print(f"  Indicators checked: {len(indicators)}")
    print(f"  Indicators renamed: {updated_ind}")
    print(f"  Observations updated: {updated_obs}")
    if renamed:
        print(f"\nRenamed indicators:")
        for r in renamed[:20]:
            print(f"  {r}")
        if len(renamed) > 20:
            print(f"  ... and {len(renamed) - 20} more")

    return {"indicators_renamed": updated_ind, "observations_updated": updated_obs}


def main():
    parser = argparse.ArgumentParser(description="PCBS CSV ingestion pipeline")
    parser.add_argument(
        "--discovery", type=str, default="data/pcbs_discovery.json",
        help="Path to discovery JSON from Part A",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Max tables to process (0 = all)",
    )
    parser.add_argument(
        "--db-url", type=str, default=DB_URL,
        help="PostgreSQL connection URL",
    )
    parser.add_argument(
        "--reprocess", action="store_true",
        help="Re-run geography detection on existing data instead of ingesting new data",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.reprocess:
        reprocess_geography(args.db_url)
    else:
        run_ingestion(args.discovery, args.limit)


if __name__ == "__main__":
    main()
