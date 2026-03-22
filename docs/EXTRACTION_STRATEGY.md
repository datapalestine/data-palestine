# Data Palestine — PCBS Data Extraction Strategy

## What I Found (March 2026 Site Audit)

After crawling the live PCBS site, here's the reality: **it's much better than expected**. PCBS data lives in 5 distinct formats, each requiring a different extraction approach. Critically, many tables already have CSV download links — you don't need to scrape them.

---

## The 5 Data Layers (ordered by extraction difficulty)

### Layer 1: CSV/Excel Downloads (EASIEST — Start Here)
**Effort: Low | Reliability: High | Coverage: ~40% of structured data**

PCBS statistical tables at `statisticsIndicatorsTables.aspx?table_id=X` often include a direct CSV download link. Example found on the Balance of Payments page:

```
https://www.pcbs.gov.ps/papers/statisticsIndicatorsTables_uploads/en2025-12-28-9-1-35-Copy of Tables -2024 Report -E.csv
```

**Strategy:**
1. Crawl the Statistics A-Z directory at `/site/lang__en/507/default.aspx` to collect all category links
2. Follow each category link to find `statisticsIndicatorsTables.aspx?table_id=X` URLs
3. For each table page, scan for CSV/XLSX download links (pattern: `papers/statisticsIndicatorsTables_uploads/`)
4. Download the files directly — these are already clean structured data
5. Parse with pandas, map to your schema, load

**URL Patterns discovered:**
```
# Statistical table page
https://www.pcbs.gov.ps/statisticsIndicatorsTables.aspx?lang=en&table_id={TABLE_ID}

# CSV download (embedded in table pages)
https://www.pcbs.gov.ps/papers/statisticsIndicatorsTables_uploads/en{TIMESTAMP}-{FILENAME}.csv

# Bilingual: same table in Arabic
https://www.pcbs.gov.ps/statisticsIndicatorsTables.aspx?lang=ar&table_id={TABLE_ID}
```

**Known table_ids from the site (sample):**
- 4373: Balance of Payments 2024
- 4383: Financial Account 2024
- 4410: Quarterly Balance of Payments (6th edition time series)
- 4390: Quarterly Balance of Payments (5th edition time series)
- 4391: Annual Balance of Payments (5th edition time series)
- 4388: Annual Balance of Payments (6th edition time series)

The table_id appears to be sequential. A systematic crawl of IDs 1-5000 would map the entire database.

**Pipeline code pattern:**
```python
import httpx
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO

async def discover_csv_links(table_id: int) -> dict:
    """Check a PCBS table page for downloadable CSV/XLSX links."""
    url = f"https://www.pcbs.gov.ps/statisticsIndicatorsTables.aspx?lang=en&table_id={table_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return {"table_id": table_id, "csv": None, "xlsx": None, "html_table": False}

        soup = BeautifulSoup(resp.text, "html.parser")

        # Find CSV download link
        csv_link = None
        for a in soup.find_all("a", href=True):
            if ".csv" in a["href"].lower():
                csv_link = a["href"]
                if not csv_link.startswith("http"):
                    csv_link = f"https://www.pcbs.gov.ps{csv_link}"
                break

        # Find XLSX download link
        xlsx_link = None
        for a in soup.find_all("a", href=True):
            if ".xlsx" in a["href"].lower() or ".xls" in a["href"].lower():
                xlsx_link = a["href"]
                if not xlsx_link.startswith("http"):
                    xlsx_link = f"https://www.pcbs.gov.ps{xlsx_link}"
                break

        # Check for HTML table
        tables = soup.find_all("table", class_=lambda c: c and ("Grid" in c or "Data" in c or "table" in c.lower()))
        has_table = len(tables) > 0

        # Get table title
        title = soup.find("title")
        title_text = title.text.strip() if title else ""

        return {
            "table_id": table_id,
            "title": title_text,
            "csv": csv_link,
            "xlsx": xlsx_link,
            "html_table": has_table,
            "url": url,
        }

async def download_and_parse_csv(csv_url: str) -> pd.DataFrame:
    """Download a PCBS CSV file and parse it."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(csv_url)
        resp.raise_for_status()

        # PCBS CSVs may have BOM or encoding issues
        content = resp.content.decode("utf-8-sig", errors="replace")

        # Some CSVs have metadata rows at the top — skip until we find the header
        lines = content.strip().split("\n")
        header_idx = 0
        for i, line in enumerate(lines):
            # Heuristic: header row has multiple comma-separated non-empty values
            parts = [p.strip() for p in line.split(",") if p.strip()]
            if len(parts) >= 2 and not line.startswith("#"):
                header_idx = i
                break

        cleaned = "\n".join(lines[header_idx:])
        df = pd.read_csv(StringIO(cleaned))
        return df
```

