"""PCBS CSV parser — pattern detector + pattern-specific parsers.

Handles all 6 column header patterns found across 82 PCBS CSV files.
Each parser returns a list of RawObservation dataclass instances.

Usage:
    from pcbs.csv_parser import detect_pattern, parse_csv
    pattern = detect_pattern("data/raw/pcbs_csv/table_27.csv")
    observations = parse_csv("data/raw/pcbs_csv/table_27.csv")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


# ─── Types ──────────────────────────────────────────────

@dataclass
class RawObservation:
    """A single parsed data point from a PCBS CSV."""
    indicator_name: str
    time_period: date
    time_precision: str  # "month", "quarter", "year"
    value: float
    dimensions: dict = field(default_factory=dict)
    unit: str = ""
    is_pct_change: bool = False
    geography_code: str = "PS"


PATTERNS = [
    "multirow_subcategory",     # 1a: row1=sub-cats, row2=time
    "multirow_region",          # 1b: row1=region, row2=time (CPI)
    "metadata_quarterly",       # 1c: metadata rows + quarterly columns
    "static_snapshot",          # 1d: no time dimension at all
    "time_in_rows",             # 1e: year in first column, indicators in columns
    "time_with_pct_change",     # 2:  single-row header, month+year + % change
    "time_series_annual",       # 3:  single-row header, year columns
    "multi_dim_monthly",        # 4:  single-row header, month+year+subcategory
    "time_series_quarterly",    # 5:  single-row header, Q1/2019 format
]


# ─── Month / time parsing helpers ────────────────────────

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

MONTH_RE = re.compile(
    r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    r'\.?\s*(\d{4})',
    re.IGNORECASE,
)

QUARTER_RE = re.compile(r'Q(\d)[/\-\s](\d{4})|(\d{4})\s*Q(\d)', re.IGNORECASE)

AVG_RE = re.compile(r'Avg\.?\s*\([\d\-]+\)[\\\/](\d{4})', re.IGNORECASE)

YEAR_RE = re.compile(r'^(\d{4})\*{0,3}$')

PCT_RE = re.compile(r'%\s*[Cc]hange|[Pp]ercent\s*[Cc]hange|التغير', re.IGNORECASE)

REGION_MAP = {
    "palestine": "PS",
    "west bank": "PS-WBK",
    "gaza strip": "PS-GZA",
    "gaza": "PS-GZA",
}

REGION_RE = re.compile(r'^(Palestine|West\s+Bank\s*\*{0,2}|Gaza\s+Strip?)$', re.IGNORECASE)


def parse_time_from_string(s: str) -> tuple[date, str] | None:
    """Try to parse a date from a column header string.

    Returns (date, precision) or None.
    """
    s = s.strip().rstrip("*")

    # Quarter: Q1-2014, Q1/2019, 2014Q1
    m = QUARTER_RE.search(s)
    if m:
        if m.group(1) and m.group(2):
            q, y = int(m.group(1)), int(m.group(2))
        else:
            y, q = int(m.group(3)), int(m.group(4))
        month = {1: 1, 2: 4, 3: 7, 4: 10}.get(q, 1)
        return date(y, month, 1), "quarter"

    # Annual average: Avg. (1-4)\2019
    m = AVG_RE.search(s)
    if m:
        return date(int(m.group(1)), 1, 1), "year"

    # "Year YYYY" pattern (Balance of Payments annual totals)
    m = re.match(r'^Year\s+(\d{4})\*{0,3}$', s, re.IGNORECASE)
    if m:
        return date(int(m.group(1)), 1, 1), "year"

    # Month + year: Jan. 2020, May 2020, March 2020
    m = MONTH_RE.search(s)
    if m:
        month_name = m.group(1).lower().rstrip(".")
        month_num = MONTH_MAP.get(month_name)
        year = int(m.group(2))
        if month_num and 1990 <= year <= 2030:
            return date(year, month_num, 1), "month"

    # Plain year: 2020, 1997
    m = YEAR_RE.match(s.strip())
    if m:
        y = int(m.group(1))
        if 1948 <= y <= 2030:
            return date(y, 1, 1), "year"

    return None


def is_pct_change_col(s: str) -> bool:
    return bool(PCT_RE.search(s))


def clean_cell(s: str) -> str:
    """Clean a cell value: strip footnote markers, replacement chars, NBSP."""
    s = s.strip()
    # Strip trailing footnote markers: *, **, ***, superscript digits
    s = re.sub(r'[\*]+$', '', s)
    s = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]+$', '', s)
    # Strip replacement character and adjacent whitespace
    s = s.replace('\ufffd', ' ')
    # Strip non-breaking spaces, zero-width spaces
    s = s.replace('\xa0', ' ').replace('\u200b', '').replace('\u200c', '').replace('\ufeff', '')
    # Collapse multiple spaces
    s = re.sub(r' {2,}', ' ', s)
    return s.strip()


def parse_csv_rows(filepath: str | Path) -> list[list[str]]:
    """Read a CSV file with robust encoding detection."""
    path = Path(filepath)
    raw = path.read_bytes()

    # Try encodings in order
    content = None
    for encoding in ("utf-8-sig", "utf-8", "windows-1256", "iso-8859-1"):
        try:
            content = raw.decode(encoding)
            # Check for replacement characters — if too many, try next encoding
            if content.count('\ufffd') > 3 and encoding != "iso-8859-1":
                continue
            break
        except (UnicodeDecodeError, ValueError):
            continue

    if content is None:
        content = raw.decode("utf-8-sig", errors="replace")

    lines = content.strip().split("\n")
    rows = []
    for line in lines:
        # Strip \r from Windows line endings
        line = line.rstrip('\r')
        # Simple CSV split (PCBS files don't use quoted fields with commas)
        cells = [clean_cell(c.strip('"')) for c in line.split(",")]
        rows.append(cells)
    return rows


def try_float(s: str) -> float | None:
    """Try to parse a string as a float."""
    s = s.strip().replace(",", "").replace("٫", ".")
    if not s or s in ("-", "..", "...", "—", "–", "N/A", "n/a"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ─── Pattern Detection ──────────────────────────────────

def detect_pattern(filepath: str | Path) -> str:
    """Classify a PCBS CSV file into one of the known patterns."""
    rows = parse_csv_rows(filepath)
    if len(rows) < 2:
        return "static_snapshot"

    # Skip metadata/title rows to find the actual header pair
    # Metadata rows: very few non-empty cells, or contain title text
    # Skip leading metadata/title rows
    start = 0
    for i in range(min(5, len(rows))):
        if is_metadata_row(rows[i]):
            start = i + 1
        else:
            break

    row0 = rows[start] if start < len(rows) else rows[0]
    row1 = rows[start + 1] if start + 1 < len(rows) else []

    non_empty_0 = [c for c in row0 if c.strip()]
    non_empty_1 = [c for c in row1 if c.strip()]

    # Check any row in first 6 for quarterly data (metadata_quarterly)
    for r in rows[:6]:
        quarterly_count = sum(1 for c in r if c and QUARTER_RE.search(c))
        if quarterly_count >= 3:
            return "metadata_quarterly"

    # Check if first column values are years (time_in_rows)
    first_col_name = row0[0].lower().strip() if row0 else ""
    if first_col_name in ("year", "السنة"):
        return "time_in_rows"
    # Also detect by checking data rows for year values in col 0
    if len(rows) > start + 2:
        year_count = sum(
            1 for r in rows[start + 2:min(start + 6, len(rows))]
            if r and r[0].strip() and YEAR_RE.match(r[0].strip())
        )
        if year_count >= 2:
            return "time_in_rows"

    # Check row0 for time-like column headers (single-row header patterns)
    time_in_row0 = sum(1 for c in row0[1:] if c and parse_time_from_string(c) is not None)
    pct_in_row0 = sum(1 for c in row0[1:] if c and is_pct_change_col(c))

    if time_in_row0 > 0:
        # All years → annual time series
        year_cols = [c for c in row0[1:] if c and YEAR_RE.match(c.strip())]
        if len(year_cols) >= 3 and len(year_cols) == time_in_row0:
            return "time_series_annual"

        # Quarterly (Q1/2019)
        quarterly = sum(1 for c in row0[1:] if c and QUARTER_RE.search(c))
        if quarterly >= 2:
            return "time_series_quarterly"

        # Multi-dim monthly: month+year+subcategory in one header cell
        monthly_with_extra = 0
        for c in row0[1:]:
            if not c:
                continue
            m = MONTH_RE.search(c)
            if m:
                remainder = (c[:m.start()] + " " + c[m.end():]).strip(" -–—")
                if remainder and not is_pct_change_col(remainder):
                    monthly_with_extra += 1
        if monthly_with_extra >= 2:
            return "multi_dim_monthly"

        # Time + pct change, or just monthly
        if pct_in_row0 >= 1 or time_in_row0 >= 2:
            return "time_with_pct_change"

    # Multi-row header: row0 has sparse values (labels/groups), row1 has time
    # Use a more generous threshold: non_empty_0 <= 50% of columns
    if len(non_empty_0) <= len(row0) * 0.5 and len(non_empty_1) > 2:
        time_in_row1 = sum(1 for c in row1 if c and parse_time_from_string(c) is not None)
        if time_in_row1 >= 2:
            # Check if row0 values (excluding first label col) are region names
            group_values = [c.strip() for c in non_empty_0[1:] if c.strip()]
            is_region = len(group_values) > 0 and all(
                REGION_RE.match(v) for v in group_values
            )
            if is_region:
                return "multirow_region"
            return "multirow_subcategory"

    # Fallback
    return "static_snapshot"


# ─── Pattern-Specific Parsers ───────────────────────────

def is_metadata_row(row: list[str]) -> bool:
    """Check if a row is a title/note/metadata line, not a data header."""
    non_empty = [c for c in row if c.strip()]
    if len(non_empty) == 0:
        return True
    # A metadata row has mostly empty cells with one long text cell
    if len(non_empty) <= 2 and len(row) > 4:
        first = row[0].strip().lower()
        # Title row: long text describing the table
        if len(first) > 30:
            return True
        # Note row: starts with parenthetical or asterisk
        if first.startswith("(") or first.startswith("*") or first.startswith("source"):
            return True
        # "Base Year" note
        if "base year" in first:
            return True
        # "Values in million" etc
        if "values in" in first:
            return True
    return False


def find_header_pair(rows: list[list[str]]) -> tuple[int, int]:
    """Find the sub-category row and time row in a multi-row header CSV.

    Scans the first 6 rows and identifies:
    - Sub-category row: sparse labels with many empty cells (forward-fill pattern)
    - Time row: contains month+year or other time patterns

    Returns (subcat_row_idx, time_row_idx).
    """
    time_row = -1
    subcat_row = -1

    for i in range(min(6, len(rows))):
        row = rows[i]
        non_empty = [c for c in row if c.strip()]

        # Skip pure metadata rows
        if is_metadata_row(row):
            continue

        # Check if this row has time values
        time_count = sum(1 for c in row[1:] if c and parse_time_from_string(c) is not None)
        if time_count >= 2:
            time_row = i
            continue

        # Check if this row is sparse (sub-category labels with gaps)
        # A sub-category row has < 50% cells filled and at least 2 non-empty
        if 2 <= len(non_empty) <= len(row) * 0.5:
            # Make sure it's not a data row (data rows have many numeric values)
            numeric_count = sum(1 for c in row[1:] if c and try_float(c) is not None)
            if numeric_count < len(non_empty) * 0.5:
                subcat_row = i

    # If we didn't find a time row, fall back to the row after subcat
    if time_row == -1 and subcat_row >= 0 and subcat_row + 1 < len(rows):
        time_row = subcat_row + 1

    # If no subcat row found, the row before time is the subcat
    if subcat_row == -1 and time_row > 0:
        subcat_row = time_row - 1

    # Ensure subcat comes before time
    if subcat_row >= time_row and time_row >= 0:
        subcat_row = time_row - 1

    return max(0, subcat_row), max(0, time_row)


def parse_csv(filepath: str | Path, publication_date: date | None = None) -> list[RawObservation]:
    """Detect pattern and parse a PCBS CSV file."""
    pattern = detect_pattern(filepath)
    rows = parse_csv_rows(filepath)

    # Multi-row parsers handle metadata skipping internally via find_header_pair

    parsers = {
        "multirow_subcategory": parse_multirow_subcategory,
        "multirow_region": parse_multirow_region,
        "metadata_quarterly": parse_metadata_quarterly,
        "static_snapshot": parse_static_snapshot,
        "time_in_rows": parse_time_in_rows,
        "time_with_pct_change": parse_time_with_pct_change,
        "time_series_annual": parse_time_series_annual,
        "multi_dim_monthly": parse_multi_dim_monthly,
        "time_series_quarterly": parse_time_series_quarterly,
    }

    parser = parsers.get(pattern, parse_static_snapshot)
    return parser(rows, publication_date)


def parse_multirow_subcategory(rows: list[list[str]], pub_date: date | None = None) -> list[RawObservation]:
    """Pattern 1a: Sub-category groups (forward-fill) + time periods in a header pair."""
    if len(rows) < 3:
        return []

    subcat_idx, time_idx = find_header_pair(rows)
    row0 = rows[subcat_idx]
    row1 = rows[time_idx]
    data_start = time_idx + 1

    # Forward-fill row0 sub-categories
    subcats = []
    current_subcat = ""
    for c in row0:
        if c.strip():
            current_subcat = c.strip()
        subcats.append(current_subcat)

    # Parse time from row1
    col_info: list[tuple[date, str, str, bool] | None] = [None]  # skip label column
    for i in range(1, max(len(row1), len(subcats))):
        cell = row1[i] if i < len(row1) else ""
        subcat = subcats[i] if i < len(subcats) else ""
        pct = is_pct_change_col(cell)

        t = parse_time_from_string(cell)
        if t:
            col_info.append((t[0], t[1], subcat, pct))
        elif pct:
            # % Change column without explicit time — use None time, will skip
            col_info.append(None)
        else:
            col_info.append(None)

    # Parse data rows (starting after the time header row)
    observations = []
    for row in rows[data_start:]:
        if not row or not row[0].strip():
            continue
        indicator = row[0].strip()
        if not indicator or indicator.lower() in ("total", "general index"):
            pass  # keep these, they're valid indicators

        for i in range(1, min(len(row), len(col_info))):
            info = col_info[i]
            if info is None:
                continue
            tp, prec, subcat, pct = info
            val = try_float(row[i])
            if val is None:
                continue

            name = f"{indicator} (% Change)" if pct else indicator
            dims = {}
            label_col = subcats[0] if subcats else ""
            if subcat and subcat != label_col:
                dims["subcategory"] = subcat

            observations.append(RawObservation(
                indicator_name=name,
                time_period=tp,
                time_precision=prec,
                value=val,
                dimensions=dims,
                unit="percent" if pct else "",
                is_pct_change=pct,
            ))

    return observations


def parse_multirow_region(rows: list[list[str]], pub_date: date | None = None) -> list[RawObservation]:
    """Pattern 1b: Region names (Palestine, West Bank, Gaza) + time in a header pair."""
    if len(rows) < 3:
        return []

    subcat_idx, time_idx = find_header_pair(rows)
    row0 = rows[subcat_idx]
    row1 = rows[time_idx]
    data_start = time_idx + 1

    # Forward-fill row0 regions
    regions = []
    current_region = ""
    for c in row0:
        if c.strip():
            current_region = c.strip()
        regions.append(current_region)

    # Parse time from row1
    col_info: list[tuple[date, str, str, bool] | None] = [None]
    for i in range(1, max(len(row1), len(regions))):
        cell = row1[i] if i < len(row1) else ""
        region = regions[i] if i < len(regions) else ""
        pct = is_pct_change_col(cell)

        t = parse_time_from_string(cell)
        if t:
            geo_code = "PS"
            for rname, rcode in REGION_MAP.items():
                if rname in region.lower():
                    geo_code = rcode
                    break
            col_info.append((t[0], t[1], geo_code, pct))
        elif pct:
            col_info.append(None)
        else:
            col_info.append(None)

    observations = []
    for row in rows[data_start:]:
        if not row or not row[0].strip():
            continue
        indicator = row[0].strip()

        for i in range(1, min(len(row), len(col_info))):
            info = col_info[i]
            if info is None:
                continue
            tp, prec, geo, pct = info
            val = try_float(row[i])
            if val is None:
                continue

            name = f"{indicator} (% Change)" if pct else indicator
            observations.append(RawObservation(
                indicator_name=name,
                time_period=tp,
                time_precision=prec,
                value=val,
                unit="percent" if pct else "",
                is_pct_change=pct,
                geography_code=geo,
            ))

    return observations


def parse_metadata_quarterly(rows: list[list[str]], pub_date: date | None = None) -> list[RawObservation]:
    """Pattern 1c: Metadata rows, then quarterly data. Also handles mixed Q + Year columns."""
    # Find the header row (first row with multiple quarterly values)
    header_idx = 0
    for i, row in enumerate(rows):
        quarterly_count = sum(1 for c in row if c and QUARTER_RE.search(c))
        time_count = sum(1 for c in row if c and parse_time_from_string(c) is not None)
        if quarterly_count >= 3 or time_count >= 4:
            header_idx = i
            break

    if header_idx >= len(rows) - 1:
        return []

    header = rows[header_idx]

    # Determine label columns (non-time columns at the start)
    label_cols = 0
    for c in header:
        if c and parse_time_from_string(c) is not None:
            break
        label_cols += 1

    # Parse time from header
    col_times: list[tuple[date, str] | None] = [None] * label_cols
    for i in range(label_cols, len(header)):
        t = parse_time_from_string(header[i])
        col_times.append(t)

    observations = []
    for row in rows[header_idx + 1:]:
        if not row:
            continue
        # Build indicator name from label columns
        label_parts = [row[j].strip() for j in range(min(label_cols, len(row))) if row[j].strip()]
        if not label_parts:
            continue
        indicator = " - ".join(label_parts)

        for i in range(label_cols, min(len(row), len(col_times))):
            if col_times[i] is None:
                continue
            tp, prec = col_times[i]
            val = try_float(row[i])
            if val is None:
                continue

            observations.append(RawObservation(
                indicator_name=indicator,
                time_period=tp,
                time_precision=prec,
                value=val,
            ))

    return observations


def parse_static_snapshot(rows: list[list[str]], pub_date: date | None = None) -> list[RawObservation]:
    """Pattern 1d: No time dimension. Use publication_date or 2020-01-01 as fallback."""
    if len(rows) < 2:
        return []

    tp = pub_date or date(2020, 1, 1)

    # Find header row
    header_idx = 0
    for i, row in enumerate(rows):
        non_empty = [c for c in row if c.strip()]
        if len(non_empty) >= 2:
            header_idx = i
            break

    header = rows[header_idx]
    observations = []

    for row in rows[header_idx + 1:]:
        if not row or not row[0].strip():
            continue
        indicator = row[0].strip()

        for i in range(1, min(len(row), len(header))):
            val = try_float(row[i])
            if val is None:
                continue
            col_name = header[i].strip()
            if not col_name:
                continue

            # Detect unit from column header
            unit = ""
            if "(Gg)" in col_name:
                unit = "Gg"
            elif "%" in col_name:
                unit = "percent"
            elif "million" in col_name.lower():
                unit = "million USD"

            observations.append(RawObservation(
                indicator_name=f"{indicator} - {col_name}" if col_name != indicator else indicator,
                time_period=tp,
                time_precision="year",
                value=val,
                unit=unit,
            ))

    return observations


def parse_time_in_rows(rows: list[list[str]], pub_date: date | None = None) -> list[RawObservation]:
    """Pattern 1e: First column is Year, columns are indicators.
    Multi-row column headers merged: row0=category, row1=sub-category.
    """
    if len(rows) < 3:
        return []

    row0 = rows[0]
    row1 = rows[1]

    # Forward-fill row0 for category grouping
    categories = []
    current = ""
    for c in row0:
        if c.strip() and c.strip().lower() != "year":
            current = c.strip()
        categories.append(current)

    # Merge row0 + row1 into indicator names
    indicators = []
    for i in range(len(row1)):
        cat = categories[i] if i < len(categories) else ""
        sub = row1[i].strip() if i < len(row1) else ""
        if cat and sub:
            indicators.append(f"{cat} - {sub}")
        elif sub:
            indicators.append(sub)
        elif cat:
            indicators.append(cat)
        else:
            indicators.append("")

    observations = []
    for row in rows[2:]:
        if not row or not row[0].strip():
            continue
        year_val = try_float(row[0])
        if year_val is None or year_val < 1948 or year_val > 2030:
            continue
        tp = date(int(year_val), 1, 1)

        for i in range(1, min(len(row), len(indicators))):
            if not indicators[i]:
                continue
            val = try_float(row[i])
            if val is None:
                continue

            observations.append(RawObservation(
                indicator_name=indicators[i],
                time_period=tp,
                time_precision="year",
                value=val,
            ))

    return observations


def parse_time_with_pct_change(rows: list[list[str]], pub_date: date | None = None) -> list[RawObservation]:
    """Pattern 2: Single-row header with month+year columns interleaved with % Change."""
    if len(rows) < 2:
        return []

    header = rows[0]

    col_info: list[tuple[date, str, bool] | None] = [None]  # skip label col
    for i in range(1, len(header)):
        cell = header[i]
        pct = is_pct_change_col(cell)
        t = parse_time_from_string(cell)
        if t:
            col_info.append((t[0], t[1], pct))
        elif pct:
            # Standalone "% Change" — skip (no time)
            col_info.append(None)
        else:
            col_info.append(None)

    observations = []
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        indicator = row[0].strip()

        for i in range(1, min(len(row), len(col_info))):
            info = col_info[i]
            if info is None:
                continue
            tp, prec, pct = info
            val = try_float(row[i])
            if val is None:
                continue

            name = f"{indicator} (% Change)" if pct else indicator
            observations.append(RawObservation(
                indicator_name=name,
                time_period=tp,
                time_precision=prec,
                value=val,
                unit="percent" if pct else "",
                is_pct_change=pct,
            ))

    return observations


def parse_time_series_annual(rows: list[list[str]], pub_date: date | None = None) -> list[RawObservation]:
    """Pattern 3: Single-row header with year columns (1997, 1998, ...)."""
    if len(rows) < 2:
        return []

    header = rows[0]

    col_times: list[tuple[date, str] | None] = [None]
    for i in range(1, len(header)):
        t = parse_time_from_string(header[i])
        col_times.append(t)

    observations = []
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        indicator = row[0].strip()

        for i in range(1, min(len(row), len(col_times))):
            if col_times[i] is None:
                continue
            tp, prec = col_times[i]
            val = try_float(row[i])
            if val is None:
                continue

            observations.append(RawObservation(
                indicator_name=indicator,
                time_period=tp,
                time_precision=prec,
                value=val,
            ))

    return observations


def parse_multi_dim_monthly(rows: list[list[str]], pub_date: date | None = None) -> list[RawObservation]:
    """Pattern 4: Single-row header with {month year subcategory} combined.
    e.g., 'May 2020 Residential buildings', 'March 2020 - Local'
    """
    if len(rows) < 2:
        return []

    header = rows[0]

    col_info: list[tuple[date, str, str, bool] | None] = [None]
    for i in range(1, len(header)):
        cell = header[i]
        pct = is_pct_change_col(cell)

        m = MONTH_RE.search(cell)
        if m:
            month_name = m.group(1).lower().rstrip(".")
            month_num = MONTH_MAP.get(month_name, 1)
            year = int(m.group(2))
            tp = date(year, month_num, 1)
            # Extract subcategory: everything not the time part
            remainder = (cell[:m.start()] + " " + cell[m.end():]).strip()
            remainder = remainder.strip(" -–—")
            # Also strip % change part
            remainder = PCT_RE.sub("", remainder).strip(" -–—")
            col_info.append((tp, "month", remainder, pct))
        elif pct:
            # Standalone "% Change - Local" — extract subcategory but no time
            remainder = PCT_RE.sub("", cell).strip(" -–—")
            col_info.append(None)
        else:
            col_info.append(None)

    observations = []
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        indicator = row[0].strip()

        for i in range(1, min(len(row), len(col_info))):
            info = col_info[i]
            if info is None:
                continue
            tp, prec, subcat, pct = info
            val = try_float(row[i])
            if val is None:
                continue

            name = f"{indicator} (% Change)" if pct else indicator
            dims = {}
            if subcat:
                dims["subcategory"] = subcat

            observations.append(RawObservation(
                indicator_name=name,
                time_period=tp,
                time_precision=prec,
                value=val,
                dimensions=dims,
                unit="percent" if pct else "",
                is_pct_change=pct,
            ))

    return observations


def parse_time_series_quarterly(rows: list[list[str]], pub_date: date | None = None) -> list[RawObservation]:
    """Pattern 5: Single-row header with Q1/2019, Q4-2013 columns.
    May also have annual columns like '2019**' or 'Year 2019'.
    """
    if len(rows) < 2:
        return []

    header = rows[0]

    col_times: list[tuple[date, str] | None] = [None]
    for i in range(1, len(header)):
        t = parse_time_from_string(header[i])
        col_times.append(t)

    observations = []
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        indicator = row[0].strip()

        for i in range(1, min(len(row), len(col_times))):
            if col_times[i] is None:
                continue
            tp, prec = col_times[i]
            val = try_float(row[i])
            if val is None:
                continue

            observations.append(RawObservation(
                indicator_name=indicator,
                time_period=tp,
                time_precision=prec,
                value=val,
            ))

    return observations
