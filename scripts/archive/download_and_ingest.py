"""Download new CSVs from discovery results, then ingest everything.

Usage:
    python scripts/download_and_ingest.py

Steps:
1. Load all discovery JSON files (original 1-200 + expanded 200-5000)
2. Download any CSVs not yet on disk to data/raw/pcbs_csv/
3. Run full ingestion of ALL CSVs using the pattern-aware parser
4. Apply geography detection + indicator consolidation + dedup
5. Quality pass: strip footnotes, set temporal coverage, set update frequency
"""

import asyncio
import json
import logging
import os
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import httpx
import psycopg2
from psycopg2.extras import execute_values

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "pipeline"))
from pcbs.csv_parser import detect_pattern, parse_csv, RawObservation

logger = logging.getLogger(__name__)
import os
DB_URL = os.environ.get("DATABASE_URL", "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine")
CSV_DIR = Path("data/raw/pcbs_csv")
DISCOVERY_FILES = [
    Path("data/pcbs_discovery.json"),          # table_ids 1-200
    Path("data/pcbs_discovery_200_5000.json"), # table_ids 200-5000
]

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


def clean_indicator_name(name: str) -> str:
    """Strip footnote markers and trailing garbage from indicator names."""
    name = re.sub(r'[\*]+$', '', name)
    name = re.sub(r'\s*\d+\)?\s*$', '', name)  # trailing "1)" or "2"
    name = re.sub(r'\s*[¹²³⁴⁵⁶⁷⁸⁹⁰]+\s*$', '', name)
    name = name.strip(' \t\r\n,.')
    return name


def detect_geography_in_name(name: str) -> tuple[str, str]:
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
    if any(k in t for k in ("population", "census", "demographic", "birth", "death", "fertility")):
        return cat_map.get("population")
    if any(k in t for k in ("education", "school", "student", "literacy", "university")):
        return cat_map.get("education")
    if any(k in t for k in ("labour", "labor", "employment", "unemployment", "wage", "workforce")):
        return cat_map.get("labor")
    if any(k in t for k in ("water", "electricity", "energy", "infrastructure")):
        return cat_map.get("infrastructure")
    if any(k in t for k in ("tourism", "hotel")):
        return cat_map.get("economy")
    return None


# ─── Step 1: Download ────────────────────────────────────

async def download_new_csvs():
    """Download CSVs from discovery results that aren't on disk yet."""
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    # Load all discovery results
    all_tables = {}
    for disc_file in DISCOVERY_FILES:
        if not disc_file.exists():
            logger.warning("Discovery file not found: %s", disc_file)
            continue
        with open(disc_file) as f:
            for item in json.load(f):
                if item.get("csv_url"):
                    all_tables[item["table_id"]] = item

    logger.info("Total tables with CSV links: %d", len(all_tables))

    # Find which ones we already have
    existing = set()
    for f in CSV_DIR.glob("table_*.csv"):
        tid = int(f.stem.split("_")[1])
        existing.add(tid)

    to_download = {tid: info for tid, info in all_tables.items() if tid not in existing}
    logger.info("Already downloaded: %d, to download: %d", len(existing), len(to_download))

    if not to_download:
        return all_tables

    downloaded = 0
    failed = 0
    async with httpx.AsyncClient(
        timeout=60,
        headers={"User-Agent": "DataPalestine/0.1 (open data platform)"},
    ) as client:
        for tid in sorted(to_download.keys()):
            url = to_download[tid]["csv_url"]
            try:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code == 200:
                    outpath = CSV_DIR / f"table_{tid}.csv"
                    outpath.write_bytes(resp.content)
                    downloaded += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
            await asyncio.sleep(1.0)

            if (downloaded + failed) % 50 == 0:
                logger.info("  Download progress: %d downloaded, %d failed", downloaded, failed)

    logger.info("Download complete: %d new files, %d failed", downloaded, failed)
    return all_tables