### Layer 2: Statistical Data Catalogue (MODERATE)
**Effort: Low-Medium | Reliability: High | Coverage: ~30% (historical)**

The catalogue at `/Stat-Data-Catalogue/default` has **45 categories** and each offers downloads in PDF, Word (.doc), and Excel (.xls/.xlsx). This is the richest historical archive.

**Categories found (all of these are downloadable):**
Agriculture, Census, Child Statistics, Constructions, Crime & Victimization, Population & Demographic, Education/Culture/Media, Energy, Environment, Establishments, Living Standards, Housing, Industry, Technology, Labour, Localities, Prices, Services, Tourism, Trade, Transport & Communication, Water, Weather, Yearbooks, Satellite Accounts, Governance, National Accounts, Settlements, Israeli Measures, Health, Finance & Insurance, Balance of Payments, Economic Surveys, Gender Statistics, Foreign Investment, Household Violence, Statistical Atlas, Olive Press, Socio-Economic Conditions, Disability Statistics

**Strategy:**
1. The catalogue uses AJAX lazy-loading — each accordion loads content dynamically
2. Intercept the AJAX calls to get the list of publications per category
3. Each publication has PDF/DOC/XLS download links with patterns:
   - PDF: `https://www.pcbs.gov.ps/Downloads/book{N}.pdf`
   - Excel: `https://www.pcbs.gov.ps/Downloads/ZIP/{N}-x.zip`
   - Word: `https://www.pcbs.gov.ps/Downloads/ZIP/{N}-w.zip`
4. Download all Excel files first (easiest to parse), PDF as backup
5. Excel files from here are the golden source for historical time-series data

**Pipeline approach:**
```python
async def crawl_catalogue_category(category_slug: str) -> list[dict]:
    """Crawl a single category from the PCBS Statistical Data Catalogue.

    The catalogue uses AJAX — need to figure out the API endpoint
    by inspecting network requests. Likely something like:
    /Stat-Data-Catalogue/api/category/{id}/publications
    """
    # TODO: Inspect AJAX calls in browser DevTools to find the API
    # The catalogue sections load dynamically via JavaScript
    pass

async def download_catalogue_excel(zip_url: str, output_dir: str) -> str:
    """Download and extract an Excel file from the catalogue ZIP."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(zip_url)
        resp.raise_for_status()

        import zipfile, io, os
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            for name in zf.namelist():
                if name.endswith((".xls", ".xlsx")):
                    extracted = os.path.join(output_dir, name)
                    with open(extracted, "wb") as f:
                        f.write(zf.read(name))
                    return extracted
    return ""
```


### Layer 3: HTML Tables in Press Releases (MODERATE)
**Effort: Medium | Reliability: Medium | Coverage: ~20% (recent data)**

Press releases are how PCBS publishes the most current data (monthly CPI, quarterly labor, etc.). They contain inline HTML tables. Example from the CPI February 2026 press release:

```
URL: /site/512/default.aspx?tabID=512&lang=en&ItemID=6179&mid=3171&wversion=Staging
```

The data is in standard `<table>` HTML. The CPI release contained a table with sub-groups and percent changes.

**Key insight:** The English press releases are abbreviated ("Please note that the press release in English is brief compared to the Arabic version"). The **Arabic versions have more detailed tables**. You'll want to scrape both.

