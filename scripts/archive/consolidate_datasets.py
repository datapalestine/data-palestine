#!/usr/bin/env python3
"""
Consolidate duplicate PCBS datasets that differ only by time period.

E.g., 60+ "Average Consumer Prices for selected commodities by region for {Month} {Year}"
become ONE dataset: "Average Consumer Prices for Selected Commodities by Region"

Steps:
  1. Extract base topic name by stripping time suffixes
  2. Group datasets by base topic
  3. Dry run: print proposed groupings
  4. Merge: consolidate indicators + observations under canonical dataset
  5. Clean up names
"""

import re
import sys
import argparse
from collections import defaultdict
from dataclasses import dataclass, field
import psycopg2
from psycopg2.extras import DictCursor

import os
DB_URL = os.environ.get("DATABASE_URL", "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine")

# ── Step 1: Extract base topic name ──────────────────────────────────────────

# Month names in all forms
MONTHS = (
    r"January|February|March|April|May|June|July|August|September|October|November|December"
    r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
    r"|Februray|Febuary"  # common PCBS typos
)
QUARTERS = r"First Quarter|Second Quarter|Third Quarter|Fourth Quarter|Q[1-4]"

def extract_base_name(name: str) -> str:
    """Strip time-specific suffixes from a dataset name to find the base topic."""
    if not name:
        return name

    s = name.strip()

    # Patterns to strip (order matters — most specific first)
    patterns = [
        # "for months of January - May 2020 Compared to January - May 2019"
        rf"[,:]?\s*for\s+months?\s+of\s+(?:{MONTHS})[\s\-]+(?:{MONTHS})?\s*\d{{4}}.*$",
        # "Compared to/with January - June 2019" or "Compared with 2019"
        rf"\s+Compared\s+(?:to|with)\s+.*$",
        # "for January 2021", "for February 2026", "for July 2025"
        rf"[,:]?\s*for\s+(?:{MONTHS})\.?\s*\d{{4}}\s*$",
        # ": January 2025 and February 2025", ": April and May 2020"
        rf"[,:]?\s*(?:{MONTHS})\.?\s*\d{{0,4}}\s+and\s+(?:{MONTHS})\.?\s*\d{{4}}\s*$",
        # ": First Quarter 2025", "Fourth Quarter 2025"
        rf"[,:]?\s*(?:{QUARTERS})\s*\d{{4}}\s*$",
        # "First quarter - Fourth quarter 2023"
        rf"[,:]?\s*(?:{QUARTERS})\s*[-–]\s*(?:{QUARTERS})\s*\d{{4}}\s*$",
        # ": 2022 - 2023", ": 1996 - 2025", "for the years 2019, 2020"
        rf"[,:]?\s*for\s+the\s+[Yy]ears?\s*\d{{4}}.*$",
        rf"[,:]?\s*\d{{4}}\s*[-–]\s*\d{{4}}\s*$",
        # "for years: 2011- 2025 Base year (2019=100)"
        rf"[,:]?\s*for\s+years?:?\s*\d{{4}}\s*[-–]\s*\d{{4}}.*$",
        # Trailing "Base Year (2013=100)" or "Base year (2018=100)"
        rf"\s*[Bb]ase\s+[Yy]ear\s*\(?.*$",
        # ": 2020 Compared with 2019" or "for 2021 compared with 2020"
        rf"[,:]?\s*(?:for\s+)?\d{{4}}\s+[Cc]ompared\s+(?:with|to)\s+\d{{4}}\s*$",
        # Trailing year: ", 2020", ", 2023", "2020-2021"
        rf",\s*\d{{4}}\s*[-–]\s*\d{{4}}\s*$",
        rf",\s*\d{{4}}\s*$",
        # "1997- 2019", "1997-2018" at end after comma or colon
        rf"[,:]?\s*\d{{4}}\s*[-–]\s*\d{{4}}\s*$",
        # "for: 1996 - 2020"
        rf"\s+for:?\s*\d{{4}}\s*[-–]?\s*\d{{0,4}}\s*$",
        # Trailing standalone year
        rf"[,:]?\s+\d{{4}}\s*$",
        # Quarter references inline: "Q1-2020", "Second quarter - Third quarter 2022"
        rf"[,:]?\s*(?:{QUARTERS})\s*[-–]?\s*(?:{QUARTERS})?\s*\d{{0,4}}\s*$",
    ]

    # Apply patterns repeatedly until stable
    for _ in range(3):  # max 3 passes
        prev = s
        for pat in patterns:
            s = re.sub(pat, "", s, flags=re.IGNORECASE).strip()
        if s == prev:
            break

    # Clean up artifacts
    # Remove leading "(" if unbalanced
    if s.startswith("(") and s.count("(") > s.count(")"):
        s = s[1:].strip()
    # Remove trailing colons, commas, asterisks, parens
    s = re.sub(r"[,:;\*\s]+$", "", s)
    # Remove trailing unmatched parens
    s = re.sub(r"\s*\(\s*$", "", s)
    # Collapse multiple spaces
    s = re.sub(r"\s{2,}", " ", s)
    # Strip leading/trailing parens wrapping entire name
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()

    return s


