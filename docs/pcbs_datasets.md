# PCBS Scraping Reference

## Site Architecture

PCBS uses ASP.NET Web Forms. Key patterns:

- Base URL: `https://www.pcbs.gov.ps/`
- English pages: `/site/lang__en/{page_id}/default.aspx`
- Arabic pages: `/site/lang__ar/{page_id}/default.aspx`
- Press releases (EN): `/pcbs_2012/PressEn.aspx`
- Press releases (AR): `/pcbs_2012/PressAr.aspx`
- Publications: `/pcbs_2012/Publications.aspx`
- Statistical catalog: `/Stat-Data-Catalogue/default`
- Indices page: `/site/lang__en/1095/default.aspx`

## Key Page IDs

| Page ID | Section |
|---------|---------|
| 507 | Statistics main page |
| 1095 | Indices (CPI, IPI, etc.) |
| 611 | Statistical indicators |
| 612 | Glossary |
| 616 | Media room |
| 538 | About / Mission |

## Data Extraction Patterns

### HTML Tables in Press Releases

Most recent data is published as press releases with embedded HTML tables.

Pattern:
```
https://www.pcbs.gov.ps/site/512/default.aspx?tabID=512&lang=en&ItemID={item_id}&mid=3171&wversion=Staging
```

Tables are rendered as standard `<table>` elements. Extract using BeautifulSoup:

```python
import httpx
from bs4 import BeautifulSoup

async def scrape_press_release(item_id: int) -> dict:
    url = f"https://www.pcbs.gov.ps/site/512/default.aspx?tabID=512&lang=en&ItemID={item_id}&mid=3171&wversion=Staging"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Title
        title = soup.select_one(".ArticleTitle, h1")

        # Data tables
        tables = soup.select("table.TableData, table.GridTable, table")

        # Publication date
        date_el = soup.select_one(".ArticleDate, .date")

        return {
            "title": title.text.strip() if title else "",
            "tables": tables,
            "date": date_el.text.strip() if date_el else "",
        }
```

### Index Pages (CPI, IPI)

The indices page at `/site/lang__en/1095/default.aspx` contains links to:
- Consumer Price Index (CPI) — monthly
- Industrial Production Index (IPI) — monthly
- Wholesale Price Index — quarterly
- Construction Cost Index — monthly/quarterly

These are published as press releases with the data in tables and explanatory text.

### Statistical Catalog

The catalog at `/Stat-Data-Catalogue/default` provides structured access to datasets. It may offer Excel/CSV downloads directly. Check for download links with patterns:
- `.xlsx` files
- `.csv` files
- Links containing "download" or "excel"

### PDF Reports

Many datasets are published as PDF reports in the Publications section. These need PDF extraction:

```python
import camelot  # For table extraction from PDFs

def extract_tables_from_pdf(pdf_path: str) -> list:
    tables = camelot.read_pdf(pdf_path, pages="all", flavor="lattice")
    if len(tables) == 0:
        # Try stream mode for borderless tables
        tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream")
    return [t.df for t in tables]
```

For Arabic PDFs that are scanned images, use:
```python
import pytesseract
from pdf2image import convert_from_path

def ocr_arabic_pdf(pdf_path: str) -> str:
    images = convert_from_path(pdf_path)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img, lang="ara+eng")
    return text
```

## Recent Press Release Item IDs (as of March 2026)

| ItemID | Title | Data Type |
|--------|-------|-----------|
| 6183 | World Water Day 2026 | Water statistics |
| 6179 | CPI February 2026 | Consumer prices |
| 6177 | Building Licenses Q4 2025 | Construction |
| 6176 | Women's Day statistics | Gender data |
| 6172 | IPI January 2026 | Industrial production |
| 6175 | Women's situation 2026 | Demographics/gender |

## Monitoring for New Data

To detect new publications:
1. Scrape the press releases page periodically (daily)
2. Check for new ItemIDs in the news listing
3. Parse the title to determine which dataset it belongs to
4. Trigger the appropriate pipeline

The news listing is at:
- English: `https://www.pcbs.gov.ps/post.aspx?showAll=showAll`
- Arabic: `https://www.pcbs.gov.ps/postar.aspx?showAll=showAll`

## Population Data (Census)

The most recent census was 2017: `https://www.pcbs.gov.ps/census2017/`

Population estimates are published annually with breakdowns by:
- Territory (West Bank / Gaza)
- Governorate
- Gender
- Age group (5-year bands)
- Urban/rural/camp

The opendata.ps portal (when accessible) has census data in structured format:
`http://www.opendata.ps/` — look for "Palestinian population census" datasets.
