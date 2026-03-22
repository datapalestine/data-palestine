#!/usr/bin/env python3
"""Final cleanup pass — merge duplicates, fix names, remove junk."""

import re
from collections import defaultdict
import psycopg2

import os
DB_URL = os.environ.get("DATABASE_URL", "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine")


def merge_datasets(conn, keep_id, remove_ids, new_name=None):
    """Merge remove_ids datasets into keep_id."""
    cur = conn.cursor()

    if new_name:
        slug = re.sub(r"[^\w\s-]", "", new_name.lower())
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-{2,}", "-", slug).strip("-")[:200]
        cur.execute("SELECT COUNT(*) FROM datasets WHERE slug = %s AND id != %s", (slug, keep_id))
        if cur.fetchone()[0] > 0:
            slug = f"{slug}-{keep_id}"
        cur.execute("UPDATE datasets SET name_en = %s, slug = %s WHERE id = %s",
                    (new_name, slug, keep_id))

    for rid in remove_ids:
        # Get indicators from the dataset to remove
        cur.execute("SELECT id, code, name_en, unit_en FROM indicators WHERE dataset_id = %s", (rid,))
        other_inds = cur.fetchall()

        for oi_id, oi_code, oi_name, oi_unit in other_inds:
            # Find matching indicator in canonical
            cur.execute("""
                SELECT id FROM indicators
                WHERE dataset_id = %s
                  AND (LOWER(TRIM(name_en)) = LOWER(TRIM(%s)) OR code = %s)
                LIMIT 1
            """, (keep_id, oi_name, oi_code))
            match = cur.fetchone()

            if match:
                target_id = match[0]
                # Move non-duplicate observations
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
                """, (target_id, oi_id, target_id))
                cur.execute("DELETE FROM observations WHERE indicator_id = %s", (oi_id,))
                cur.execute("DELETE FROM indicators WHERE id = %s", (oi_id,))
            else:
                # Move indicator to canonical dataset, handling code conflicts
                cur.execute("SELECT COUNT(*) FROM indicators WHERE dataset_id = %s AND code = %s",
                            (keep_id, oi_code))
                if cur.fetchone()[0] > 0:
                    new_code = f"{oi_code}-{oi_id}"
                    cur.execute("UPDATE indicators SET dataset_id = %s, code = %s WHERE id = %s",
                                (keep_id, new_code, oi_id))
                else:
                    cur.execute("UPDATE indicators SET dataset_id = %s WHERE id = %s",
                                (keep_id, oi_id))

        # Clean up source links and delete
        cur.execute("""
            INSERT INTO dataset_sources (dataset_id, source_id, is_primary)
            SELECT %s, source_id, is_primary FROM dataset_sources WHERE dataset_id = %s
            ON CONFLICT (dataset_id, source_id) DO NOTHING
        """, (keep_id, rid))
        cur.execute("DELETE FROM dataset_sources WHERE dataset_id = %s", (rid,))
        cur.execute("DELETE FROM indicators WHERE dataset_id = %s", (rid,))
        cur.execute("DELETE FROM datasets WHERE id = %s", (rid,))

    # Update temporal coverage
    cur.execute("""
        UPDATE datasets SET
            temporal_coverage_start = sub.min_t,
            temporal_coverage_end = sub.max_t
        FROM (
            SELECT i.dataset_id, MIN(o.time_period) as min_t, MAX(o.time_period) as max_t
            FROM observations o JOIN indicators i ON o.indicator_id = i.id
            WHERE i.dataset_id = %s GROUP BY i.dataset_id
        ) sub WHERE datasets.id = sub.dataset_id
    """, (keep_id,))

    conn.commit()
    cur.close()


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Get before counts
    cur.execute("SELECT COUNT(*) FROM datasets")
    ds_before = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM indicators")
    ind_before = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM observations")
    obs_before = cur.fetchone()[0]
    print(f"Before: {ds_before} datasets, {ind_before:,} indicators, {obs_before:,} observations\n")

    # ── 1. Merge exact duplicate names ──────────────────────────────────────

    print("=== 1. Merging exact duplicate dataset names ===")
    cur.execute("""
        SELECT name_en, array_agg(id ORDER BY id) as ids, COUNT(*) as cnt
        FROM datasets GROUP BY name_en HAVING COUNT(*) > 1 ORDER BY cnt DESC
    """)
    exact_dups = cur.fetchall()

    for name, ids, cnt in exact_dups:
        keep = ids[0]
        remove = ids[1:]
        print(f"  Merging {cnt} copies of \"{name[:70]}\" (keep {keep}, remove {remove})")
        merge_datasets(conn, keep, remove)

    print(f"  Merged {sum(c-1 for _,_,c in exact_dups)} datasets\n")

    # ── 2. Merge near-duplicates ────────────────────────────────────────────

    print("=== 2. Merging near-duplicate names ===")

    # Specific known near-duplicates to merge
    near_dups = [
        # ForeignTrade vs Foreign Trade
        (2127, [881], "Detailed Indicators of Foreign Trade"),
        # General Government Finance variants
        (323, [738], "General Government Finance"),
        (329, [737], "General Government Finance (Part 2)"),
        # Sewage "Sub Groups" vs "Subgroups"
        (1827, [1156], "Sewage Networks Cost Indices & % Change by Major and Subgroups in the West Bank"),
        # Tribal Judiciary extra space in parens
        (1626, [814], None),
        # Received/incoming case difference
        (2354, [868], "Received/Incoming Investigative Cases by Public Prosecution"),
    ]

    for keep, remove, new_name in near_dups:
        # Verify both exist
        cur.execute("SELECT COUNT(*) FROM datasets WHERE id = ANY(%s)", ([keep] + remove,))
        if cur.fetchone()[0] < 2:
            continue
        print(f"  Merging {keep} ← {remove}" + (f" as \"{new_name[:60]}\"" if new_name else ""))
        merge_datasets(conn, keep, remove, new_name)

    # ── 3. Balance of Payments cleanup ──────────────────────────────────────

    print("\n=== 3. Balance of Payments cleanup ===")

    # These are genuinely different methodological editions:
    # - 5th Edition (BPM5): older methodology
    # - 6th Edition (BPM6): newer methodology (since ~2014)
    # - "BPM6" (from Table Title split): same as 6th Ed
    # - Unlabeled: oldest, pre-edition labeling
    #
    # Merge: "Balance of Payments for the" (39 obs, truncated name) into unlabeled "Balance of Payments"
    # Merge: "Quarterly Balance of Payments for Palestine (BPM6" into "Quarterly Balance of Payments (6th Ed."
    # Keep separate: 5th vs 6th edition (different methodologies)

    # "Balance of Payments for the" → merge into "Balance of Payments"
    cur.execute("SELECT id FROM datasets WHERE name_en = 'Balance of Payments for the'")
    bop_for = cur.fetchone()
    cur.execute("SELECT id FROM datasets WHERE name_en = 'Balance of Payments'")
    bop_base = cur.fetchone()
    if bop_for and bop_base:
        print("  Merging 'Balance of Payments for the' into 'Balance of Payments'")
        merge_datasets(conn, bop_base[0], [bop_for[0]])

    # BPM6 → merge into Quarterly 6th Ed
    cur.execute("SELECT id FROM datasets WHERE name_en LIKE 'Quarterly Balance of Payments for Palestine (BPM6%'")
    bpm6 = cur.fetchone()
    cur.execute("SELECT id FROM datasets WHERE name_en LIKE 'Quarterly Balance of Payments (6th Ed.%'")
    q6 = cur.fetchone()
    if bpm6 and q6:
        print("  Merging BPM6 quarterly into 6th Ed. quarterly")
        merge_datasets(conn, q6[0], [bpm6[0]])

    # Clean up BoP names — fix unclosed parens
    bop_fixes = [
        ("Quarterly Balance of Payments (6th Ed.", "Quarterly Balance of Payments (6th Ed.)"),
        ("Quarterly Balance of Payments (5th Ed.", "Quarterly Balance of Payments (5th Ed.)"),
        ("Annual Balance of Payments (6th Ed.", "Annual Balance of Payments (6th Ed.)"),
        ("Annual Balance of Payments (5th Ed.", "Annual Balance of Payments (5th Ed.)"),
    ]
    for old, new in bop_fixes:
        cur.execute("UPDATE datasets SET name_en = %s WHERE name_en = %s", (new, old))

    # Add descriptions explaining the editions
    descriptions = {
        "Quarterly Balance of Payments (6th Ed.)":
            "Balance of payments data using BPM6 methodology (IMF's 6th edition manual). Quarterly frequency.",
        "Quarterly Balance of Payments (5th Ed.)":
            "Balance of payments data using BPM5 methodology (IMF's 5th edition manual). Quarterly frequency. Superseded by 6th edition.",
        "Annual Balance of Payments (6th Ed.)":
            "Annual balance of payments aggregates using BPM6 methodology.",
        "Annual Balance of Payments (5th Ed.)":
            "Annual balance of payments aggregates using BPM5 methodology. Superseded by 6th edition.",
        "Quarterly Balance of Payments":
            "Quarterly balance of payments data (pre-edition labeling).",
        "Balance of Payments":
            "Balance of payments data (pre-edition labeling, annual).",
    }
    for name, desc in descriptions.items():
        cur.execute("UPDATE datasets SET description_en = %s WHERE name_en = %s AND (description_en IS NULL OR description_en = '')",
                    (desc, name))
    conn.commit()

    # ── 4. Strip remaining years from names ─────────────────────────────────

    print("\n=== 4. Stripping remaining years from names ===")

    cur.execute("SELECT id, name_en FROM datasets ORDER BY name_en")
    all_ds = cur.fetchall()

    year_patterns = [
        # "End of 2022", "End of the First Quarter 2023"
        (r"\s+End of (?:the\s+)?(?:First|Second|Third|Fourth)?\s*Quarter?\s*\d{4}", ""),
        # "End of Year 2021"
        (r"\s+End of Year \d{4}", ""),
        # "for the Period: January - December 2021"
        (r"\s+for (?:the )?Period:?\s+\w+\s*-\s*\w+\s+\d{4}", ""),
        # "for January - September 2020"
        (r"\s+for (?:January|February|March|April|May|June|July|August|September|October|November|December)\s*-\s*\w+\s+\d{4}", ""),
        # "for Month of Febraury 2025"
        (r"\s+for Months? of \w+\s*\d{4}", ""),
        # "for Months of May2022"
        (r"\s+for Months? of \w+\d{4}", ""),
        # "for 2020 & % Change from 2019"
        (r"\s+for \d{4}\s*&\s*% Change from \d{4}", ""),
        # "for July 2020"
        (r"\s+for \w+ \d{4}", ""),
        # "for the Year 2019"
        (r"\s+for (?:the )?[Yy]ear\s+\d{4}", ""),
        # Leading "2015 " (year prefix)
        (r"^\d{4}\s+", ""),
        # Trailing ", 2013- 2018 at" patterns
        (r",\s*\d{4}\s*-\s*\d{4}\s+at\b", " at"),
        # Remaining trailing years
        (r"\s+\d{4}\s*$", ""),
        # "2019" at the very end
        (r",?\s*\d{4}\s*$", ""),
    ]

    year_fixes = 0
    for ds_id, name in all_ds:
        new_name = name
        for pat, repl in year_patterns:
            new_name = re.sub(pat, repl, new_name, flags=re.IGNORECASE)
        new_name = re.sub(r"[,;:\s]+$", "", new_name).strip()

        if new_name != name and len(new_name) > 10:
            slug = re.sub(r"[^\w\s-]", "", new_name.lower())
            slug = re.sub(r"[\s_]+", "-", slug)
            slug = re.sub(r"-{2,}", "-", slug).strip("-")[:200]
            cur.execute("SELECT COUNT(*) FROM datasets WHERE slug = %s AND id != %s", (slug, ds_id))
            if cur.fetchone()[0] > 0:
                slug = f"{slug}-{ds_id}"
            cur.execute("UPDATE datasets SET name_en = %s, slug = %s WHERE id = %s",
                        (new_name, slug, ds_id))
            year_fixes += 1

    conn.commit()
    print(f"  Fixed {year_fixes} dataset names")

    # ── 5. Fix trailing prepositions ────────────────────────────────────────

    print("\n=== 5. Fixing trailing prepositions ===")

    cur.execute("SELECT id, name_en FROM datasets WHERE name_en ~ '\\s(and|in|by|for|of|the|from|to|at|with)\\s*$'")
    trailing = cur.fetchall()

    for ds_id, name in trailing:
        new_name = re.sub(r"\s+(and|in|by|for|of|the|from|to|at|with)\s*$", "", name)
        new_name = re.sub(r"[,;:\s]+$", "", new_name)
        if new_name != name:
            slug = re.sub(r"[^\w\s-]", "", new_name.lower())
            slug = re.sub(r"[\s_]+", "-", slug)
            slug = re.sub(r"-{2,}", "-", slug).strip("-")[:200]
            cur.execute("SELECT COUNT(*) FROM datasets WHERE slug = %s AND id != %s", (slug, ds_id))
            if cur.fetchone()[0] > 0:
                slug = f"{slug}-{ds_id}"
            cur.execute("UPDATE datasets SET name_en = %s, slug = %s WHERE id = %s",
                        (new_name, slug, ds_id))

    conn.commit()
    print(f"  Fixed {len(trailing)} dataset names")

    # ── 6. Remove PCBS Unclassified ─────────────────────────────────────────

    print("\n=== 6. Removing PCBS - Unclassified Data ===")
    cur.execute("SELECT id FROM datasets WHERE name_en = 'PCBS - Unclassified Data'")
    unclassified = cur.fetchone()
    if unclassified:
        uid = unclassified[0]
        cur.execute("SELECT COUNT(*) FROM indicators WHERE dataset_id = %s", (uid,))
        ind_count = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM observations o
            JOIN indicators i ON o.indicator_id = i.id
            WHERE i.dataset_id = %s
        """, (uid,))
        obs_count = cur.fetchone()[0]
        print(f"  Removing: {ind_count} indicators, {obs_count} observations")

        cur.execute("DELETE FROM observations WHERE indicator_id IN (SELECT id FROM indicators WHERE dataset_id = %s)", (uid,))
        cur.execute("DELETE FROM indicators WHERE dataset_id = %s", (uid,))
        cur.execute("DELETE FROM dataset_sources WHERE dataset_id = %s", (uid,))
        cur.execute("DELETE FROM datasets WHERE id = %s", (uid,))
        conn.commit()

    # ── 7. Fix unclosed parentheses in remaining names ──────────────────────

    print("\n=== 7. Fix unclosed parentheses ===")
    cur.execute("SELECT id, name_en FROM datasets WHERE name_en LIKE '%(%' AND name_en NOT LIKE '%)%'")
    unclosed = cur.fetchall()
    for ds_id, name in unclosed:
        new_name = name + ")"
        cur.execute("UPDATE datasets SET name_en = %s WHERE id = %s", (new_name, ds_id))
    conn.commit()
    print(f"  Fixed {len(unclosed)} unclosed parentheses")

    # ── 8. One more consolidation pass ──────────────────────────────────────

    print("\n=== 8. Final consolidation pass ===")
    cur.execute("""
        SELECT name_en, array_agg(id ORDER BY id) as ids, COUNT(*)
        FROM datasets GROUP BY name_en HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC
    """)
    final_dups = cur.fetchall()
    for name, ids, cnt in final_dups:
        keep = ids[0]
        remove = ids[1:]
        print(f"  Merging {cnt} copies of \"{name[:70]}\" (keep {keep})")
        merge_datasets(conn, keep, remove)
    print(f"  Merged {sum(c-1 for _,_,c in final_dups)} more datasets")

    # ── Final report ────────────────────────────────────────────────────────

    cur.execute("SELECT COUNT(*) FROM datasets")
    ds_after = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM indicators")
    ind_after = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM observations")
    obs_after = cur.fetchone()[0]

    print(f"\n{'='*60}")
    print(f"FINAL STATE")
    print(f"{'='*60}")
    print(f"  Datasets:     {ds_before} → {ds_after} (-{ds_before - ds_after})")
    print(f"  Indicators:   {ind_before:,} → {ind_after:,} (-{ind_before - ind_after:,})")
    print(f"  Observations: {obs_before:,} → {obs_after:,} (-{obs_before - obs_after:,})")

    # Print first 50 names
    print(f"\n{'='*60}")
    print(f"FIRST 50 DATASET NAMES (alphabetical)")
    print(f"{'='*60}")
    cur.execute("SELECT name_en FROM datasets ORDER BY name_en LIMIT 50")
    for i, (name,) in enumerate(cur.fetchall(), 1):
        print(f"  {i:3}. {name}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