def normalize_for_grouping(base_name: str) -> str:
    """Further normalize for grouping comparison — collapse whitespace/case variations."""
    s = base_name.strip()
    # Normalize whitespace
    s = re.sub(r"\s+", " ", s)
    # Normalize some common variations
    s = re.sub(r"\s*\*\s*", "", s)  # remove asterisks
    s = s.replace("Sub Group", "Subgroups").replace("Sub Groups", "Subgroups")
    s = s.replace("Subgroup", "Subgroups")
    # Normalize case for comparison (but keep original for display)
    return s.lower().strip()


# ── Step 2-3: Group and report ───────────────────────────────────────────────

@dataclass
class DatasetInfo:
    id: int
    slug: str
    name_en: str
    name_ar: str
    base_name: str
    indicator_count: int = 0
    observation_count: int = 0
    min_date: str = ""
    max_date: str = ""


@dataclass
class ConsolidationGroup:
    canonical_name: str
    group_key: str
    datasets: list = field(default_factory=list)
    total_observations: int = 0
    total_indicators: int = 0
    time_range: str = ""

    @property
    def needs_merge(self) -> bool:
        return len(self.datasets) > 1


def load_datasets(conn) -> list:
    """Load all datasets with their stats."""
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("""
            SELECT d.id, d.slug, d.name_en, d.name_ar,
                   COUNT(DISTINCT i.id) as indicator_count,
                   COUNT(DISTINCT o.id) as observation_count,
                   MIN(o.time_period)::text as min_date,
                   MAX(o.time_period)::text as max_date
            FROM datasets d
            LEFT JOIN indicators i ON i.dataset_id = d.id
            LEFT JOIN observations o ON o.indicator_id = i.id
            GROUP BY d.id, d.slug, d.name_en, d.name_ar
            ORDER BY d.name_en
        """)
        results = []
        for row in cur.fetchall():
            base = extract_base_name(row["name_en"])
            results.append(DatasetInfo(
                id=row["id"],
                slug=row["slug"],
                name_en=row["name_en"],
                name_ar=row["name_ar"],
                base_name=base,
                indicator_count=row["indicator_count"] or 0,
                observation_count=row["observation_count"] or 0,
                min_date=row["min_date"] or "",
                max_date=row["max_date"] or "",
            ))
        return results


