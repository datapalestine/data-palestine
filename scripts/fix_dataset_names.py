#!/usr/bin/env python3
"""Fix dataset names by matching table IDs to PCBS discovery titles.

Reads pcbs_discovery JSON files to build a table_id → title mapping,
then updates datasets whose names are raw filenames (table_XXXX.csv).

Usage:
    python scripts/fix_dataset_names.py                    # dry run
    python scripts/fix_dataset_names.py --execute          # apply changes
"""

import argparse
import json
import os
import re
import glob
import psycopg2

DB_URL = os.environ.get("DATABASE_URL", "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine")


def clean_pcbs_title(title: str) -> str:
    """Clean a PCBS title into a dataset name."""
    # Remove "PCBS | " or "PCBS| " prefix
    title = re.sub(r"^PCBS\s*\|\s*", "", title)
    # Remove "Table N: " prefix
    title = re.sub(r"^Table\s+\d+[:\s]+", "", title)
    # Remove trailing year ranges like ", 2019" or ", 1997-2019"
    title = re.sub(r",?\s*\d{4}\s*[-–]\s*\d{4}\s*$", "", title)
    title = re.sub(r",?\s*\d{4}\s*$", "", title)
    # Remove "in Palestine" / "in Palestine*" (redundant for this platform)
    title = re.sub(r"\s+in Palestine\*?\s*", " ", title)
    # Clean up whitespace
    title = re.sub(r"\s+", " ", title).strip()
    # Remove trailing punctuation
    title = title.rstrip(",. ")
    return title


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")[:200]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Apply changes (default: dry run)")
    parser.add_argument("--data-dir", default="/data", help="Data directory")
    args = parser.parse_args()

    # Build table_id → title mapping from all discovery files
    title_map = {}
    discovery_files = glob.glob(os.path.join(args.data_dir, "pcbs_discovery*.json"))
    if not discovery_files:
        # Try local paths
        discovery_files = glob.glob("data/pcbs_discovery*.json")

    for df in discovery_files:
        with open(df) as f:
            entries = json.load(f)
        for entry in entries:
            tid = entry.get("table_id")
            title = entry.get("title", "")
            if tid and title:
                cleaned = clean_pcbs_title(title)
                if cleaned and len(cleaned) > 5:
                    title_map[int(tid)] = cleaned

    print(f"Loaded {len(title_map)} title mappings from {len(discovery_files)} discovery files")

    # Connect to database
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Find datasets with raw filename names
    cur.execute("""
        SELECT id, name_en, slug
        FROM datasets
        WHERE name_en ~ '^[Tt]able[ _]\\d+' OR name_en ~ '.*\\.csv$'
        ORDER BY name_en
    """)
    raw_datasets = cur.fetchall()
    print(f"Found {len(raw_datasets)} datasets with raw filename names")

    updated = 0
    not_found = 0

    for ds_id, name_en, slug in raw_datasets:
        # Extract table_id from name
        match = re.search(r"(\d+)", name_en)
        if not match:
            continue
        table_id = int(match.group(1))

        if table_id in title_map:
            new_name = title_map[table_id]
            new_slug = slugify(new_name)

            # Check for slug collision
            cur.execute("SELECT id FROM datasets WHERE slug = %s AND id != %s", (new_slug, ds_id))
            if cur.fetchone():
                new_slug = f"{new_slug}-{table_id}"

            if args.execute:
                cur.execute(
                    "UPDATE datasets SET name_en = %s, name_ar = %s, slug = %s WHERE id = %s",
                    (new_name, new_name, new_slug, ds_id),
                )
            updated += 1
            if updated <= 20:
                print(f"  {name_en} → {new_name}")
        else:
            not_found += 1
            if not_found <= 10:
                print(f"  No title for table_id={table_id} ({name_en})")

    if args.execute:
        conn.commit()
        print(f"\nAPPLIED: {updated} datasets renamed, {not_found} without titles")
    else:
        conn.rollback()
        print(f"\nDRY RUN: {updated} would be renamed, {not_found} without titles")
        print("Run with --execute to apply")

    conn.close()


if __name__ == "__main__":
    main()
