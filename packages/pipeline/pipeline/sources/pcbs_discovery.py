"""PCBS statistical table discovery crawler.

Scans PCBS statisticsIndicatorsTables pages to find downloadable CSV/XLSX files.
Respects PCBS servers with a 2-second delay between requests.

Usage:
    python pcbs_discovery.py [--start 1] [--end 200] [--output data/pcbs_discovery.json]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

PCBS_BASE = "https://www.pcbs.gov.ps"
TABLE_URL_TEMPLATE = f"{PCBS_BASE}/statisticsIndicatorsTables.aspx?lang=en&table_id={{table_id}}"
REQUEST_DELAY = 2.0  # seconds between requests — be respectful


async def discover_table(client: httpx.AsyncClient, table_id: int) -> dict | None:
    """Check a single PCBS table page for downloadable data links.

    Returns None if the page doesn't exist or is empty/error.
    """
    url = TABLE_URL_TEMPLATE.format(table_id=table_id)

    try:
        resp = await client.get(url, follow_redirects=True)
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
        logger.warning("  table_id=%d: connection error: %s", table_id, e)
        return None

    if resp.status_code != 200:
        return None

    html = resp.text

    # Skip empty/error pages — PCBS returns 200 even for missing tables
    # but the page body is mostly empty or shows an error message
    if len(html) < 1000:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Extract page title
    title_el = soup.find("title")
    title = title_el.text.strip() if title_el else ""

    # Skip generic/empty pages (the default PCBS template title)
    if not title or title in (
        "PCBS",
        "الجهاز المركزي للإحصاء الفلسطيني",
        "State of Palestine",
    ):
        return None

    # Find CSV download link
    csv_url = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".csv" in href.lower():
            csv_url = href if href.startswith("http") else f"{PCBS_BASE}/{href.lstrip('/')}"
            break

    # Find XLSX/XLS download link
    xlsx_url = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".xlsx" in href.lower() or (
            ".xls" in href.lower() and ".xlsx" not in href.lower()
        ):
            xlsx_url = href if href.startswith("http") else f"{PCBS_BASE}/{href.lstrip('/')}"
            break

    # Check for HTML data tables on the page
    # PCBS uses ASP.NET GridView controls and standard HTML tables
    has_html_table = False
    for table in soup.find_all("table"):
        # Look for tables with actual data rows (not layout tables)
        rows = table.find_all("tr")
        if len(rows) >= 3:  # header + at least 2 data rows
            # Check if it has numeric content (data table vs navigation table)
            text = table.get_text()
            import re
            numbers = re.findall(r"\d{2,}", text)
            if len(numbers) >= 3:
                has_html_table = True
                break

    # Skip pages that have no data at all
    if not csv_url and not xlsx_url and not has_html_table:
        return None

    return {
        "table_id": table_id,
        "title": title,
        "csv_url": csv_url,
        "xlsx_url": xlsx_url,
        "has_html_table": has_html_table,
        "url": url,
    }


async def run_discovery(start_id: int, end_id: int) -> list[dict]:
    """Crawl a range of PCBS table IDs and discover available data."""
    results = []
    total = end_id - start_id + 1

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        headers={
            "User-Agent": "DataPalestine/0.1 (open data platform; https://datapalestine.org)",
            "Accept": "text/html",
            "Accept-Language": "en",
        },
    ) as client:
        for i, table_id in enumerate(range(start_id, end_id + 1)):
            progress = f"[{i + 1}/{total}]"

            result = await discover_table(client, table_id)

            if result:
                flags = []
                if result["csv_url"]:
                    flags.append("CSV")
                if result["xlsx_url"]:
                    flags.append("XLSX")
                if result["has_html_table"]:
                    flags.append("HTML")
                logger.info(
                    "  %s table_id=%d: %s [%s]",
                    progress, table_id, result["title"][:70], ", ".join(flags),
                )
                results.append(result)
            else:
                # Only log every 10 empty pages to reduce noise
                if table_id % 10 == 0:
                    logger.debug("  %s table_id=%d: empty/missing", progress, table_id)

            # Respect PCBS servers
            await asyncio.sleep(REQUEST_DELAY)

    return results


def print_summary(results: list[dict]) -> None:
    """Print a summary of the discovery sweep."""
    total = len(results)
    with_csv = sum(1 for r in results if r["csv_url"])
    with_xlsx = sum(1 for r in results if r["xlsx_url"])
    with_html = sum(1 for r in results if r["has_html_table"])
    with_any_download = sum(1 for r in results if r["csv_url"] or r["xlsx_url"])

    print("\n" + "=" * 60)
    print("PCBS DISCOVERY SWEEP — RESULTS")
    print("=" * 60)
    print(f"  Tables found:          {total}")
    print(f"  With CSV download:     {with_csv}")
    print(f"  With XLSX download:    {with_xlsx}")
    print(f"  With HTML data table:  {with_html}")
    print(f"  With any download:     {with_any_download}")
    print()

    if with_csv > 0:
        print("CSV download links found:")
        for r in results:
            if r["csv_url"]:
                print(f"  [{r['table_id']}] {r['title'][:60]}")
                print(f"       {r['csv_url']}")
        print()

    if with_xlsx > 0:
        print("XLSX download links found:")
        for r in results:
            if r["xlsx_url"]:
                print(f"  [{r['table_id']}] {r['title'][:60]}")
                print(f"       {r['xlsx_url']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="PCBS statistical table discovery crawler")
    parser.add_argument("--start", type=int, default=1, help="Starting table_id")
    parser.add_argument("--end", type=int, default=200, help="Ending table_id")
    parser.add_argument(
        "--output", type=str, default="data/pcbs_discovery.json",
        help="Output JSON file path",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    print(f"PCBS Discovery: scanning table_ids {args.start} to {args.end}...")
    print(f"  Delay: {REQUEST_DELAY}s between requests")
    print(f"  Output: {args.output}")
    print()

    results = asyncio.run(run_discovery(args.start, args.end))

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print_summary(results)
    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