def build_groups(datasets: list) -> dict:
    """Group datasets by normalized base name."""
    groups = defaultdict(list)
    for ds in datasets:
        key = normalize_for_grouping(ds.base_name)
        groups[key].append(ds)

    # Build ConsolidationGroup objects
    result = {}
    for key, ds_list in groups.items():
        # Pick the shortest/cleanest name as canonical
        canonical = min(ds_list, key=lambda d: len(d.base_name)).base_name
        # If canonical is empty, use the shortest original name
        if not canonical:
            canonical = min(ds_list, key=lambda d: len(d.name_en)).name_en

        total_obs = sum(d.observation_count for d in ds_list)
        total_ind = sum(d.indicator_count for d in ds_list)

        dates = [d.min_date for d in ds_list if d.min_date] + \
                [d.max_date for d in ds_list if d.max_date]
        time_range = f"{min(dates)} to {max(dates)}" if dates else "unknown"

        result[key] = ConsolidationGroup(
            canonical_name=canonical,
            group_key=key,
            datasets=ds_list,
            total_observations=total_obs,
            total_indicators=total_ind,
            time_range=time_range,
        )

    return result


def check_indicator_compatibility(conn, group: ConsolidationGroup) -> bool:
    """Check if datasets in a group have compatible indicator structures.

    Compatible = most indicator names overlap (same metrics measured across time).
    Incompatible = completely different indicator sets (different breakdowns).
    """
    if len(group.datasets) <= 1:
        return True

    with conn.cursor() as cur:
        indicator_sets = []
        for ds in group.datasets:
            cur.execute("""
                SELECT DISTINCT LOWER(TRIM(name_en))
                FROM indicators WHERE dataset_id = %s
            """, (ds.id,))
            names = {row[0] for row in cur.fetchall()}
            if names:
                indicator_sets.append(names)

        if len(indicator_sets) < 2:
            return True

        # Check pairwise overlap — if any pair has > 30% overlap, consider compatible
        for i in range(len(indicator_sets)):
            for j in range(i + 1, len(indicator_sets)):
                overlap = indicator_sets[i] & indicator_sets[j]
                union = indicator_sets[i] | indicator_sets[j]
                if union and len(overlap) / len(union) > 0.3:
                    return True

        return False


# ── Step 4: Execute merge ────────────────────────────────────────────────────

def make_slug(name: str) -> str:
    """Create a URL-friendly slug from a name."""
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    s = s.strip("-")
    return s[:200]


