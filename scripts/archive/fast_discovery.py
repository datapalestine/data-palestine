"""Fast PCBS discovery + download.

Shorter delay for empty pages (0.5s), full delay for content pages (1.5s).
Downloads CSVs as they're found.

Usage:
    python scripts/fast_discovery.py --start 200 --end 5000
"""

import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

PCBS_BASE = "https://www.pcbs.gov.ps"
CSV_DIR = Path("data/raw/pcbs_csv")


async def discover_and_download(start_id: int, end_id: int, output_path: str):
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    total = end_id - start_id + 1
    found = 0
    downloaded = 0

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    ) as client:
        for i, table_id in enumerate(range(start_id, end_id + 1)):
            try:
                resp = await client.get(
                    f"{PCBS_BASE}/statisticsIndicatorsTables.aspx?lang=en&table_id={table_id}",
                    follow_redirects=True,
                )
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
                await asyncio.sleep(0.5)
                continue

            if resp.status_code != 200 or len(resp.text) < 1000:
                await asyncio.sleep(0.3)  # fast skip for empty pages
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            title_el = soup.find("title")
            title = title_el.text.strip() if title_el else ""
            if not title or title in ("PCBS", "الجهاز المركزي للإحصاء الفلسطيني", "State of Palestine"):
                await asyncio.sleep(0.3)
                continue

            # Find CSV link
            csv_url = None
            for a in soup.find_all("a", href=True):
                if ".csv" in a["href"].lower():
                    csv_url = a["href"] if a["href"].startswith("http") else f"{PCBS_BASE}/{a['href'].lstrip('/')}"
                    break

            # Find XLSX link
            xlsx_url = None
            for a in soup.find_all("a", href=True):
                if ".xlsx" in a["href"].lower() or (".xls" in a["href"].lower() and ".xlsx" not in a["href"].lower()):
                    xlsx_url = a["href"] if a["href"].startswith("http") else f"{PCBS_BASE}/{a['href'].lstrip('/')}"
                    break

            # Check for HTML table
            has_html = False
            for table in soup.find_all("table"):
                rows = table.find_all("tr")
                if len(rows) >= 3:
                    text = table.get_text()
                    if len(re.findall(r"\d{2,}", text)) >= 3:
                        has_html = True
                        break

            if not csv_url and not xlsx_url and not has_html:
                await asyncio.sleep(0.3)
                continue

            found += 1
            result = {
                "table_id": table_id,
                "title": title,
                "csv_url": csv_url,
                "xlsx_url": xlsx_url,
                "has_html_table": has_html,
                "url": f"{PCBS_BASE}/statisticsIndicatorsTables.aspx?lang=en&table_id={table_id}",
            }
            results.append(result)

            # Download CSV if available and not already on disk
            if csv_url:
                csv_path = CSV_DIR / f"table_{table_id}.csv"
                if not csv_path.exists():
                    try:
                        csv_resp = await client.get(csv_url, follow_redirects=True)
                        if csv_resp.status_code == 200 and len(csv_resp.content) > 10:
                            csv_path.write_bytes(csv_resp.content)
                            downloaded += 1
                    except Exception:
                        pass

            if found % 20 == 0:
                logger.info("[%d/%d] id=%d — %d found, %d downloaded", i + 1, total, table_id, found, downloaded)
                # Incremental save every 20 tables found
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)

            await asyncio.sleep(1.5)  # respectful delay for content pages

    # Final save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDiscovery complete:")
    print(f"  IDs scanned:     {total}")
    print(f"  Tables found:    {found}")
    print(f"  With CSV:        {sum(1 for r in results if r['csv_url'])}")
    print(f"  CSVs downloaded: {downloaded}")
    print(f"  Results saved:   {output_path}")

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=200)
    parser.add_argument("--end", type=int, default=5000)
    parser.add_argument("--output", type=str, default="data/pcbs_discovery_200_5000.json")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    asyncio.run(discover_and_download(args.start, args.end, args.output))


if __name__ == "__main__":
    main()
