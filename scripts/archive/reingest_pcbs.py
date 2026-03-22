"""Re-ingest all PCBS CSVs using the new pattern-specific parser.

Wipes existing PCBS observations (keeps World Bank untouched),
then re-ingests from data/raw/pcbs_csv/ using pcbs.csv_parser.

Usage:
    python scripts/reingest_pcbs.py
"""

import json
import logging
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "pipeline"))
from pcbs.csv_parser import detect_pattern, parse_csv, RawObservation

logger = logging.getLogger(__name__)
import os
DB_URL = os.environ.get("DATABASE_URL", "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine")
CSV_DIR = Path("data/raw/pcbs_csv")
DISCOVERY_PATH = Path("data/pcbs_discovery.json")

# Geography name → code mapping (loaded from DB)
GEO_MAP: dict[str, str] = {}

GOVERNORATE_NAMES = [
    "Jenin", "Tubas", "Tulkarm", "Nablus", "Qalqiliya", "Salfit",
    "Ramallah", "Jericho", "Jerusalem", "Bethlehem", "Hebron",
    "North Gaza", "Gaza", "Deir Al-Balah", "Khan Yunis", "Rafah",
]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"pcbs\s*\|\s*", "", text)
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:200].strip("-")


def clean_title(title: str) -> str:
    return re.sub(r"^PCBS\s*\|\s*", "", title).strip()


def detect_geography_in_name(name: str) -> tuple[str, str]:
    """Check if an indicator name IS a governorate name."""
    name_lower = name.lower().strip()
    for geo_name, geo_code in sorted(GEO_MAP.items(), key=lambda x: -len(x[0])):
        if name_lower == geo_name.lower():
            return name, geo_code
    return name, "PS"