def merge_group(conn, group: ConsolidationGroup, dry_run: bool = True):
    """Merge all datasets in a group into one canonical dataset."""
    if not group.needs_merge:
        return

    datasets = group.datasets
    # Pick the dataset with the most observations as canonical
    canonical_ds = max(datasets, key=lambda d: d.observation_count)
    others = [d for d in datasets if d.id != canonical_ds.id]

    new_name = group.canonical_name
    new_slug = make_slug(new_name)

    if dry_run:
        return

    with conn.cursor() as cur:
        # Check slug uniqueness, append if needed
        cur.execute("SELECT COUNT(*) FROM datasets WHERE slug = %s AND id != %s",
                    (new_slug, canonical_ds.id))
        if cur.fetchone()[0] > 0:
            new_slug = f"{new_slug}-{canonical_ds.id}"

        # Update canonical dataset name and slug
        cur.execute("""
            UPDATE datasets SET name_en = %s, slug = %s, updated_at = NOW()
            WHERE id = %s
        """, (new_name, new_slug, canonical_ds.id))

        # For each other dataset, merge indicators and observations
        for other in others:
            # Get indicators from the other dataset
            cur.execute("""
                SELECT id, code, name_en, name_ar, unit_en, unit_ar,
                       unit_symbol, decimals, dimensions
                FROM indicators WHERE dataset_id = %s
            """, (other.id,))
            other_indicators = cur.fetchall()

            for oi in other_indicators:
                oi_id, oi_code, oi_name, oi_name_ar, oi_unit, oi_unit_ar, \
                    oi_symbol, oi_decimals, oi_dims = oi

                # Try to find matching indicator in canonical dataset
                # Match by normalized name + unit OR by code
                cur.execute("""
                    SELECT id FROM indicators
                    WHERE dataset_id = %s
                      AND (
                        (LOWER(TRIM(name_en)) = LOWER(TRIM(%s))
                         AND COALESCE(unit_en, '') = COALESCE(%s, ''))
                        OR code = %s
                      )
                    LIMIT 1
                """, (canonical_ds.id, oi_name, oi_unit, oi_code))
                match = cur.fetchone()

                if match:
                    # Re-point observations to existing indicator
                    target_indicator_id = match[0]
                else:
                    # Move indicator to canonical dataset — resolve code conflicts
                    cur.execute("""
                        SELECT COUNT(*) FROM indicators
                        WHERE dataset_id = %s AND code = %s
                    """, (canonical_ds.id, oi_code))
                    if cur.fetchone()[0] > 0:
                        # Code conflict — append a suffix
                        new_code = f"{oi_code}-{other.id}"
                        cur.execute("""
                            UPDATE indicators SET dataset_id = %s, code = %s WHERE id = %s
                        """, (canonical_ds.id, new_code, oi_id))
                    else:
                        cur.execute("""
                            UPDATE indicators SET dataset_id = %s WHERE id = %s
                        """, (canonical_ds.id, oi_id))
                    target_indicator_id = oi_id

                if match:
                    # Re-point observations, avoiding duplicates
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
                    """, (target_indicator_id, oi_id, target_indicator_id))

                    # Delete any remaining duplicate observations
                    cur.execute("DELETE FROM observations WHERE indicator_id = %s", (oi_id,))
                    # Delete the now-empty indicator
                    cur.execute("DELETE FROM indicators WHERE id = %s", (oi_id,))

            # Move source links to canonical dataset, then delete
            cur.execute("""
                INSERT INTO dataset_sources (dataset_id, source_id, is_primary)
                SELECT %s, source_id, is_primary FROM dataset_sources
                WHERE dataset_id = %s
                ON CONFLICT (dataset_id, source_id) DO NOTHING
            """, (canonical_ds.id, other.id))
            cur.execute("DELETE FROM dataset_sources WHERE dataset_id = %s", (other.id,))
            cur.execute("DELETE FROM indicators WHERE dataset_id = %s", (other.id,))
            cur.execute("DELETE FROM datasets WHERE id = %s", (other.id,))

        # Update temporal coverage on canonical
        cur.execute("""
            UPDATE datasets SET
                temporal_coverage_start = (
                    SELECT MIN(o.time_period) FROM observations o
                    JOIN indicators i ON o.indicator_id = i.id
                    WHERE i.dataset_id = %s
                ),
                temporal_coverage_end = (
                    SELECT MAX(o.time_period) FROM observations o
                    JOIN indicators i ON o.indicator_id = i.id
                    WHERE i.dataset_id = %s
                )
            WHERE id = %s
        """, (canonical_ds.id, canonical_ds.id, canonical_ds.id))

    conn.commit()


# ── Step 5: Clean up names ───────────────────────────────────────────────────

def clean_dataset_name(name: str) -> str:
    """Clean a dataset name for display."""
    s = name.strip()

    # Remove "PCBS |" prefix
    s = re.sub(r"^PCBS\s*\|\s*", "", s)

    # Remove leading/trailing parens, quotes, asterisks
    s = re.sub(r"^\(+\s*", "", s)
    s = re.sub(r"\s*\)+$", "", s)
    s = re.sub(r'^["\']|["\']$', "", s)
    s = re.sub(r"\*+", "", s)

    # Remove base year notes — move to metadata later
    base_year_match = re.search(r"\s*\(?\s*[Bb]ase\s+[Yy]ear\s*[:(]?\s*\d{4}\s*=\s*\d+\s*\)?\s*", s)
    if base_year_match:
        s = s[:base_year_match.start()] + s[base_year_match.end():]

    # Collapse spaces
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"[,:;\s]+$", "", s)
    s = s.strip()

    # Title case (but preserve acronyms like IIP, GDP, GHG, BPM6)
    words = s.split()
    result = []
    skip_lower = {"and", "or", "the", "in", "by", "of", "for", "to", "from", "at", "on", "with", "a", "an"}
    acronyms = {"IIP", "GDP", "GHG", "BPM6", "CPI", "PPI", "CO2", "CH4", "N2O", "WHO",
                "PCBS", "USD", "NIS", "S16", "IMF", "UN", "UNRWA", "EU"}
    for i, w in enumerate(words):
        upper = w.upper().rstrip(".,;:()")
        if upper in acronyms or re.match(r"^[A-Z]{2,}", w):
            result.append(w)
        elif i == 0:
            result.append(w.capitalize())
        elif w.lower() in skip_lower:
            result.append(w.lower())
        else:
            result.append(w.capitalize() if w.islower() else w)

    return " ".join(result)


def clean_all_names(conn, dry_run: bool = True):
    """Clean all dataset names in the database."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, name_en FROM datasets ORDER BY name_en")
        updates = []
        for row in cur.fetchall():
            ds_id, name = row
            cleaned = clean_dataset_name(name)
            if cleaned != name:
                updates.append((ds_id, cleaned, make_slug(cleaned)))

        if dry_run:
            print(f"\n{'='*60}")
            print(f"NAME CLEANUP: {len(updates)} names would be cleaned")
            for ds_id, cleaned, slug in updates[:20]:
                print(f"  → {cleaned}")
            return

        for ds_id, cleaned, slug in updates:
            # Check slug uniqueness
            cur.execute("SELECT COUNT(*) FROM datasets WHERE slug = %s AND id != %s",
                        (slug, ds_id))
            if cur.fetchone()[0] > 0:
                slug = f"{slug}-{ds_id}"
            cur.execute("UPDATE datasets SET name_en = %s, slug = %s WHERE id = %s",
                        (cleaned, slug, ds_id))
        conn.commit()
        print(f"Cleaned {len(updates)} dataset names")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Consolidate duplicate PCBS datasets")
    parser.add_argument("--execute", action="store_true",
                        help="Actually perform the merge (default is dry run)")
    parser.add_argument("--skip-world-bank", action="store_true", default=True,
                        help="Skip World Bank datasets (default: skip)")
    args = parser.parse_args()

    dry_run = not args.execute

    conn = psycopg2.connect(DB_URL)

    print("Loading datasets...")
    datasets = load_datasets(conn)
    print(f"Loaded {len(datasets)} datasets")

    # Separate World Bank
    wb_datasets = [d for d in datasets if "world bank" in d.name_en.lower()]
    pcbs_datasets = [d for d in datasets if "world bank" not in d.name_en.lower()]

    print(f"  PCBS: {len(pcbs_datasets)}, World Bank: {len(wb_datasets)} (skipped)")

    # Build groups
    groups = build_groups(pcbs_datasets)

    mergeable = {k: g for k, g in groups.items() if g.needs_merge}
    singletons = {k: g for k, g in groups.items() if not g.needs_merge}

    print(f"\nGrouping results:")
    print(f"  Total groups: {len(groups)}")
    print(f"  Groups to merge (2+ datasets): {len(mergeable)}")
    print(f"  Singletons (already unique): {len(singletons)}")

    # Sort by number of datasets being merged (descending)
    sorted_groups = sorted(mergeable.values(), key=lambda g: len(g.datasets), reverse=True)

    print(f"\n{'='*80}")
    print(f"TOP 30 CONSOLIDATION GROUPS (by number of datasets merged)")
    print(f"{'='*80}")

    for i, group in enumerate(sorted_groups[:30]):
        print(f"\n{i+1}. \"{group.canonical_name}\"")
        print(f"   Merging {len(group.datasets)} datasets → 1")
        print(f"   Observations: {group.total_observations:,} | Indicators: {group.total_indicators}")
        print(f"   Time range: {group.time_range}")
        if len(group.datasets) <= 6:
            for ds in group.datasets:
                print(f"     - [{ds.id}] {ds.name_en[:100]}")
        else:
            for ds in group.datasets[:3]:
                print(f"     - [{ds.id}] {ds.name_en[:100]}")
            print(f"     ... and {len(group.datasets) - 3} more")

    # Check compatibility for groups with very different indicator counts
    print(f"\n{'='*80}")
    print(f"COMPATIBILITY CHECKS")
    print(f"{'='*80}")

    incompatible = []
    for group in sorted_groups:
        if not check_indicator_compatibility(conn, group):
            incompatible.append(group)
            print(f"  ⚠ INCOMPATIBLE: \"{group.canonical_name}\" ({len(group.datasets)} datasets)")
            ind_counts = [d.indicator_count for d in group.datasets]
            print(f"    Indicator counts vary: {min(ind_counts)} to {max(ind_counts)}")

    compatible_merge = [g for g in sorted_groups if g not in incompatible]
    print(f"\n  Compatible groups to merge: {len(compatible_merge)}")
    print(f"  Incompatible groups (will split, not merge): {len(incompatible)}")

    # Summary statistics
    total_datasets_before = len(pcbs_datasets)
    datasets_after_merge = len(singletons) + len(compatible_merge) + sum(
        len(g.datasets) for g in incompatible  # incompatible stay separate
    )
    total_merged_away = total_datasets_before - datasets_after_merge

    print(f"\n{'='*80}")
    print(f"CONSOLIDATION SUMMARY")
    print(f"{'='*80}")
    print(f"  Before: {total_datasets_before} PCBS datasets + {len(wb_datasets)} World Bank")
    print(f"  After:  ~{datasets_after_merge} PCBS datasets + {len(wb_datasets)} World Bank")
    print(f"  Reduction: ~{total_merged_away} datasets removed ({total_merged_away*100//total_datasets_before}%)")

    if dry_run:
        print(f"\n{'='*80}")
        print("DRY RUN — no changes made. Run with --execute to perform the merge.")
        print(f"{'='*80}")
        conn.close()
        return

    # Execute the merge
    print(f"\n{'='*80}")
    print("EXECUTING MERGE...")
    print(f"{'='*80}")

    merged = 0
    failed = 0
    for i, group in enumerate(compatible_merge):
        try:
            merge_group(conn, group, dry_run=False)
            merged += 1
            if (i + 1) % 10 == 0:
                print(f"  Merged {i+1}/{len(compatible_merge)} groups...")
        except Exception as e:
            print(f"  ✗ Failed to merge \"{group.canonical_name}\": {e}")
            conn.rollback()
            failed += 1

    print(f"  Merged: {merged} groups, Failed: {failed}")

    # Clean up names
    clean_all_names(conn, dry_run=False)

    # Final stats
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM datasets")
        final_datasets = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM indicators")
        final_indicators = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM observations")
        final_observations = cur.fetchone()[0]

    print(f"\n{'='*80}")
    print(f"FINAL RESULTS")
    print(f"{'='*80}")
    print(f"  Datasets:     {total_datasets_before + len(wb_datasets)} → {final_datasets}")
    print(f"  Indicators:   {final_indicators:,}")
    print(f"  Observations: {final_observations:,}")

    # Show top 10 datasets by observation count
    with conn.cursor() as cur:
        cur.execute("""
            SELECT d.name_en, COUNT(o.id) as obs,
                   COUNT(DISTINCT i.id) as inds,
                   MIN(o.time_period)::text as min_t,
                   MAX(o.time_period)::text as max_t
            FROM datasets d
            JOIN indicators i ON i.dataset_id = d.id
            JOIN observations o ON o.indicator_id = i.id
            GROUP BY d.name_en
            ORDER BY obs DESC
            LIMIT 10
        """)
        print(f"\nTop 10 datasets by observation count:")
        for row in cur.fetchall():
            print(f"  {row[1]:>7,} obs | {row[2]:>4} ind | {row[3]} to {row[4]} | {row[0][:80]}")

    conn.close()


if __name__ == "__main__":
    main()