**Strategy:**
1. Crawl the press release index at `/pcbs_2012/PressEn.aspx` and `/pcbs_2012/PressAr.aspx`
2. Build a mapping of press release types by keyword in title:
   - "Consumer Price Index" → CPI pipeline
   - "Labour Force" / "Labor Force" → Employment pipeline
   - "Industrial Production" → IPI pipeline
   - "Building Licenses" → Construction pipeline
   - "External Trade" → Trade pipeline
   - "Producer Price" → PPI pipeline
3. For each press release, extract HTML tables using BeautifulSoup
4. Parse the semi-structured text around the tables for additional data points

**Pipeline code pattern:**
```python
import re

async def extract_press_release_data(item_id: int, lang: str = "en") -> dict:
    """Extract structured data from a PCBS press release."""
    mid = "3171" if lang == "en" else "3915"
    url = f"https://www.pcbs.gov.ps/site/512/default.aspx?tabID=512&lang={lang}&ItemID={item_id}&mid={mid}&wversion=Staging"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

    # Extract title
    title_el = soup.select_one("h1, .ArticleTitle, #ctl00_ContentPlaceHolder1_lblTitle")
    title = title_el.text.strip() if title_el else ""

    # Extract publication date
    date_text = ""
    for el in soup.find_all(string=re.compile(r"\d{1,2}-\d{1,2}-\d{4}")):
        date_text = el.strip()
        break

    # Extract all tables
    tables = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells and any(c for c in cells):
                rows.append(cells)
        if len(rows) >= 2:  # At least header + 1 data row
            tables.append(rows)

    # Extract inline statistics from text (e.g., "recorded an increase by 12.02%")
    text = soup.get_text()
    inline_stats = re.findall(
        r'([\w\s]+?)\s+(?:recorded|reached|was|is)\s+(?:an?\s+)?(?:increase|decrease|change)?\s*(?:of|by)?\s*([\d,.]+%?)',
        text, re.IGNORECASE
    )

    return {
        "item_id": item_id,
        "title": title,
        "date": date_text,
        "tables": tables,
        "inline_stats": inline_stats,
        "url": url,
        "lang": lang,
    }

async def discover_all_press_releases(lang: str = "en") -> list[dict]:
    """Crawl the press release index to find all available releases."""
    page_url = f"https://www.pcbs.gov.ps/pcbs_2012/Press{'En' if lang == 'en' else 'Ar'}.aspx"
    # This page may use ASP.NET postbacks for pagination
    # Strategy: incrementally try ItemIDs from 1 to ~7000
    # Or: scrape the index page which lists them
    pass
```


### Layer 4: PDF Reports (HARD)
**Effort: High | Reliability: Medium | Coverage: ~20% (deep analysis)**

Full publications (yearbooks, survey reports, analytical papers) are published as PDFs. These contain the richest, most detailed data but are the hardest to extract.

**Types of PDFs:**

| Type | Example | Extraction Method |
|------|---------|-------------------|
| Text PDFs with tables | Most recent reports | `camelot` (lattice or stream mode) |
| Text PDFs with inline data | Analytical reports | Regex parsing of extracted text |
| Scanned PDFs (Arabic) | Older publications | OCR with `tesseract` + Arabic model |
| Mixed text/image PDFs | Some reports | Combination of camelot + OCR |

**Strategy:**
1. Download all available PDFs from the catalogue (Layer 2 gives you the ZIP links)
2. Classify each PDF: text-based vs scanned (check if `pdftotext` produces output)
3. For text-based PDFs with tables: use `camelot` with lattice mode first, fall back to stream
4. For scanned PDFs: convert to images with `pdf2image`, OCR with tesseract Arabic model
5. For all: store the raw extracted data alongside the parsed structured data for human review

