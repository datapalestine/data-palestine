#!/usr/bin/env python3
"""
Decompose multi-dimensional indicator names into proper structure.

Handles patterns like:
  "Arson - Bethlehem"       → indicator "Arson", geography = Bethlehem
  "Female - Nablus"         → indicator base, dimensions={"gender": "Female"}, geography = Nablus
  "Theft - Total"           → indicator "Theft", geography = national (PS)
  "CPI - % Change Palestine"→ indicator "CPI (% Change)", geography = Palestine

Steps:
  1. Load governorate names and build a matching dictionary
  2. For each indicator, detect if suffix after " - " is a geography
  3. Consolidate: merge indicators that only differ by geography
  4. Update observation geography_codes
"""

import re
import sys
import argparse
from collections import defaultdict
from dataclasses import dataclass
import psycopg2

import os
DB_URL = os.environ.get("DATABASE_URL", "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine")

# Geography name → code mapping (including common variants)
GEO_ALIASES = {
    # Governorates
    "bethlehem": "PS-WBK-BTH",
    "hebron": "PS-WBK-HBN",
    "jenin": "PS-WBK-JEN",
    "jericho & al aghwar": "PS-WBK-JRH",
    "jericho & al-aghwar": "PS-WBK-JRH",
    "jericho and al aghwar": "PS-WBK-JRH",
    "jericho and al-aghwar": "PS-WBK-JRH",
    "jericho": "PS-WBK-JRH",
    "jerusalem": "PS-WBK-JEM",
    "j. jerusalem": "PS-WBK-JEM",
    "khan yunis": "PS-GZA-KYS",
    "khan younis": "PS-GZA-KYS",
    "nablus": "PS-WBK-NBS",
    "north gaza": "PS-GZA-NGZ",
    "gaza": "PS-GZA-GZA",
    "qalqiliya": "PS-WBK-QQA",
    "rafah": "PS-GZA-RFH",
    "ramallah & al-bireh": "PS-WBK-RBH",
    "ramallah and al-bireh": "PS-WBK-RBH",
    "ramallah & al bireh": "PS-WBK-RBH",
    "ramallah": "PS-WBK-RBH",
    "salfit": "PS-WBK-SLT",
    "safit": "PS-WBK-SLT",  # typo in data
    "tubas": "PS-WBK-TBS",
    "tubas & northern valleys": "PS-WBK-TBS",
    "tubas and northern valleys": "PS-WBK-TBS",
    "tulkarm": "PS-WBK-TKM",
    "deir al-balah": "PS-GZA-DEB",
    "deir al balah": "PS-GZA-DEB",
    # Territories
    "west bank": "PS-WBK",
    "gaza strip": "PS-GZA",
    # National
    "palestine": "PS",
    "total": "PS",  # "Total" means national aggregate
    "*total": "PS",
}

# Region suffixes that appear in "Price {Region}" patterns
REGION_PRICE_PATTERNS = {
    "price palestine": "PS",
    "price west bank": "PS-WBK",
    "price gaza strip": "PS-GZA",
    "price jerusalem j": "PS-WBK-JEM",
}

# Dimension category detectors
GENDER_VALUES = {"male", "female", "males", "females", "both sexes"}
COURT_STAGE_VALUES = {"submitted", "decided", "carried from last year",
                      "pending for the following year", "total pending cases",
                      "received cases"}


def detect_suffix_type(suffix: str) -> tuple:
    """Detect what type of suffix this is.
    Returns: (type, normalized_value)
    type is one of: 'geography', 'gender', 'court_stage', 'pct_change', 'other'
    """
    s = suffix.strip().lower()

    # Check geography
    if s in GEO_ALIASES:
        return ("geography", GEO_ALIASES[s])

    # Check "% Change {geography}" pattern
    pct_match = re.match(r"% ?change\s+(.+)", s)
    if pct_match:
        geo_part = pct_match.group(1).strip().lower()
        if geo_part in GEO_ALIASES:
            return ("pct_change_geo", GEO_ALIASES[geo_part])

    # Check "Percent Change %" and similar
    if "% change" in s or "percent change" in s:
        return ("pct_change", suffix.strip())

    # Check gender
    if s in GENDER_VALUES:
        return ("gender", suffix.strip())

    # Check court stages
    if s in COURT_STAGE_VALUES:
        return ("court_stage", suffix.strip())

    return ("other", suffix.strip())