# ─── Step 2: Ingest ──────────────────────────────────────

def run_full_ingestion(all_tables: dict):
    """Ingest ALL CSVs from disk."""
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # Load geography map
    global GEO_MAP
    cur.execute("SELECT code, name_en, name_ar FROM geographies WHERE level = 'governorate'")
    for code, name_en, name_ar in cur.fetchall():
        GEO_MAP[name_en.lower()] = code
        GEO_MAP[name_ar] = code
        first_part = name_en.split("&")[0].strip().lower()
        if first_part != name_en.lower():
            GEO_MAP[first_part] = code

    cur.execute("SELECT slug, id FROM categories")
    cat_map = dict(cur.fetchall())

    cur.execute("SELECT id FROM sources WHERE slug = 'pcbs'")
    source_id = cur.fetchone()[0]

    # Record old state
    cur.execute("""
        SELECT COUNT(*) FROM observations o
        JOIN indicators i ON o.indicator_id = i.id
        JOIN dataset_sources ds ON i.dataset_id = ds.dataset_id
        WHERE ds.source_id = %s
    """, (source_id,))
    old_obs = cur.fetchone()[0]

    # Wipe existing PCBS data
    logger.info("Wiping existing PCBS data (%d observations)...", old_obs)
    cur.execute("DELETE FROM observations WHERE indicator_id IN (SELECT i.id FROM indicators i JOIN dataset_sources ds ON i.dataset_id = ds.dataset_id WHERE ds.source_id = %s)", (source_id,))
    cur.execute("DELETE FROM indicators WHERE dataset_id IN (SELECT ds.dataset_id FROM dataset_sources ds WHERE ds.source_id = %s)", (source_id,))
    cur.execute("DELETE FROM dataset_sources WHERE source_id = %s", (source_id,))
    cur.execute("DELETE FROM datasets WHERE primary_source_id = %s AND id NOT IN (SELECT dataset_id FROM dataset_sources)", (source_id,))
    cur.execute("DELETE FROM source_documents WHERE source_id = %s", (source_id,))

    # Ingest all CSVs from disk
    csv_files = sorted(CSV_DIR.glob("table_*.csv"), key=lambda f: int(f.stem.split("_")[1]))
    logger.info("Ingesting %d CSV files...", len(csv_files))

    total_obs = 0
    total_ind = 0
    total_ds = 0
    pattern_counts = Counter()
    precision_counts = Counter()
    failed_files = []

    for i, csv_file in enumerate(csv_files):
        table_id = int(csv_file.stem.split("_")[1])
        info = all_tables.get(table_id, {})
        title = clean_title(info.get("title", f"PCBS Table {table_id}"))
        slug = slugify(title)
        csv_url = info.get("csv_url", "")
        page_url = info.get("url", "")

        try:
            pattern = detect_pattern(csv_file)
            pattern_counts[pattern] += 1
            observations = parse_csv(csv_file)
        except Exception as e:
            failed_files.append((table_id, str(e)))
            continue

        if not observations:
            continue

        for o in observations:
            precision_counts[o.time_precision] += 1

        # Geography detection
        for obs in observations:
            if obs.geography_code == "PS":
                _, geo = detect_geography_in_name(obs.indicator_name)
                obs.geography_code = geo

        # Clean indicator names
        for obs in observations:
            obs.indicator_name = clean_indicator_name(obs.indicator_name)

        # Create source_document
        cur.execute("""
            INSERT INTO source_documents (source_id, title_en, document_url, file_type, access_date, metadata)
            VALUES (%s, %s, %s, 'csv', %s, %s) RETURNING id
        """, (source_id, title[:500], csv_url[:1000], date.today(),
              json.dumps({"pcbs_table_id": table_id, "pattern": pattern})))
        source_doc_id = cur.fetchone()[0]

        # Create dataset
        category_id = guess_category(title, cat_map)
        cur.execute("""
            INSERT INTO datasets (slug, name_en, name_ar, description_en, category_id,
                primary_source_id, status, license, featured)
            VALUES (%s, %s, %s, %s, %s, %s, 'published', 'CC-BY-4.0', FALSE)
            ON CONFLICT (slug) DO UPDATE SET updated_at = NOW() RETURNING id
        """, (slug, title[:500], title[:500], f"PCBS: {title}", category_id, source_id))
        dataset_id = cur.fetchone()[0]

        cur.execute("INSERT INTO dataset_sources (dataset_id, source_id, is_primary) VALUES (%s, %s, TRUE) ON CONFLICT DO NOTHING", (dataset_id, source_id))

        # Create indicators
        ind_names = sorted(set(o.indicator_name for o in observations if o.indicator_name))
        ind_id_map = {}
        for ind_name in ind_names:
            ind_code = slugify(ind_name)[:100]
            if not ind_code:
                continue
            sample = next((o for o in observations if o.indicator_name == ind_name), None)
            unit = sample.unit if sample else ""
            unit_sym = "%" if unit == "percent" else ""
            cur.execute("""
                INSERT INTO indicators (dataset_id, code, name_en, name_ar, unit_en, unit_symbol)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (dataset_id, code) DO UPDATE SET updated_at = NOW() RETURNING id
            """, (dataset_id, ind_code, ind_name[:500], ind_name[:500], unit, unit_sym))
            ind_id_map[ind_name] = cur.fetchone()[0]

        # Insert observations
        obs_tuples = []
        for o in observations:
            ind_id = ind_id_map.get(o.indicator_name)
            if not ind_id:
                continue
            dims_json = json.dumps(o.dimensions) if o.dimensions else "{}"
            obs_tuples.append((
                ind_id, o.geography_code, o.time_period, o.time_precision,
                o.value, "final", source_doc_id, dims_json, 1, True,
            ))

        if obs_tuples:
            execute_values(cur, """
                INSERT INTO observations (indicator_id, geography_code, time_period, time_precision,
                    value, status, source_document_id, dimensions, data_version, is_latest)
                VALUES %s ON CONFLICT DO NOTHING
            """, obs_tuples)

        n_obs = len(obs_tuples)
        n_ind = len(ind_id_map)
        total_obs += n_obs
        total_ind += n_ind
        total_ds += 1

        if (i + 1) % 100 == 0:
            logger.info("  Progress: %d/%d files, %d obs so far", i + 1, len(csv_files), total_obs)

    # Record pipeline run
    cur.execute("""
        INSERT INTO pipeline_runs (pipeline_name, started_at, completed_at, status,
            records_processed, records_inserted, metadata)
        VALUES ('full_pcbs_ingest', NOW(), NOW(), 'success', %s, %s, %s)
    """, (len(csv_files), total_obs,
          json.dumps({"patterns": dict(pattern_counts), "precision": dict(precision_counts)})))

    conn.commit()
    conn.close()

    return {
        "old_obs": old_obs,
        "new_obs": total_obs,
        "datasets": total_ds,
        "indicators": total_ind,
        "files": len(csv_files),
        "failed": failed_files,
        "patterns": dict(pattern_counts),
        "precision": dict(precision_counts),
    }