**Pipeline code pattern:**
```python
import subprocess
import tempfile
import os

def classify_pdf(pdf_path: str) -> str:
    """Determine if a PDF is text-based or scanned."""
    result = subprocess.run(
        ["pdftotext", pdf_path, "-"],
        capture_output=True, text=True, timeout=30
    )
    text = result.stdout.strip()
    if len(text) > 100:
        return "text"
    else:
        return "scanned"

def extract_tables_from_text_pdf(pdf_path: str) -> list:
    """Extract tables from a text-based PDF using camelot."""
    try:
        import camelot
        # Try lattice mode first (works for tables with borders)
        tables = camelot.read_pdf(pdf_path, pages="all", flavor="lattice")
        if len(tables) == 0:
            # Fall back to stream mode (borderless tables)
            tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream")
        return [{"page": t.page, "data": t.df.to_dict("records"), "accuracy": t.accuracy} for t in tables]
    except Exception as e:
        return [{"error": str(e)}]

def extract_tables_from_scanned_pdf(pdf_path: str) -> list:
    """OCR a scanned PDF and extract text."""
    from pdf2image import convert_from_path
    import pytesseract

    images = convert_from_path(pdf_path, dpi=300)
    results = []
    for i, img in enumerate(images):
        # OCR with both Arabic and English
        text = pytesseract.image_to_string(img, lang="ara+eng")
        results.append({"page": i + 1, "text": text})
    return results

def extract_pdf_data(pdf_path: str) -> dict:
    """Main PDF extraction dispatcher."""
    pdf_type = classify_pdf(pdf_path)

    if pdf_type == "text":
        tables = extract_tables_from_text_pdf(pdf_path)
        # Also extract full text for inline statistics
        result = subprocess.run(
            ["pdftotext", pdf_path, "-"],
            capture_output=True, text=True, timeout=30
        )
        return {
            "type": "text",
            "tables": tables,
            "full_text": result.stdout,
            "path": pdf_path,
        }
    else:
        pages = extract_tables_from_scanned_pdf(pdf_path)
        return {
            "type": "scanned",
            "pages": pages,
            "path": pdf_path,
        }
```

### Layer 5: Legacy HTML Pages (MODERATE)
**Effort: Medium | Reliability: Low-Medium | Coverage: ~10% (historical)**

Some older time-series data exists as standalone HTML pages. Example found:
```
https://www.pcbs.gov.ps/Portals/_Rainbow/Documents/e-BOP-time-2012.htm
```

These are simple HTML tables that can be scraped directly with BeautifulSoup + pandas `read_html`.

```python
async def extract_legacy_html_table(url: str) -> pd.DataFrame:
    """Extract data from legacy PCBS HTML table pages."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        # These pages may use windows-1256 or ISO-8859-6 encoding for Arabic
        content = resp.content.decode("utf-8", errors="replace")

    dfs = pd.read_html(StringIO(content))
    if dfs:
        return dfs[0]  # Usually the main data table is the first one
    return pd.DataFrame()
```


---

## Recommended Execution Order

### Week 1-2: Low-Hanging Fruit (get data flowing immediately)

1. **World Bank API** — Already clean JSON API. 20+ indicators. Takes 1 day to build pipeline.
2. **PCBS CSV downloads** — Crawl all `statisticsIndicatorsTables.aspx` pages, download every CSV link found. Probably 100+ tables. Takes 2-3 days.
3. **PCBS Catalogue Excel files** — Download all Excel ZIPs from the catalogue. Parse with pandas/openpyxl. Takes 2-3 days.

By end of week 2, you should have **hundreds of data tables** in your database.

### Week 3-4: Structured Scraping

4. **Press release HTML tables** — Build scrapers for the 6-7 recurring press release types (CPI, LFS, IPI, PPI, building licenses, trade, population). Takes 3-4 days.
5. **PCBS Indicators page** — Scrape the indicators directory at `/site/lang__en/611/default.aspx`. Takes 1 day.
6. **B'Tselem interactive database** — Check if they offer data export or API access. If not, scrape the filtering interface. Takes 2 days.

### Month 2: Hard Stuff

7. **PDF extraction** — Process the most important PDF reports (yearbooks, survey results). Start with text-based PDFs. Takes 1-2 weeks depending on volume.
8. **HDX/OCHA datasets** — Download from Humanitarian Data Exchange API. Mix of CSV and GeoJSON. Takes 2-3 days.
9. **Scanned PDF OCR** — Only do this for high-value historical documents. Takes ongoing effort.