def process_dataset(cur, dataset_id: str, dataset_name: str, dry_run: bool = True):
    """Process all indicators in a dataset to decompose geography from names."""

    # Load indicators
    cur.execute("""
        SELECT i.id, i.code, i.name_en, i.name_ar, i.unit_en, i.dimensions,
               COUNT(o.id) as obs_count
        FROM indicators i
        LEFT JOIN observations o ON o.indicator_id = i.id
        WHERE i.dataset_id = %s
        GROUP BY i.id, i.code, i.name_en, i.name_ar, i.unit_en, i.dimensions
        ORDER BY i.name_en
    """, (dataset_id,))
    indicators = cur.fetchall()

    if not indicators:
        return 0, 0

    # Analyze: check if indicators have " - {geography}" pattern
    geo_indicators = []  # (indicator_id, base_name, geo_code, suffix_type)
    non_geo_indicators = []

    for ind in indicators:
        ind_id, code, name_en, name_ar, unit_en, dims, obs_count = ind

        if " - " not in name_en:
            non_geo_indicators.append(ind)
            continue

        # Get the suffix (after last " - ")
        parts = name_en.rsplit(" - ", 1)
        if len(parts) != 2:
            non_geo_indicators.append(ind)
            continue

        base_name, suffix = parts[0].strip(), parts[1].strip()
        suffix_type, value = detect_suffix_type(suffix)

        if suffix_type == "geography":
            geo_indicators.append((ind_id, base_name, value, code, name_ar, unit_en, dims, obs_count))
        elif suffix_type == "pct_change_geo":
            # "CPI - % Change Palestine" → indicator "CPI (% Change)", geo = PS
            new_name = f"{base_name} (% Change)"
            geo_indicators.append((ind_id, new_name, value, code, name_ar, "percent", dims, obs_count))
        else:
            non_geo_indicators.append(ind)

    if not geo_indicators:
        return len(indicators), len(indicators)

    # Group by base_name to consolidate
    groups = defaultdict(list)
    for ind_id, base_name, geo_code, code, name_ar, unit_en, dims, obs_count in geo_indicators:
        groups[base_name.lower()].append({
            "id": ind_id, "base_name": base_name, "geo_code": geo_code,
            "code": code, "name_ar": name_ar, "unit_en": unit_en,
            "dims": dims, "obs_count": obs_count
        })

    indicators_before = len(indicators)
    indicators_merged = 0

    if dry_run:
        for base_key, group in groups.items():
            if len(group) > 1:
                indicators_merged += len(group) - 1
        return indicators_before, indicators_before - indicators_merged

    # Execute: for each group, keep one canonical indicator, merge others
    for base_key, group in groups.items():
        if not group:
            continue

        # Pick the one with the most observations as canonical
        canonical = max(group, key=lambda g: g["obs_count"])
        others = [g for g in group if g["id"] != canonical["id"]]

        # Rename canonical to base name
        new_code = re.sub(r"[^\w-]", "-", canonical["base_name"].lower())[:100]
        new_code = re.sub(r"-{2,}", "-", new_code).strip("-")

        # Check code uniqueness
        cur.execute("""
            SELECT COUNT(*) FROM indicators
            WHERE dataset_id = %s AND code = %s AND id != %s
        """, (dataset_id, new_code, canonical["id"]))
        if cur.fetchone()[0] > 0:
            new_code = f"{new_code}-{canonical['id']}"

        cur.execute("""
            UPDATE indicators SET name_en = %s, code = %s
            WHERE id = %s
        """, (canonical["base_name"], new_code, canonical["id"]))

        # Update geography on canonical's observations
        cur.execute("""
            UPDATE observations SET geography_code = %s
            WHERE indicator_id = %s AND geography_code = 'PS'
        """, (canonical["geo_code"], canonical["id"]))

        # Merge others into canonical
        for other in others:
            # Update geography on other's observations, then re-point to canonical
            cur.execute("""
                UPDATE observations SET geography_code = %s
                WHERE indicator_id = %s AND geography_code = 'PS'
            """, (other["geo_code"], other["id"]))

            # Re-point observations to canonical, avoid duplicates
            cur.execute("""
                UPDATE observations SET indicator_id = %s
                WHERE indicator_id = %s
                  AND NOT EXISTS (
                    SELECT 1 FROM observations o2
                    WHERE o2.indicator_id = %s
                      AND o2.geography_code = observations.geography_code
                      AND o2.time_period = observations.time_period
                      AND o2.dimensions = observations.dimensions
                  )
            """, (canonical["id"], other["id"], canonical["id"]))

            # Delete remaining dups and the old indicator
            cur.execute("DELETE FROM observations WHERE indicator_id = %s", (other["id"],))
            cur.execute("DELETE FROM indicators WHERE id = %s", (other["id"],))
            indicators_merged += 1

    return indicators_before, indicators_before - indicators_merged


def main():
    parser = argparse.ArgumentParser(description="Decompose multi-dimensional indicator names")
    parser.add_argument("--execute", action="store_true", help="Actually modify the database")
    parser.add_argument("--dataset-id", type=int, help="Process only this dataset")
    args = parser.parse_args()
    dry_run = not args.execute

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Get before counts
    cur.execute("SELECT COUNT(*) FROM indicators")
    total_indicators_before = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM observations")
    total_obs_before = cur.fetchone()[0]

    # Load all datasets
    if args.dataset_id:
        cur.execute("SELECT id, name_en FROM datasets WHERE id = %s", (args.dataset_id,))
    else:
        cur.execute("SELECT id, name_en FROM datasets ORDER BY name_en")
    datasets = cur.fetchall()

    print(f"Processing {len(datasets)} datasets...")
    print(f"Before: {total_indicators_before:,} indicators, {total_obs_before:,} observations")
    print()

    results = []
    total_before = 0
    total_after = 0

    for ds_id, ds_name in datasets:
        before, after = process_dataset(cur, ds_id, ds_name, dry_run=dry_run)
        reduced = before - after
        if reduced > 0:
            results.append((ds_name, before, after, reduced))
        total_before += before
        total_after += after

        if not dry_run and reduced > 0:
            conn.commit()

    # Sort by reduction amount
    results.sort(key=lambda r: r[3], reverse=True)

    print(f"{'='*80}")
    print(f"TOP 20 MOST AFFECTED DATASETS")
    print(f"{'='*80}")
    for name, before, after, reduced in results[:20]:
        print(f"  {before:>5} → {after:>5} ({-reduced:>5}) | {name[:75]}")

    total_reduced = total_before - total_after
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"  Datasets processed: {len(datasets)}")
    print(f"  Datasets with reductions: {len(results)}")
    print(f"  Indicators: {total_before:,} → {total_after:,} ({-total_reduced:,})")

    if dry_run:
        print(f"\nDRY RUN — no changes made. Run with --execute to apply.")
    else:
        # Get final counts
        cur.execute("SELECT COUNT(*) FROM indicators")
        final_ind = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM observations")
        final_obs = cur.fetchone()[0]
        print(f"\n  Final indicators: {final_ind:,}")
        print(f"  Final observations: {final_obs:,}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