# ─── Step 3: Post-processing ─────────────────────────────

def run_post_processing():
    """Geography consolidation, dedup, temporal coverage, update frequency."""
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # Load geo map
    global GEO_MAP
    cur.execute("SELECT code, name_en, name_ar FROM geographies WHERE level = 'governorate'")
    for code, name_en, name_ar in cur.fetchall():
        GEO_MAP[name_en.lower()] = code
        GEO_MAP[name_ar] = code
        first_part = name_en.split("&")[0].strip().lower()
        if first_part != name_en.lower():
            GEO_MAP[first_part] = code

    # Geography reprocessing
    cur.execute("""
        SELECT i.id, i.name_en FROM indicators i
        JOIN dataset_sources ds ON i.dataset_id = ds.dataset_id
        JOIN sources s ON ds.source_id = s.id WHERE s.slug = 'pcbs'
    """)
    geo_updated = 0
    for ind_id, name_en in cur.fetchall():
        name_lower = name_en.lower().strip()
        for geo_name, geo_code in GEO_MAP.items():
            if name_lower == geo_name.lower():
                cur.execute("UPDATE observations SET geography_code = %s WHERE indicator_id = %s AND geography_code = 'PS'", (geo_code, ind_id))
                geo_updated += cur.rowcount
                break
    logger.info("Geography reprocessing: %d observations updated", geo_updated)

    # Indicator consolidation (governorate-named indicators)
    gov_names = set(GEO_MAP.keys())
    gov_names.add("jericho & al aghwar")
    gov_names.add("ramallah & al bireh")
    cur.execute("SELECT id, slug, name_en FROM datasets")
    for ds_id, ds_slug, ds_name in cur.fetchall():
        cur.execute("SELECT id, name_en FROM indicators WHERE dataset_id = %s", (ds_id,))
        indicators = cur.fetchall()
        if len(indicators) < 3:
            continue
        all_are_govs = all(ind_name.lower().strip() in gov_names for _, ind_name in indicators)
        if not all_are_govs:
            continue
        # Consolidate
        metric_name = re.sub(r",?\s*\d{4}\s*[-–—]\s*\d{4}\s*$", "", ds_name)
        metric_name = re.sub(r"\s+in\s+the\s+West\s+Bank\s*\*?\s*$", "", metric_name, flags=re.IGNORECASE).strip().rstrip(",").strip()
        metric_code = slugify(metric_name)[:100]
        old_ids = [ind_id for ind_id, _ in indicators]
        cur.execute("INSERT INTO indicators (dataset_id, code, name_en, name_ar) VALUES (%s, %s, %s, %s) ON CONFLICT (dataset_id, code) DO UPDATE SET updated_at = NOW() RETURNING id",
                    (ds_id, metric_code, metric_name, metric_name))
        new_id = cur.fetchone()[0]
        cur.execute("UPDATE observations SET indicator_id = %s WHERE indicator_id = ANY(%s)", (new_id, old_ids))
        delete_ids = [i for i in old_ids if i != new_id]
        if delete_ids:
            cur.execute("DELETE FROM indicators WHERE id = ANY(%s)", (delete_ids,))

    # Deduplication
    cur.execute("""
        DELETE FROM observations WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY indicator_id, geography_code, time_period, value, dimensions ORDER BY id
                ) as rn FROM observations
            ) d WHERE rn > 1
        )
    """)
    deduped = cur.rowcount
    logger.info("Deduplication: removed %d duplicate observations", deduped)

    # Strip footnote markers from ALL indicator names
    cur.execute("SELECT id, name_en FROM indicators")
    for ind_id, name in cur.fetchall():
        cleaned = clean_indicator_name(name)
        if cleaned != name:
            cur.execute("UPDATE indicators SET name_en = %s, name_ar = %s WHERE id = %s", (cleaned, cleaned, ind_id))

    # Set temporal coverage on all datasets
    cur.execute("""
        UPDATE datasets d SET
            temporal_coverage_start = sub.min_tp,
            temporal_coverage_end = sub.max_tp
        FROM (
            SELECT i.dataset_id, MIN(o.time_period) as min_tp, MAX(o.time_period) as max_tp
            FROM observations o JOIN indicators i ON o.indicator_id = i.id
            GROUP BY i.dataset_id
        ) sub WHERE d.id = sub.dataset_id
    """)

    # Set update_frequency based on dominant time precision
    cur.execute("""
        WITH prec AS (
            SELECT i.dataset_id, o.time_precision, COUNT(*) as cnt,
                   ROW_NUMBER() OVER (PARTITION BY i.dataset_id ORDER BY COUNT(*) DESC) as rn
            FROM observations o JOIN indicators i ON o.indicator_id = i.id
            GROUP BY i.dataset_id, o.time_precision
        )
        UPDATE datasets d SET update_frequency =
            CASE WHEN p.time_precision = 'month' THEN 'monthly'::update_frequency
                 WHEN p.time_precision = 'quarter' THEN 'quarterly'::update_frequency
                 WHEN p.time_precision = 'year' THEN 'annual'::update_frequency
                 ELSE 'irregular'::update_frequency END
        FROM prec p WHERE d.id = p.dataset_id AND p.rn = 1
    """)

    conn.commit()
    conn.close()
    return deduped