### Ongoing: Monitoring Pipeline

10. **New data detection** — Daily cron that checks `/post.aspx?showAll=showAll` for new press releases. When found, trigger the appropriate pipeline.


---

## Critical Technical Notes

### PCBS Site Quirks

- **ASP.NET ViewState**: Many pages use ASP.NET Web Forms. Form submissions require `__VIEWSTATE`, `__VIEWSTATEGENERATOR`, and `__EVENTVALIDATION` hidden fields. Scrapers must capture and send these.
- **Encoding**: Arabic content uses various encodings. Always try `utf-8-sig` first, then `windows-1256`, then `iso-8859-6`.
- **Rate limiting**: Be respectful. Add 1-2 second delays between requests. PCBS is a small institution; don't hammer their server.
- **Bilingual pages**: Most pages have both English (`lang=en`) and Arabic (`lang=ar`) versions. The Arabic versions often have MORE data. Scrape both.
- **English press releases are abbreviated**: PCBS explicitly states "the press release in English is brief compared to the Arabic version." The Arabic version should be treated as the primary source.

### Data Quality Checks

Every piece of data extracted from PCBS should be validated:

```python
def validate_observation(value: float, indicator_code: str, year: int) -> list[str]:
    """Run basic validation checks on an extracted data point."""
    errors = []

    # Range checks by indicator type
    if "RATE" in indicator_code or "PERCENT" in indicator_code:
        if value < -100 or value > 1000:
            errors.append(f"Percentage value {value} out of expected range")

    if "POPULATION" in indicator_code:
        if value < 0 or value > 20_000_000:
            errors.append(f"Population value {value} out of expected range")

    if "GDP" in indicator_code and "GROWTH" not in indicator_code:
        if value < 0:
            errors.append(f"GDP value {value} is negative")

    # Year sanity check
    if year < 1948 or year > 2027:
        errors.append(f"Year {year} is out of expected range")

    return errors
```

### Source Provenance

For every extracted data point, store:
```python
@dataclass
class ExtractionProvenance:
    source_url: str                # The page URL scraped
    source_type: str               # "csv_download", "html_table", "pdf_extraction", "api"
    extraction_date: datetime      # When you ran the pipeline
    original_file_hash: str        # SHA-256 of the downloaded file
    original_file_archived: str    # Path to your archived copy
    table_number: int | None       # Which table on the page (if multiple)
    row_number: int | None         # Row in the source table
    notes: str                     # Any extraction caveats
```


---

## What NOT to Scrape (Use APIs Instead)

| Source | API Available | Use This Instead of Scraping |
|--------|--------------|------------------------------|
| World Bank | Yes — REST API | `api.worldbank.org/v2/country/PSE/indicator/{code}?format=json` |
| HDX | Yes — HAPI API | `hapi.humdata.org/api/v1/` |
| WHO | Yes — GHO API | `ghoapi.azureedge.net/api/` |
| UNESCO UIS | Yes — API | `api.uis.unesco.org/` |
| FRED | Yes — API | `api.stlouisfed.org/fred/series/observations` |

Always prefer an API over scraping. It's more reliable, faster, and less likely to break.


---

## Estimated Data Volume After Phase 1

| Source | Tables/Datasets | Observations (est.) | Method |
|--------|-----------------|---------------------|--------|
| PCBS CSV downloads | ~100-200 tables | ~50,000-100,000 | Direct download |
| PCBS Catalogue Excel | ~300-500 files | ~200,000-500,000 | Download + parse |
| World Bank API | ~50 indicators | ~2,000-3,000 | API |
| PCBS Press Releases | ~50 recent releases | ~5,000-10,000 | HTML scraping |
| B'Tselem | ~5 datasets | ~20,000-50,000 | TBD (scrape or request) |
| **Total Phase 1** | **~500-800 tables** | **~300,000-700,000** | |

This is more than enough data to launch a credible platform.
