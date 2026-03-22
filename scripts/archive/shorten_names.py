#!/usr/bin/env python3
"""Shorten and clean up dataset names."""

import re
import psycopg2

import os
DB_URL = os.environ.get("DATABASE_URL", "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine")

# Replacements to shorten names (order matters)
REPLACEMENTS = [
    # Remove "in Palestine" / "in the State of Palestine" (redundant)
    (r"\s+in\s+(?:the\s+State\s+of\s+)?Palestine\*?", ""),
    # Remove "in the West Bank*" when redundant (keep if distinguishes from Gaza)
    # Only remove when it's the only region mentioned
    # (r"\s+in\s+the\s+West\s+Bank\*?(?!\s+and)", ""),
    # Shorten common verbose phrases
    (r"Consumer Price Index Numbers? by Major Groups of Expenditure and Region", "Consumer Price Index by Expenditure Group"),
    (r"Accused\s+Juvenile Offenders Who Have Been Referred to the\s+Juvenile [Oo]fficer", "Juvenile Offenders Referred to Juvenile Officer"),
    (r"Juvenile Offenders Who Entered Reformatory Institutions", "Juvenile Offenders in Reformatory Institutions"),
    (r"The Preliminary Results of the Quarterly Balance of Payments for Palestine", "Quarterly Balance of Payments"),
    (r"The Preliminary Results of the Annual Balance of Payments for Palestine", "Annual Balance of Payments"),
    (r"According to the Sixth Editionn?", "(6th Ed.)"),
    (r"According to the Fifth Edition", "(5th Ed.)"),
    (r"Fifth Edition", "(5th Ed.)"),
    (r"Percentage Distribution of", "Distribution of"),
    (r"International Investment Position \(IIP\)", "IIP"),
    (r"Percent Changes?", "% Change"),
    (r"percentage changes?", "% Change"),
    (r"Number of ", ""),
    (r"and % Change", "& % Change"),
    # Remove "by Governorate" when data already has gov-level geographies
    (r",?\s*by\s+Governorate\s*$", ""),
    (r"\s+by\s+Governorate\s+and\s+", " by "),
    # Remove trailing "for" left from time stripping
    (r"\s+for\s*$", ""),
    # Remove trailing prepositions
    (r"\s+(?:at|in|by|for|of)\s*$", ""),
    # Clean up double spaces, trailing punctuation
    (r"\s{2,}", " "),
    (r"[,;:\s]+$", ""),
    (r"^\s+", ""),
]


def shorten_name(name: str) -> str:
    s = name
    for pattern, replacement in REPLACEMENTS:
        s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)

    # Trim to ~80 chars if still too long, breaking at word boundary
    if len(s) > 85:
        # Find last space before char 80
        cut = s[:80].rfind(" ")
        if cut > 40:  # only if we keep meaningful content
            s = s[:cut]
            s = re.sub(r"[,;:\s]+$", "", s)

    return s.strip()


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("SELECT id, name_en, slug FROM datasets ORDER BY name_en")
    datasets = cur.fetchall()

    changes = []
    for ds_id, name, slug in datasets:
        new_name = shorten_name(name)
        if new_name != name:
            # Generate new slug
            new_slug = re.sub(r"[^\w\s-]", "", new_name.lower())
            new_slug = re.sub(r"[\s_]+", "-", new_slug)
            new_slug = re.sub(r"-{2,}", "-", new_slug).strip("-")[:200]

            changes.append((ds_id, name, new_name, new_slug))

    print(f"Name changes: {len(changes)} of {len(datasets)} datasets")
    print()

    # Show first 30 changes
    for ds_id, old, new, slug in changes[:30]:
        print(f"  OLD: {old[:90]}")
        print(f"  NEW: {new}")
        print()

    if len(changes) > 30:
        print(f"  ... and {len(changes) - 30} more\n")

    # Check for name length stats
    lengths = [len(c[2]) for c in changes]
    old_lengths = [len(c[1]) for c in changes]
    if lengths:
        print(f"Name length: avg {sum(old_lengths)//len(old_lengths)} → {sum(lengths)//len(lengths)} chars")
        print(f"  Max: {max(old_lengths)} → {max(lengths)} chars")
        over_80 = sum(1 for l in lengths if l > 80)
        print(f"  Still over 80 chars: {over_80}")

    # Apply
    print("\nApplying changes...")
    for ds_id, old, new_name, new_slug in changes:
        # Check slug uniqueness
        cur.execute("SELECT COUNT(*) FROM datasets WHERE slug = %s AND id != %s",
                    (new_slug, ds_id))
        if cur.fetchone()[0] > 0:
            new_slug = f"{new_slug}-{ds_id}"
        cur.execute("UPDATE datasets SET name_en = %s, slug = %s WHERE id = %s",
                    (new_name, new_slug, ds_id))

    conn.commit()
    print(f"Updated {len(changes)} dataset names")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
