"""Download and analyze PCBS CSV column headers.

Downloads each CSV from the discovery JSON, saves to data/raw/pcbs_csv/,
and produces a comprehensive analysis of column header patterns.
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path

import httpx

DISCOVERY_PATH = "data/pcbs_discovery.json"
OUTPUT_DIR = "data/raw/pcbs_csv"


async def download_csv(client: httpx.AsyncClient, url: str) -> bytes | None:
    try:
        resp = await client.get(url, follow_redirects=True)
        if resp.status_code == 200:
            return resp.content
        return None
    except Exception:
        return None


def detect_header_row(lines: list[str]) -> int:
    """Same heuristic as the ingestion pipeline."""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        parts = [p.strip().strip('"') for p in stripped.split(",")]
        non_empty = [p for p in parts if p]
        if len(non_empty) < 2:
            continue
        first = non_empty[0].lower()
        if any(first.startswith(prefix) for prefix in (
            "values in", "source:", "note:", "* ", "** ", "west bank and gaza",
        )):
            continue
        if len(non_empty) >= 2:
            return i
    return 0


def classify_column(col: str) -> dict:
    """Classify what a column header encodes."""
    col = col.strip()
    result = {
        "raw": col,
        "has_year": False,
        "has_month": False,
        "has_quarter": False,
        "has_pct_change": False,
        "has_subcategory": False,
        "subcategory": "",
        "time_part": "",
        "label_col": False,
    }

    # Check for % change
    if re.search(r'%\s*[Cc]hange|[Pp]ercent\s*[Cc]hange|التغير', col):
        result["has_pct_change"] = True

    # Month names
    month_pattern = (
        r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    )

    # Try to find time patterns
    # "May 2020 Residential buildings" or "Palestine Jun. 2019"
    month_year = re.search(rf'({month_pattern})\.?\s+(\d{{4}})', col, re.IGNORECASE)
    if month_year:
        result["has_month"] = True
        result["has_year"] = True
        result["time_part"] = f"{month_year.group(1)} {month_year.group(2)}"
        # Everything after the time part is subcategory
        after = col[month_year.end():].strip()
        before = col[:month_year.start()].strip()
        if after:
            result["has_subcategory"] = True
            result["subcategory"] = after
        elif before and not re.match(r'^(Palestine|West Bank|Gaza)', before, re.IGNORECASE):
            result["has_subcategory"] = True
            result["subcategory"] = before
        return result

    # "2020Q1" or "Q1/2020"
    quarter = re.search(r'Q(\d)[/\s]*(\d{4})|(\d{4})\s*Q(\d)', col, re.IGNORECASE)
    if quarter:
        result["has_quarter"] = True
        result["has_year"] = True
        result["time_part"] = col.strip().split()[0] if " " not in col.strip() else col.strip()
        return result

    # Just a year: "2020", "2019**"
    year_only = re.match(r'^(\d{4})\*{0,3}$', col.strip())
    if year_only:
        result["has_year"] = True
        result["time_part"] = year_only.group(1)
        return result

    # "Palestine Jun. 2020", "Palestine 2020", region + time
    region_time = re.search(r'(Palestine|West Bank|Gaza\s*Strip?)\s+(.+)', col, re.IGNORECASE)
    if region_time:
        remainder = region_time.group(2)
        # Check if remainder contains time
        if re.search(rf'{month_pattern}', remainder, re.IGNORECASE):
            result["has_month"] = True
            result["has_year"] = True
            result["time_part"] = remainder.strip()
            result["has_subcategory"] = True
            result["subcategory"] = region_time.group(1)
        elif re.match(r'\d{4}', remainder):
            result["has_year"] = True
            result["time_part"] = remainder.strip()
            result["has_subcategory"] = True
            result["subcategory"] = region_time.group(1)
        return result

    # If none of the above matched, it's probably a label column
    result["label_col"] = True
    return result


def analyze_csv(content: bytes, table_id: int, title: str) -> dict:
    """Analyze a single CSV file."""
    text = content.decode("utf-8-sig", errors="replace")
    lines = text.strip().split("\n")
    if len(lines) < 2:
        return {"table_id": table_id, "status": "too_short"}

    header_idx = detect_header_row(lines)
    metadata_rows = lines[:header_idx] if header_idx > 0 else []
    header_line = lines[header_idx]
    data_lines = lines[header_idx + 1:header_idx + 4]  # first 3 data rows

    # Parse headers
    headers = [h.strip().strip('"') for h in header_line.split(",")]
    # Some CSVs use multi-row headers
    has_subheader = False
    if header_idx + 1 < len(lines):
        next_line = lines[header_idx + 1]
        next_parts = [p.strip().strip('"') for p in next_line.split(",")]
        # If the second row has mostly non-numeric values, it might be a sub-header
        non_numeric = sum(1 for p in next_parts if p and not re.match(r'^-?[\d,.]+%?$', p))
        if non_numeric > len(next_parts) * 0.5:
            has_subheader = True

    # Classify each column
    classifications = [classify_column(h) for h in headers]

    # Determine overall pattern
    has_time_in_cols = any(c["has_year"] or c["has_month"] or c["has_quarter"] for c in classifications)
    has_pct_cols = any(c["has_pct_change"] for c in classifications)
    has_subcats = any(c["has_subcategory"] for c in classifications)
    has_monthly = any(c["has_month"] for c in classifications)
    has_quarterly = any(c["has_quarter"] for c in classifications)
    label_cols = sum(1 for c in classifications if c["label_col"])
    time_cols = sum(1 for c in classifications if c["has_year"] or c["has_month"] or c["has_quarter"])

    pattern = "unknown"
    if has_time_in_cols and has_subcats and has_monthly:
        pattern = "multi_dim_monthly"  # Time + sub-category in columns
    elif has_time_in_cols and has_subcats:
        pattern = "multi_dim_annual"
    elif has_time_in_cols and has_pct_cols:
        pattern = "time_with_pct_change"
    elif has_time_in_cols and has_monthly:
        pattern = "time_series_monthly"
    elif has_time_in_cols and has_quarterly:
        pattern = "time_series_quarterly"
    elif has_time_in_cols:
        pattern = "time_series_annual"
    elif label_cols == len(headers):
        pattern = "no_time_detected"

    subcategories = sorted(set(c["subcategory"] for c in classifications if c["subcategory"]))

    return {
        "table_id": table_id,
        "title": title,
        "status": "analyzed",
        "pattern": pattern,
        "headers": headers,
        "header_count": len(headers),
        "metadata_rows": len(metadata_rows),
        "has_subheader": has_subheader,
        "has_time_in_cols": has_time_in_cols,
        "has_monthly": has_monthly,
        "has_quarterly": has_quarterly,
        "has_pct_change": has_pct_cols,
        "has_subcategories": has_subcats,
        "subcategories": subcategories,
        "label_cols": label_cols,
        "time_cols": time_cols,
        "data_rows_sample": data_lines[:3],
        "raw_first_3": lines[:min(3 + header_idx, len(lines))],
    }


async def main():
    with open(DISCOVERY_PATH) as f:
        tables = json.load(f)

    csv_tables = [t for t in tables if t.get("csv_url")]
    print(f"Found {len(csv_tables)} CSV URLs in discovery JSON")
    print(f"Downloading and analyzing...\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    results = []
    async with httpx.AsyncClient(timeout=60, headers={
        "User-Agent": "DataPalestine/0.1 (open data platform)",
    }) as client:
        for i, table in enumerate(csv_tables):
            url = table["csv_url"]
            table_id = table["table_id"]
            title = table.get("title", "").replace("PCBS | ", "")

            content = await download_csv(client, url)
            if content is None:
                results.append({"table_id": table_id, "status": "download_failed", "title": title})
                continue

            # Save to disk
            filename = f"table_{table_id}.csv"
            with open(os.path.join(OUTPUT_DIR, filename), "wb") as f:
                f.write(content)

            analysis = analyze_csv(content, table_id, title)
            results.append(analysis)

            # Respect rate limits
            await asyncio.sleep(1.0)

    # Print per-file analysis
    print("=" * 80)
    print("PER-FILE ANALYSIS")
    print("=" * 80)

    for r in results:
        if r["status"] != "analyzed":
            print(f"\n[{r['table_id']}] {r.get('title', 'N/A')} — {r['status']}")
            continue

        print(f"\n{'─' * 70}")
        print(f"[{r['table_id']}] {r['title'][:70]}")
        print(f"  Pattern: {r['pattern']}")
        print(f"  Columns: {r['header_count']} ({r['label_cols']} label, {r['time_cols']} time)")
        if r['metadata_rows']:
            print(f"  Metadata rows skipped: {r['metadata_rows']}")
        if r['has_subheader']:
            print(f"  Has sub-header row: yes")
        if r['has_pct_change']:
            print(f"  Has % change columns: yes")
        if r['has_subcategories']:
            print(f"  Sub-categories: {r['subcategories']}")

        # Show first few column headers
        print(f"  Column headers:")
        for j, h in enumerate(r['headers'][:8]):
            print(f"    [{j}] {h}")
        if len(r['headers']) > 8:
            print(f"    ... +{len(r['headers']) - 8} more")

        # Show first 2 data rows
        if r.get('data_rows_sample'):
            print(f"  First data row:")
            print(f"    {r['data_rows_sample'][0][:120]}")

    # Summary report
    print("\n\n")
    print("=" * 80)
    print("SUMMARY REPORT")
    print("=" * 80)

    analyzed = [r for r in results if r["status"] == "analyzed"]
    failed = [r for r in results if r["status"] != "analyzed"]
    print(f"\nTotal CSVs: {len(csv_tables)}")
    print(f"Successfully analyzed: {len(analyzed)}")
    print(f"Failed/too short: {len(failed)}")

    # Group by pattern
    patterns = {}
    for r in analyzed:
        p = r["pattern"]
        if p not in patterns:
            patterns[p] = []
        patterns[p].append(r)

    print(f"\nDistinct column header patterns: {len(patterns)}")
    print()

    for pattern, items in sorted(patterns.items(), key=lambda x: -len(x[1])):
        print(f"  {pattern}: {len(items)} files")
        for item in items[:3]:
            print(f"    [{item['table_id']}] {item['title'][:60]}")
            if item['has_subcategories']:
                print(f"         Subcategories: {item['subcategories'][:3]}")
            print(f"         Cols: {item['headers'][:4]}")
        if len(items) > 3:
            print(f"    ... and {len(items) - 3} more")
        print()

    # Detail on time encoding
    print("TIME ENCODING:")
    monthly = [r for r in analyzed if r['has_monthly']]
    quarterly = [r for r in analyzed if r['has_quarterly']]
    annual = [r for r in analyzed if r['has_time_in_cols'] and not r['has_monthly'] and not r['has_quarterly']]
    no_time = [r for r in analyzed if not r['has_time_in_cols']]
    print(f"  Monthly precision: {len(monthly)} files")
    print(f"  Quarterly precision: {len(quarterly)} files")
    print(f"  Annual precision: {len(annual)} files")
    print(f"  No time in columns: {len(no_time)} files")

    print(f"\n% CHANGE COLUMNS:")
    pct = [r for r in analyzed if r['has_pct_change']]
    print(f"  {len(pct)} files have mixed value + % change columns")

    print(f"\nSUB-CATEGORIES IN COLUMNS:")
    sub = [r for r in analyzed if r['has_subcategories']]
    print(f"  {len(sub)} files have sub-category dimensions in column headers")
    all_subcats = set()
    for r in sub:
        all_subcats.update(r['subcategories'])
    if all_subcats:
        print(f"  Unique sub-categories found: {len(all_subcats)}")
        for s in sorted(all_subcats)[:15]:
            print(f"    - {s}")
        if len(all_subcats) > 15:
            print(f"    ... and {len(all_subcats) - 15} more")


if __name__ == "__main__":
    asyncio.run(main())