def guess_category(title: str, cat_map: dict[str, int]) -> int | None:
    t = title.lower()
    if any(k in t for k in ("price index", "cpi", "consumer price")):
        return cat_map.get("economy")
    if any(k in t for k in ("gdp", "national accounts", "gross domestic")):
        return cat_map.get("economy")
    if any(k in t for k in ("balance of payments", "investment position", "debt", "external")):
        return cat_map.get("economy")
    if any(k in t for k in ("construction", "road cost", "water network", "sewage")):
        return cat_map.get("infrastructure")
    if any(k in t for k in ("health", "expenditure on health")):
        return cat_map.get("health")
    if any(k in t for k in ("greenhouse", "emission", "co2", "climate")):
        return cat_map.get("environment")
    if any(k in t for k in ("crim", "theft", "narcotic", "offense", "assault")):
        return cat_map.get("governance")
    if any(k in t for k in ("temperature", "weather", "rain")):
        return cat_map.get("environment")
    if any(k in t for k in ("producer price", "wholesale price", "industrial")):
        return cat_map.get("economy")
    if any(k in t for k in ("trade", "export", "import")):
        return cat_map.get("economy")
    return None


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Load discovery metadata for table titles
    discovery = {}
    if DISCOVERY_PATH.exists():
        with open(DISCOVERY_PATH) as f:
            for item in json.load(f):
                discovery[item["table_id"]] = item

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # Load geography name map
    global GEO_MAP
    cur.execute("SELECT code, name_en, name_ar FROM geographies WHERE level = 'governorate'")
    for code, name_en, name_ar in cur.fetchall():
        GEO_MAP[name_en.lower()] = code
        GEO_MAP[name_ar] = code
        first_part = name_en.split("&")[0].strip().lower()
        if first_part != name_en.lower():
            GEO_MAP[first_part] = code

    # Load category map
    cur.execute("SELECT slug, id FROM categories")
    cat_map = dict(cur.fetchall())

    # Get PCBS source ID
    cur.execute("SELECT id FROM sources WHERE slug = 'pcbs'")
    source_id = cur.fetchone()[0]

    # --- Record old counts ---
    cur.execute("""
        SELECT COUNT(*) FROM observations o
        JOIN indicators i ON o.indicator_id = i.id
        JOIN dataset_sources ds ON i.dataset_id = ds.dataset_id
        JOIN sources s ON ds.source_id = s.id
        WHERE s.slug = 'pcbs'
    """)
    old_pcbs_obs = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM indicators i
        JOIN dataset_sources ds ON i.dataset_id = ds.dataset_id
        JOIN sources s ON ds.source_id = s.id
        WHERE s.slug = 'pcbs'
    """)
    old_pcbs_ind = cur.fetchone()[0]

    logger.info("OLD STATE: %d PCBS observations, %d PCBS indicators", old_pcbs_obs, old_pcbs_ind)

    # --- Wipe existing PCBS data ---
    logger.info("Wiping existing PCBS observations, indicators, datasets...")
    cur.execute("""
        DELETE FROM observations WHERE indicator_id IN (
            SELECT i.id FROM indicators i
            JOIN dataset_sources ds ON i.dataset_id = ds.dataset_id
            WHERE ds.source_id = %s
        )
    """, (source_id,))
    logger.info("  Deleted %d observations", cur.rowcount)

    cur.execute("""
        DELETE FROM indicators WHERE dataset_id IN (
            SELECT ds.dataset_id FROM dataset_sources ds WHERE ds.source_id = %s
        )
    """, (source_id,))
    logger.info("  Deleted %d indicators", cur.rowcount)

    cur.execute("""
        DELETE FROM dataset_sources WHERE source_id = %s
    """, (source_id,))

    cur.execute("""
        DELETE FROM datasets WHERE id NOT IN (
            SELECT dataset_id FROM dataset_sources
        ) AND primary_source_id = %s
    """, (source_id,))
    logger.info("  Deleted %d datasets", cur.rowcount)

    # Delete PCBS source documents
    cur.execute("DELETE FROM source_documents WHERE source_id = %s", (source_id,))

    # --- Re-ingest from disk ---
    csv_files = sorted(CSV_DIR.glob("table_*.csv"), key=lambda f: int(f.stem.split("_")[1]))
    logger.info("Found %d CSV files to ingest", len(csv_files))

    total_obs = 0
    total_datasets = 0
    total_indicators = 0
    pattern_counts = Counter()
    precision_counts = Counter()
    results = []

    for csv_file in csv_files:
        table_id = int(csv_file.stem.split("_")[1])
        info = discovery.get(table_id, {})
        title = clean_title(info.get("title", f"PCBS Table {table_id}"))
        slug = slugify(title)
        csv_url = info.get("csv_url", "")
        page_url = info.get("url", "")

        # Detect pattern and parse
        pattern = detect_pattern(csv_file)
        pattern_counts[pattern] += 1
        observations = parse_csv(csv_file)

        if not observations:
            results.append({"table_id": table_id, "status": "empty", "pattern": pattern})
            continue

        for o in observations:
            precision_counts[o.time_precision] += 1

        # Apply geography detection to indicator names
        for obs in observations:
            if obs.geography_code == "PS":
                _, geo = detect_geography_in_name(obs.indicator_name, )
                obs.geography_code = geo

        # Create source_document
        cur.execute("""
            INSERT INTO source_documents
            (source_id, title_en, document_url, file_type, access_date, metadata)
            VALUES (%s, %s, %s, 'csv', %s, %s)
            RETURNING id
        """, (
            source_id, title[:500], csv_url[:1000], date.today(),
            json.dumps({"pcbs_table_id": table_id, "source_page": page_url, "pattern": pattern}),
        ))
        source_doc_id = cur.fetchone()[0]

        # Create dataset
        category_id = guess_category(title, cat_map)
        cur.execute("""
            INSERT INTO datasets
            (slug, name_en, name_ar, description_en, category_id,
             primary_source_id, status, license, featured)
            VALUES (%s, %s, %s, %s, %s, %s, 'published', 'CC-BY-4.0', FALSE)
            ON CONFLICT (slug) DO UPDATE SET updated_at = NOW()
            RETURNING id
        """, (
            slug, title[:500], title[:500],
            f"PCBS statistical table: {title}",
            category_id, source_id,
        ))
        dataset_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO dataset_sources (dataset_id, source_id, is_primary)
            VALUES (%s, %s, TRUE)
            ON CONFLICT DO NOTHING
        """, (dataset_id, source_id))

        # Group observations by indicator name → create indicator records
        ind_names = sorted(set(o.indicator_name for o in observations))
        ind_id_map = {}
        for ind_name in ind_names:
            ind_code = slugify(ind_name)[:100]
            if not ind_code:
                continue

            # Detect unit from observations
            sample = next((o for o in observations if o.indicator_name == ind_name), None)
            unit = sample.unit if sample else ""
            unit_symbol = "%" if unit == "percent" else ""

            cur.execute("""
                INSERT INTO indicators
                (dataset_id, code, name_en, name_ar, unit_en, unit_symbol)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (dataset_id, code) DO UPDATE SET updated_at = NOW()
                RETURNING id
            """, (dataset_id, ind_code, ind_name[:500], ind_name[:500], unit, unit_symbol))
            ind_id_map[ind_name] = cur.fetchone()[0]

        # Bulk insert observations
        obs_tuples = []
        for o in observations:
            ind_id = ind_id_map.get(o.indicator_name)
            if not ind_id:
                continue
            dims_json = json.dumps(o.dimensions) if o.dimensions else "{}"
            obs_tuples.append((
                ind_id,
                o.geography_code,
                o.time_period,
                o.time_precision,
                o.value,
                "final",
                source_doc_id,
                dims_json,
                1,
                True,
            ))

        if obs_tuples:
            execute_values(cur, """
                INSERT INTO observations
                (indicator_id, geography_code, time_period, time_precision,
                 value, status, source_document_id, dimensions, data_version, is_latest)
                VALUES %s
                ON CONFLICT DO NOTHING
            """, obs_tuples)

        # Update temporal coverage
        cur.execute("""
            UPDATE datasets SET
                temporal_coverage_start = (
                    SELECT MIN(o.time_period) FROM observations o
                    JOIN indicators i ON o.indicator_id = i.id WHERE i.dataset_id = %s
                ),
                temporal_coverage_end = (
                    SELECT MAX(o.time_period) FROM observations o
                    JOIN indicators i ON o.indicator_id = i.id WHERE i.dataset_id = %s
                ),
                published_at = COALESCE(published_at, NOW()), updated_at = NOW()
            WHERE id = %s
        """, (dataset_id, dataset_id, dataset_id))

        n_obs = len(obs_tuples)
        n_ind = len(ind_id_map)
        total_obs += n_obs
        total_datasets += 1
        total_indicators += n_ind

        results.append({
            "table_id": table_id, "status": "ingested", "pattern": pattern,
            "title": title[:50], "indicators": n_ind, "observations": n_obs,
        })

    # Record pipeline run
    cur.execute("""
        INSERT INTO pipeline_runs
        (pipeline_name, started_at, completed_at, status, records_processed, records_inserted,
         metadata)
        VALUES ('pcbs_reingest_v2', NOW(), NOW(), 'success', %s, %s, %s)
    """, (
        len(csv_files), total_obs,
        json.dumps({"patterns": dict(pattern_counts), "precision": dict(precision_counts)}),
    ))

    conn.commit()
    conn.close()

    # --- Print report ---
    ingested = [r for r in results if r["status"] == "ingested"]
    empty = [r for r in results if r["status"] == "empty"]

    print("\n" + "=" * 70)
    print("PCBS RE-INGESTION — BEFORE / AFTER")
    print("=" * 70)
    print(f"\n  BEFORE: {old_pcbs_obs:,} observations, {old_pcbs_ind:,} indicators")
    print(f"  AFTER:  {total_obs:,} observations, {total_indicators:,} indicators, {total_datasets} datasets")
    print(f"  CHANGE: {total_obs - old_pcbs_obs:+,} observations ({total_obs/max(old_pcbs_obs,1):.1f}x)")

    print(f"\n  Files processed: {len(csv_files)}")
    print(f"  Successfully ingested: {len(ingested)}")
    print(f"  Empty (no parseable data): {len(empty)}")

    print(f"\n  By pattern:")
    for p, c in pattern_counts.most_common():
        print(f"    {p:30s} {c:3d} files")

    print(f"\n  By time precision:")
    for p, c in precision_counts.most_common():
        print(f"    {p:10s} {c:6,} observations")

    print(f"\n  Sample ingested tables:")
    for r in ingested[:10]:
        print(f"    [{r['table_id']:3d}] {r['pattern']:25s} {r['indicators']:3d} ind, {r['observations']:5d} obs  {r['title']}")


if __name__ == "__main__":
    main()
