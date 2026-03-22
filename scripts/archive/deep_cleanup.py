#!/usr/bin/env python3
"""
Deep cleanup of indicator names, geography tagging, dataset names, and text normalization.

Fixes:
  1. Indicators that ARE geography names → merge into one indicator per dataset
  2. Compound "Geography - Category" indicators → split and retag
  3. Strip remaining years from dataset names, re-consolidate
  4. Fix capitalization and spelling variants
"""

import re
import sys
import argparse
from collections import defaultdict
import psycopg2

import os
DB_URL = os.environ.get("DATABASE_URL", "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine")

# ── Geography matching ──────────────────────────────────────────────────────

# Canonical geography names and their codes
GEO_MAP = {
    # National
    "palestine": "PS",
    "total": "PS",
    "*total": "PS",
    "state of palestine": "PS",
    # Territories
    "west bank": "PS-WBK",
    "gaza strip": "PS-GZA",
    # West Bank governorates
    "bethlehem": "PS-WBK-BTH",
    "hebron": "PS-WBK-HBN",
    "jenin": "PS-WBK-JEN",
    "jericho": "PS-WBK-JRH",
    "jericho & al-aghwar": "PS-WBK-JRH",
    "jericho & al -aghwar": "PS-WBK-JRH",
    "jericho and al-aghwar": "PS-WBK-JRH",
    "jericho & al aghwar": "PS-WBK-JRH",
    "jericho and al aghwar": "PS-WBK-JRH",
    "jerusalem": "PS-WBK-JEM",
    "j. jerusalem": "PS-WBK-JEM",
    "nablus": "PS-WBK-NBS",
    "qalqiliya": "PS-WBK-QQA",
    "ramallah": "PS-WBK-RBH",
    "ramallah & al-bireh": "PS-WBK-RBH",
    "ramallah and al-bireh": "PS-WBK-RBH",
    "ramallah & al bireh": "PS-WBK-RBH",
    "salfit": "PS-WBK-SLT",
    "safit": "PS-WBK-SLT",
    "tubas": "PS-WBK-TBS",
    "tubas & northern valleys": "PS-WBK-TBS",
    "tubas & the northern valleys": "PS-WBK-TBS",
    "tubas and northern valleys": "PS-WBK-TBS",
    "tulkarm": "PS-WBK-TKM",
    # Gaza governorates
    "gaza": "PS-GZA-GZA",
    "north gaza": "PS-GZA-NGZ",
    "khan yunis": "PS-GZA-KYS",
    "khan younis": "PS-GZA-KYS",
    "rafah": "PS-GZA-RFH",
    "deir al-balah": "PS-GZA-DEB",
    "deir al balah": "PS-GZA-DEB",
    "dier al balah": "PS-GZA-DEB",
    "dier al-balah": "PS-GZA-DEB",
}


def match_geography(text: str) -> tuple:
    """Try to match text to a geography. Returns (geo_code, remainder) or (None, text)."""
    s = text.strip().lower()

    # Exact match
    if s in GEO_MAP:
        return GEO_MAP[s], None

    # Match with trailing " - {number}" or " - -" (age/category suffix)
    m = re.match(r"^(.+?)\s*-\s*(\d+|-)$", s)
    if m:
        base = m.group(1).strip()
        suffix = m.group(2).strip()
        if base in GEO_MAP:
            return GEO_MAP[base], suffix if suffix != "-" else None

    # Match with leading geography: "Bethlehem - Appeal Court"
    for geo_name in sorted(GEO_MAP.keys(), key=len, reverse=True):
        if s.startswith(geo_name + " - "):
            remainder = text[len(geo_name) + 3:].strip()
            return GEO_MAP[geo_name], remainder

    return None, text