# ─── Main ────────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Step 1: Download
    logger.info("Step 1: Downloading new CSVs...")
    all_tables = asyncio.run(download_new_csvs())

    # Step 2: Ingest
    logger.info("Step 2: Full ingestion...")
    result = run_full_ingestion(all_tables)

    # Step 3: Post-processing
    logger.info("Step 3: Post-processing...")
    deduped = run_post_processing()

    # Final report
    print("\n" + "=" * 70)
    print("FULL PCBS INGESTION — FINAL REPORT")
    print("=" * 70)
    print(f"  CSV files processed:  {result['files']}")
    print(f"  Datasets created:     {result['datasets']}")
    print(f"  Indicators created:   {result['indicators']}")
    print(f"  Observations before:  {result['old_obs']:,}")
    print(f"  Observations after:   {result['new_obs']:,}")
    print(f"  Duplicates removed:   {deduped:,}")
    print(f"  Failed files:         {len(result['failed'])}")

    print(f"\n  By pattern:")
    for p, c in sorted(result["patterns"].items(), key=lambda x: -x[1]):
        print(f"    {p:30s} {c:4d} files")

    print(f"\n  By time precision:")
    for p, c in sorted(result["precision"].items(), key=lambda x: -x[1]):
        print(f"    {p:10s} {c:7,} observations")

    if result["failed"]:
        print(f"\n  Failed files:")
        for tid, err in result["failed"][:10]:
            print(f"    table_{tid}: {err[:80]}")

    # Show final DB totals
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM datasets")
    ds = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM indicators")
    ind = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM observations")
    obs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM observations WHERE time_precision = 'month'")
    monthly = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM observations WHERE time_precision = 'quarter'")
    quarterly = cur.fetchone()[0]

    print(f"\n  FINAL DATABASE TOTALS (incl. World Bank):")
    print(f"    Datasets:      {ds}")
    print(f"    Indicators:    {ind:,}")
    print(f"    Observations:  {obs:,}")
    print(f"    Monthly:       {monthly:,}")
    print(f"    Quarterly:     {quarterly:,}")

    # Show 5 sample datasets from different categories
    cur.execute("""
        SELECT d.name_en, c.name_en as category, d.update_frequency,
               d.temporal_coverage_start, d.temporal_coverage_end,
               (SELECT COUNT(*) FROM indicators i WHERE i.dataset_id = d.id) as ind_count,
               (SELECT COUNT(*) FROM observations o JOIN indicators i ON o.indicator_id = i.id WHERE i.dataset_id = d.id) as obs_count
        FROM datasets d
        LEFT JOIN categories c ON d.category_id = c.id
        WHERE d.status = 'published'
        ORDER BY obs_count DESC
        LIMIT 10
    """)
    print(f"\n  TOP 10 DATASETS BY OBSERVATION COUNT:")
    for name, cat, freq, start, end, inds, obs_c in cur.fetchall():
        yr_range = f"{start.year if start else '?'}-{end.year if end else '?'}"
        print(f"    {obs_c:>6,} obs | {inds:3d} ind | {freq or 'N/A':9s} | {yr_range:9s} | [{cat or 'N/A':20s}] {name[:55]}")

    conn.close()


if __name__ == "__main__":
    main()
