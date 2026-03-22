#!/usr/bin/env python3
"""Extended PCBS data sweep:
A) Catalogue ZIP downloads (Excel archives)
B) Arabic CSVs for existing tables
C) Archive PDFs found
"""

import io
import json
import logging
import time
import zipfile
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(message)s")

DELAY = 2  # seconds between requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 DataPalestine/1.0",
}

CATALOGUE_ZIP_DIR = Path("data/raw/pcbs_catalogue")
ARABIC_CSV_DIR = Path("data/raw/pcbs_csv")
PDF_DIR = Path("data/raw/pcbs_pdf")

client = httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True)


def source_a_catalogue_zips():
    """Scan PCBS catalogue for Excel ZIP downloads."""
    print("=" * 60)
    print("SOURCE A: PCBS Statistical Data Catalogue ZIP Downloads")
    print("=" * 60)

    CATALOGUE_ZIP_DIR.mkdir(parents=True, exist_ok=True)

    found = 0
    failed = 0
    xlsx_extracted = 0
    pdf_count = 0

    # Range scan N=1 to 500
    for n in range(1, 501):
        url = f"https://www.pcbs.gov.ps/Downloads/ZIP/{n}-x.zip"
        dest = CATALOGUE_ZIP_DIR / f"{n}-x.zip"

        if dest.exists() and dest.stat().st_size > 0:
            found += 1
            continue

        try:
            resp = client.get(url)
            if resp.status_code == 404:
                continue
            if resp.status_code != 200:
                continue

            # Check if it's actually a ZIP
            content = resp.content
            if len(content) < 100:
                continue
            if not content[:2] == b'PK':
                # Not a ZIP file
                continue

            dest.write_bytes(content)
            found += 1

            # Extract and catalog contents
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    names = zf.namelist()
                    xlsx_files = [n for n in names if n.lower().endswith(('.xlsx', '.xls'))]
                    pdf_files = [n for n in names if n.lower().endswith('.pdf')]

                    if xlsx_files:
                        # Extract Excel files
                        extract_dir = CATALOGUE_ZIP_DIR / f"extracted_{n}"
                        extract_dir.mkdir(exist_ok=True)
                        for xf in xlsx_files:
                            try:
                                zf.extract(xf, extract_dir)
                                xlsx_extracted += 1
                            except Exception:
                                pass

                    if pdf_files:
                        PDF_DIR.mkdir(parents=True, exist_ok=True)
                        for pf in pdf_files:
                            try:
                                zf.extract(pf, PDF_DIR)
                                pdf_count += 1
                            except Exception:
                                pass

                    print(f"  N={n:>3}: OK ({len(content):>8,} bytes) "
                          f"[{len(xlsx_files)} xlsx, {len(pdf_files)} pdf] "
                          f"{', '.join(names[:3])}")
            except zipfile.BadZipFile:
                print(f"  N={n:>3}: Downloaded but bad ZIP ({len(content):,} bytes)")
                dest.unlink(missing_ok=True)
                found -= 1

        except Exception as e:
            failed += 1
            if n % 100 == 0:
                print(f"  N={n}: error {e}")

        if n % 50 == 0:
            print(f"  ... scanned {n}/500 ({found} found so far)")

        time.sleep(DELAY)

    print(f"\nCatalogue scan complete:")
    print(f"  ZIP files found: {found}")
    print(f"  Excel files extracted: {xlsx_extracted}")
    print(f"  PDF files archived: {pdf_count}")
    print(f"  Failed: {failed}")

    return found, xlsx_extracted, pdf_count


def source_b_arabic_csvs():
    """Download Arabic versions of existing table CSVs."""
    print("\n" + "=" * 60)
    print("SOURCE B: Arabic CSVs for Existing Tables")
    print("=" * 60)

    # Load discovery data to get table IDs with CSV links
    all_tables = []
    for fname in ["data/pcbs_discovery.json", "data/pcbs_discovery_200_5000.json"]:
        p = Path(fname)
        if p.exists():
            with open(p) as f:
                all_tables.extend(json.load(f))

    csv_tables = [t for t in all_tables if t.get("csv_url")]
    print(f"Tables with English CSV: {len(csv_tables)}")

    downloaded = 0
    skipped = 0
    failed = 0

    for t in csv_tables:
        table_id = t["table_id"]
        dest = ARABIC_CSV_DIR / f"table_{table_id}_ar.csv"

        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
            continue

        # Arabic version URL
        ar_url = f"https://www.pcbs.gov.ps/statisticsIndicatorsTables.aspx?lang=ar&table_id={table_id}"

        try:
            resp = client.get(ar_url)
            resp.raise_for_status()
            html = resp.text

            # Find CSV download link in Arabic page
            import re
            csv_match = re.search(r'href="([^"]*\.csv[^"]*)"', html, re.IGNORECASE)
            if not csv_match:
                continue

            csv_url = csv_match.group(1)
            if not csv_url.startswith("http"):
                csv_url = f"https://www.pcbs.gov.ps{csv_url}"

            # Download the Arabic CSV
            csv_resp = client.get(csv_url)
            csv_resp.raise_for_status()
            dest.write_bytes(csv_resp.content)
            downloaded += 1

            if downloaded % 50 == 0:
                print(f"  Downloaded {downloaded} Arabic CSVs...")

        except Exception:
            failed += 1

        time.sleep(DELAY)

    print(f"\nArabic CSV download complete:")
    print(f"  Downloaded: {downloaded}")
    print(f"  Already had: {skipped}")
    print(f"  Failed/no Arabic CSV: {failed}")

    return downloaded


def main():
    # Source A: Catalogue ZIPs (range scan takes ~17 min at 2s delay)
    zips_found, xlsx_count, pdf_count = source_a_catalogue_zips()

    # Source B: Arabic CSVs (takes longer — 2450 tables × 2s × 2 requests = ~2.7 hours)
    # Run a smaller batch first to test
    ar_count = source_b_arabic_csvs()

    print("\n" + "=" * 60)
    print("EXTENDED SWEEP SUMMARY")
    print("=" * 60)
    print(f"  Catalogue ZIPs found: {zips_found}")
    print(f"  Excel files extracted: {xlsx_count}")
    print(f"  PDFs archived: {pdf_count}")
    print(f"  Arabic CSVs downloaded: {ar_count}")

    # Count files
    xlsx_dir = CATALOGUE_ZIP_DIR
    if xlsx_dir.exists():
        extracted = list(xlsx_dir.glob("extracted_*/*.xlsx")) + list(xlsx_dir.glob("extracted_*/*.xls"))
        print(f"  Total extracted Excel files: {len(extracted)}")

    pdf_dir = PDF_DIR
    if pdf_dir.exists():
        pdfs = list(pdf_dir.rglob("*.pdf"))
        print(f"  Total archived PDFs: {len(pdfs)}")


if __name__ == "__main__":
    main()