def derive_base_indicator_name(dataset_name: str) -> str:
    """Derive a meaningful indicator name from the dataset name.

    For datasets like "Child Marriages (Percentage of Female Under 18...)"
    the indicator should be something like "Child marriage rate".
    """
    s = dataset_name.strip()

    # Remove parenthetical details
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s)
    # Remove "by Region/Governorate" and similar
    s = re.sub(r"\s+by\s+.*$", "", s, flags=re.IGNORECASE)
    # Remove "in the West Bank" etc
    s = re.sub(r"\s+in\s+(?:the\s+)?(?:West Bank|Gaza Strip|Palestine)\*?", "", s, flags=re.IGNORECASE)
    # Clean up
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = re.sub(r"[,;:\s]+$", "", s)

    return s if s else dataset_name


# ── Fix 1: Indicators that ARE geography names ──────────────────────────────

def fix_geo_indicators(conn, dry_run=True):
    """Find indicators whose names are purely geography names and consolidate them."""
    cur = conn.cursor()

    # Get all indicators grouped by dataset
    cur.execute("""
        SELECT i.id, i.dataset_id, i.name_en, i.code, i.unit_en, i.dimensions,
               d.name_en as dataset_name
        FROM indicators i
        JOIN datasets d ON i.dataset_id = d.id
        ORDER BY i.dataset_id, i.name_en
    """)
    all_indicators = cur.fetchall()

    # Group by dataset
    by_dataset = defaultdict(list)
    for row in all_indicators:
        by_dataset[row[1]].append(row)

    total_merged = 0
    total_geo_fixed = 0
    datasets_affected = 0

    for dataset_id, indicators in by_dataset.items():
        geo_indicators = []  # (ind_id, geo_code, remainder, ind_row)
        non_geo_indicators = []

        for ind in indicators:
            ind_id, ds_id, name_en, code, unit_en, dims, ds_name = ind
            geo_code, remainder = match_geography(name_en)

            if geo_code is not None and remainder is None:
                # Pure geography name
                geo_indicators.append((ind_id, geo_code, None, ind))
            elif geo_code is not None and remainder is not None:
                # Geography with suffix (number or category)
                geo_indicators.append((ind_id, geo_code, remainder, ind))
            else:
                non_geo_indicators.append(ind)

        if not geo_indicators:
            continue

        # Check: are ALL or MOST indicators geography names?
        geo_ratio = len(geo_indicators) / len(indicators)

        if geo_ratio < 0.5:
            # Less than half are geo names — might be a mixed dataset
            # Only process the pure geo ones
            pass

        datasets_affected += 1
        dataset_name = indicators[0][6]  # ds_name

        # Group geo indicators by their remainder (the non-geo part)
        # Pure geo names have remainder=None, they all merge into one base indicator
        groups = defaultdict(list)
        for ind_id, geo_code, remainder, ind_row in geo_indicators:
            # For pure geo names (remainder=None), key is "base"
            # For "Geography - Number", key is the number
            key = remainder if remainder else "__base__"
            groups[key].append((ind_id, geo_code, ind_row))

        for group_key, members in groups.items():
            if group_key == "__base__":
                # Pure geography indicators → merge into one "base" indicator
                base_name = derive_base_indicator_name(dataset_name)
            else:
                # Geography with suffix → the suffix might be meaningful
                # Try to interpret: if it's a number, might be age threshold
                if group_key.isdigit():
                    base_name = f"{derive_base_indicator_name(dataset_name)} (age {group_key})"
                else:
                    base_name = group_key

            if len(members) <= 1 and not dry_run:
                # Single indicator — just rename and retag geography
                ind_id, geo_code, ind_row = members[0]
                cur.execute("UPDATE indicators SET name_en = %s WHERE id = %s",
                            (base_name, ind_id))
                cur.execute("UPDATE observations SET geography_code = %s WHERE indicator_id = %s",
                            (geo_code, ind_id))
                total_geo_fixed += 1
                continue

            if dry_run:
                total_merged += len(members) - 1
                total_geo_fixed += len(members)
                continue

            # Pick canonical (most observations)
            cur.execute("""
                SELECT indicator_id, COUNT(*) as cnt FROM observations
                WHERE indicator_id = ANY(%s)
                GROUP BY indicator_id ORDER BY cnt DESC
            """, ([m[0] for m in members],))
            obs_counts = {row[0]: row[1] for row in cur.fetchall()}

            canonical_id = max(members, key=lambda m: obs_counts.get(m[0], 0))[0]
            canonical_geo = [m[1] for m in members if m[0] == canonical_id][0]

            # Update canonical name and geography
            new_code = re.sub(r"[^\w-]", "-", base_name.lower())[:95]
            new_code = re.sub(r"-{2,}", "-", new_code).strip("-")

            # Ensure code uniqueness
            cur.execute("SELECT COUNT(*) FROM indicators WHERE dataset_id = %s AND code = %s AND id != %s",
                        (dataset_id, new_code, canonical_id))
            if cur.fetchone()[0] > 0:
                new_code = f"{new_code}-{canonical_id}"

            cur.execute("UPDATE indicators SET name_en = %s, code = %s WHERE id = %s",
                        (base_name, new_code, canonical_id))
            cur.execute("UPDATE observations SET geography_code = %s WHERE indicator_id = %s",
                        (canonical_geo, canonical_id))

            # Merge others
            others = [m for m in members if m[0] != canonical_id]
            for ind_id, geo_code, ind_row in others:
                # Retag geography
                cur.execute("UPDATE observations SET geography_code = %s WHERE indicator_id = %s",
                            (geo_code, ind_id))
                # Move observations to canonical
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
                """, (canonical_id, ind_id, canonical_id))
                cur.execute("DELETE FROM observations WHERE indicator_id = %s", (ind_id,))
                cur.execute("DELETE FROM indicators WHERE id = %s", (ind_id,))
                total_merged += 1

            total_geo_fixed += len(members)

        if not dry_run:
            conn.commit()

    print(f"\n  Fix 1: Geography-as-indicator")
    print(f"    Datasets affected: {datasets_affected}")
    print(f"    Indicators with geo fixed: {total_geo_fixed}")
    print(f"    Indicators merged away: {total_merged}")

    cur.close()
    return total_merged


# ── Fix 2: Clean compound indicators ────────────────────────────────────────

def fix_compound_indicators(conn, dry_run=True):
    """Fix indicators with 'Geography - Category' pattern where geography wasn't detected
    in Fix 1 because the category part prevented exact matching."""
    cur = conn.cursor()

    # Find indicators with " - " where the LEFT side is a geography
    cur.execute("""
        SELECT i.id, i.dataset_id, i.name_en, i.code
        FROM indicators i
        WHERE i.name_en LIKE '% - %'
        ORDER BY i.dataset_id, i.name_en
    """)

    fixed = 0
    for ind_id, ds_id, name_en, code in cur.fetchall():
        parts = name_en.split(" - ", 1)
        if len(parts) != 2:
            continue

        left, right = parts[0].strip(), parts[1].strip()
        geo_code, _ = match_geography(left)

        if geo_code is None:
            continue

        # Left side is geography, right side is the real indicator name
        if not dry_run:
            cur.execute("UPDATE indicators SET name_en = %s WHERE id = %s", (right, ind_id))
            cur.execute("UPDATE observations SET geography_code = %s WHERE indicator_id = %s AND geography_code = 'PS'",
                        (geo_code, ind_id))
            fixed += 1
        else:
            fixed += 1

    if not dry_run:
        conn.commit()

    print(f"\n  Fix 2: Compound indicators (Geo - Category)")
    print(f"    Fixed: {fixed}")

    cur.close()
    return fixed


# ── Fix 3: Strip years from dataset names + re-consolidate ──────────────────

def strip_years_from_names(conn, dry_run=True):
    """Remove trailing year patterns from dataset names."""
    cur = conn.cursor()

    YEAR_PATTERNS = [
        # "for the Years 2019, 2020" (must be before simpler patterns)
        r"\s+for\s+the\s+[Yy]ears?\s+.*$",
        # Trailing year range: ", 2006-2019" or ", 2006 - 2019" or ", 2000-2020"
        r",?\s*\d{4}\s*[-–]\s*\d{4}$",
        # Trailing "2022/2023"
        r",?\s*\d{4}\s*/\s*\d{4}$",
        # Complex: "1997-2001, 2004-2007, 2010-2019"
        r"(?:\s*,?\s*\d{4}\s*[-–]\s*\d{4})+$",
        # Trailing comma-separated years: ", 2018, 2019, 2020"
        r"(?:,\s*\d{4})+$",
        # Trailing single year: ", 2019" or ", 2020"
        r",\s*\d{4}$",
        # Trailing year after space (only if preceded by comma or paren)
        r"(?<=[\),])\s+\d{4}$",
    ]

    cur.execute("SELECT id, name_en FROM datasets ORDER BY name_en")
    datasets = cur.fetchall()

    changes = []
    for ds_id, name in datasets:
        new_name = name
        for pat in YEAR_PATTERNS:
            new_name = re.sub(pat, "", new_name).strip()
        # Clean trailing punctuation
        new_name = re.sub(r"[,;:\s]+$", "", new_name)

        if new_name != name and len(new_name) > 10:  # sanity check
            changes.append((ds_id, name, new_name))

    if not dry_run:
        for ds_id, old_name, new_name in changes:
            new_slug = re.sub(r"[^\w\s-]", "", new_name.lower())
            new_slug = re.sub(r"[\s_]+", "-", new_slug)
            new_slug = re.sub(r"-{2,}", "-", new_slug).strip("-")[:200]

            cur.execute("SELECT COUNT(*) FROM datasets WHERE slug = %s AND id != %s",
                        (new_slug, ds_id))
            if cur.fetchone()[0] > 0:
                new_slug = f"{new_slug}-{ds_id}"

            cur.execute("UPDATE datasets SET name_en = %s, slug = %s WHERE id = %s",
                        (new_name, new_slug, ds_id))
        conn.commit()

    print(f"\n  Fix 3: Year stripping from dataset names")
    print(f"    Names changed: {len(changes)}")
    if changes:
        for _, old, new in changes[:5]:
            print(f"      \"{old[:70]}\" → \"{new[:70]}\"")

    cur.close()
    return len(changes)


# ── Fix 4: Capitalization and spelling normalization ─────────────────────────

# Text replacements for indicators and dataset names
TEXT_FIXES = [
    # Capitalization
    (r"\bwest Bank\b", "West Bank"),
    (r"\bgaza strip\b", "Gaza Strip", re.IGNORECASE),
    # Spelling standardization
    (r"\bDier al Balah\b", "Deir Al-Balah", re.IGNORECASE),
    (r"\bDeir al Balah\b", "Deir Al-Balah", re.IGNORECASE),
    (r"\bDeir Al Balah\b", "Deir Al-Balah", re.IGNORECASE),
    (r"\bKhan Younis\b", "Khan Yunis", re.IGNORECASE),
    (r"\bJericho & Al -Aghwar\b", "Jericho & Al-Aghwar"),
    (r"\bJericho and Al[ -]?Aghwar\b", "Jericho & Al-Aghwar"),
    (r"\bTubas & the Northern Valleys\b", "Tubas & Northern Valleys"),
    (r"\bTubas and Northern Valleys\b", "Tubas & Northern Valleys"),
    (r"\bRamallah and Al-Bireh\b", "Ramallah & Al-Bireh"),
    (r"\bRamallah & Al Bireh\b", "Ramallah & Al-Bireh"),
    # Backslashes to forward slashes
    (r"\\", "/"),
    # Double spaces
    (r"\s{2,}", " "),
    # Fix "Safit" → "Salfit"
    (r"\bSafit\b", "Salfit"),
]


def fix_text_normalization(conn, dry_run=True):
    """Fix capitalization, spelling, and special characters."""
    cur = conn.cursor()

    # Fix indicator names
    cur.execute("SELECT id, name_en FROM indicators ORDER BY id")
    indicators = cur.fetchall()

    ind_fixed = 0
    for ind_id, name in indicators:
        new_name = name
        for fix in TEXT_FIXES:
            pattern, replacement = fix[0], fix[1]
            flags = fix[2] if len(fix) > 2 else 0
            new_name = re.sub(pattern, replacement, new_name, flags=flags)

        if new_name != name:
            ind_fixed += 1
            if not dry_run:
                cur.execute("UPDATE indicators SET name_en = %s WHERE id = %s",
                            (new_name, ind_id))

    # Fix dataset names
    cur.execute("SELECT id, name_en FROM datasets ORDER BY id")
    datasets = cur.fetchall()

    ds_fixed = 0
    for ds_id, name in datasets:
        new_name = name
        for fix in TEXT_FIXES:
            pattern, replacement = fix[0], fix[1]
            flags = fix[2] if len(fix) > 2 else 0
            new_name = re.sub(pattern, replacement, new_name, flags=flags)

        if new_name != name:
            ds_fixed += 1
            if not dry_run:
                cur.execute("UPDATE datasets SET name_en = %s WHERE id = %s",
                            (new_name, ds_id))

    if not dry_run:
        conn.commit()

    print(f"\n  Fix 4: Text normalization")
    print(f"    Indicators fixed: {ind_fixed}")
    print(f"    Datasets fixed: {ds_fixed}")

    cur.close()
    return ind_fixed + ds_fixed


# ── Re-consolidation after name fixes ────────────────────────────────────────

def reconsolidate_indicators(conn, dry_run=True):
    """After geo decomposition, merge indicators with identical names within a dataset."""
    cur = conn.cursor()

    # Find datasets with duplicate indicator names
    cur.execute("""
        SELECT dataset_id, LOWER(TRIM(name_en)) as lname, COUNT(*) as cnt,
               array_agg(id ORDER BY id) as ids
        FROM indicators
        GROUP BY dataset_id, LOWER(TRIM(name_en))
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
    """)

    dups = cur.fetchall()
    total_merged = 0

    for ds_id, lname, cnt, ids in dups:
        if dry_run:
            total_merged += cnt - 1
            continue

        canonical_id = ids[0]
        for other_id in ids[1:]:
            # Move observations
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
            """, (canonical_id, other_id, canonical_id))
            cur.execute("DELETE FROM observations WHERE indicator_id = %s", (other_id,))
            cur.execute("DELETE FROM indicators WHERE id = %s", (other_id,))
            total_merged += 1

    if not dry_run:
        conn.commit()

    print(f"\n  Post-fix: Indicator reconsolidation")
    print(f"    Duplicate indicator groups: {len(dups)}")
    print(f"    Indicators merged: {total_merged}")

    cur.close()
    return total_merged


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Deep cleanup of indicators and datasets")
    parser.add_argument("--execute", action="store_true", help="Actually modify the database")
    args = parser.parse_args()
    dry_run = not args.execute

    conn = psycopg2.connect(DB_URL)

    # Get before counts
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM datasets")
    ds_before = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM indicators")
    ind_before = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM observations")
    obs_before = cur.fetchone()[0]
    cur.close()

    print(f"{'='*60}")
    print(f"DEEP CLEANUP {'(DRY RUN)' if dry_run else '(EXECUTING)'}")
    print(f"{'='*60}")
    print(f"Before: {ds_before} datasets, {ind_before:,} indicators, {obs_before:,} observations")

    # Run fixes in order
    fix_geo_indicators(conn, dry_run)
    fix_compound_indicators(conn, dry_run)
    reconsolidate_indicators(conn, dry_run)
    strip_years_from_names(conn, dry_run)
    fix_text_normalization(conn, dry_run)

    if not dry_run:
        # Get after counts
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM datasets")
        ds_after = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM indicators")
        ind_after = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM observations")
        obs_after = cur.fetchone()[0]
        cur.close()

        print(f"\n{'='*60}")
        print(f"RESULTS")
        print(f"{'='*60}")
        print(f"  Datasets:     {ds_before} → {ds_after}")
        print(f"  Indicators:   {ind_before:,} → {ind_after:,} (-{ind_before - ind_after:,})")
        print(f"  Observations: {obs_before:,} → {obs_after:,}")
    else:
        print(f"\n{'='*60}")
        print(f"DRY RUN — no changes. Run with --execute to apply.")

    conn.close()


if __name__ == "__main__":
    main()
