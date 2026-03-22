"""Consolidate per-governorate indicators into single indicators.

For datasets where each indicator IS a governorate name (e.g., "Bethlehem",
"Hebron") and each has observations tagged to that governorate, this script:

1. Finds datasets where ALL indicators are governorate names
2. Creates ONE consolidated indicator per dataset (named from the dataset title)
3. Re-points all observations to the consolidated indicator
4. Deletes the old per-governorate indicator records

Usage:
    python scripts/consolidate_indicators.py [--dry-run]
"""

import argparse
import logging
import re
import psycopg2

logger = logging.getLogger(__name__)
import os
DB_URL = os.environ.get("DATABASE_URL", "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine")


def extract_metric_name(dataset_name: str) -> str:
    """Extract the core metric name from a dataset title.

    'Reported Criminal Offenses in the West Bank, 1997-2018'
    → 'Reported Criminal Offenses'
    """
    name = dataset_name
    # Strip year ranges
    name = re.sub(r",?\s*\d{4}\s*[-–—]\s*\d{4}\s*$", "", name)
    # Strip "in the West Bank" and similar suffixes
    name = re.sub(r"\s+in\s+the\s+West\s+Bank\s*\*?\s*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+in\s+Palestine\s*\*?\s*$", "", name, flags=re.IGNORECASE)
    return name.strip().rstrip(",").strip()


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:100].strip("-")


def run(dry_run: bool = False):
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # Load all governorate names
    cur.execute("SELECT name_en FROM geographies WHERE level = 'governorate'")
    gov_names = {row[0] for row in cur.fetchall()}
    # Add variant spellings from indicator data
    gov_names.add("Jericho & Al Aghwar")
    gov_names.add("Ramallah & Al Bireh")
    logger.info("Known governorate names: %d", len(gov_names))

    # Find datasets where ALL indicators are governorate names
    cur.execute("""
        SELECT d.id, d.slug, d.name_en
        FROM datasets d
        WHERE EXISTS (
            SELECT 1 FROM indicators i WHERE i.dataset_id = d.id
        )
        AND NOT EXISTS (
            SELECT 1 FROM indicators i
            WHERE i.dataset_id = d.id
            AND i.name_en NOT IN %s
        )
    """, (tuple(gov_names),))

    datasets = cur.fetchall()
    logger.info("Found %d datasets with all-governorate indicators", len(datasets))

    total_consolidated = 0
    total_obs_moved = 0

    for ds_id, ds_slug, ds_name in datasets:
        metric_name = extract_metric_name(ds_name)
        metric_code = slugify(metric_name)
        logger.info("Dataset: %s", ds_name)
        logger.info("  Metric name: %s (code: %s)", metric_name, metric_code)

        # Get existing per-governorate indicators
        cur.execute(
            "SELECT id, name_en FROM indicators WHERE dataset_id = %s ORDER BY name_en",
            (ds_id,),
        )
        old_indicators = cur.fetchall()
        old_ids = [row[0] for row in old_indicators]
        logger.info("  Old indicators: %d (%s)",
                     len(old_indicators),
                     ", ".join(r[1] for r in old_indicators[:5]) + ("..." if len(old_indicators) > 5 else ""))

        # Count observations
        cur.execute(
            "SELECT COUNT(*) FROM observations WHERE indicator_id = ANY(%s)",
            (old_ids,),
        )
        obs_count = cur.fetchone()[0]
        logger.info("  Observations to move: %d", obs_count)

        if dry_run:
            logger.info("  [DRY RUN] Would consolidate %d indicators into '%s'",
                        len(old_indicators), metric_name)
            total_consolidated += len(old_indicators)
            total_obs_moved += obs_count
            continue

        # Create the consolidated indicator
        cur.execute("""
            INSERT INTO indicators (dataset_id, code, name_en, name_ar)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (dataset_id, code) DO UPDATE SET
                name_en = EXCLUDED.name_en, updated_at = NOW()
            RETURNING id
        """, (ds_id, metric_code, metric_name, metric_name))
        new_ind_id = cur.fetchone()[0]
        logger.info("  Created consolidated indicator id=%d: %s", new_ind_id, metric_name)

        # Move all observations to the new indicator
        cur.execute(
            "UPDATE observations SET indicator_id = %s WHERE indicator_id = ANY(%s)",
            (new_ind_id, old_ids),
        )
        moved = cur.rowcount
        logger.info("  Moved %d observations", moved)
        total_obs_moved += moved

        # Delete old per-governorate indicators (skip the new one if it was one of them)
        delete_ids = [i for i in old_ids if i != new_ind_id]
        if delete_ids:
            cur.execute(
                "DELETE FROM indicators WHERE id = ANY(%s)",
                (delete_ids,),
            )
            deleted = cur.rowcount
            logger.info("  Deleted %d old indicator records", deleted)
            total_consolidated += deleted

    if not dry_run:
        # Record the migration
        cur.execute("""
            INSERT INTO pipeline_runs
            (pipeline_name, started_at, completed_at, status,
             records_processed, records_updated, metadata)
            VALUES ('indicator_consolidation', NOW(), NOW(), 'success', %s, %s,
                    '{"type": "indicator_consolidation"}')
        """, (total_consolidated, total_obs_moved))
        conn.commit()

    conn.close()

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Consolidation complete:")
    print(f"  Datasets processed: {len(datasets)}")
    print(f"  Indicators consolidated: {total_consolidated}")
    print(f"  Observations re-pointed: {total_obs_moved}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run(dry_run=args.dry_run)
