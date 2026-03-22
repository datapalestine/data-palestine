# Data Palestine — Data Sources Reference

This document catalogs every data source to integrate, with technical details for building scrapers and pipelines.

---

## Tier 1: Primary Sources (Phase 1)

### 1. Palestinian Central Bureau of Statistics (PCBS)

- **Website:** https://www.pcbs.gov.ps/default.aspx (English) / https://www.pcbs.gov.ps/defaultAr.aspx (Arabic)
- **Data format:** HTML tables, PDF reports, some Excel files
- **API:** None — requires scraping
- **Language:** Bilingual (Arabic primary, English available for most content)
- **License:** Creative Commons (per PCBS open data policy)
- **Update frequency:** Varies by dataset (monthly CPI, quarterly labor, annual census)

**Key data pages to scrape:**

| Dataset | URL Pattern | Format | Frequency |
|---------|-------------|--------|-----------|
| Population statistics | pcbs.gov.ps/site/lang__en/507/default.aspx → Demographics section | HTML + PDF | Annual |
| Labor Force Survey | pcbs.gov.ps press releases with "Labour Force" | PDF + HTML tables | Quarterly |
| Consumer Price Index | pcbs.gov.ps → Indices section | HTML tables | Monthly |
| National Accounts (GDP) | pcbs.gov.ps → Statistics → National Accounts | PDF + Excel | Annual/Quarterly |
| Foreign Trade | pcbs.gov.ps → Statistics → Foreign Trade | HTML + PDF | Monthly |
| Building Licenses | pcbs.gov.ps press releases | HTML | Quarterly |
| Industrial Production Index | pcbs.gov.ps → Indices section | HTML | Monthly |
| Education statistics | pcbs.gov.ps → Statistics → Education | PDF + Excel | Annual |
| Health statistics | pcbs.gov.ps → Statistics → Health | PDF | Annual |
| Census 2017 | pcbs.gov.ps/census2017/ | Various | One-time |

**Scraping notes:**
- The site uses ASP.NET with ViewState — scrapers need to handle form submissions
- Press releases contain embedded data tables in HTML
- PDF reports have Arabic text — need OCR-capable extraction for scanned PDFs
- The site's statistical catalog is at: pcbs.gov.ps/Stat-Data-Catalogue/default
- RSS/news feed available at the press release page for monitoring new publications

**Also check:** PCBS open data portal at http://www.opendata.ps/ (CKAN-based, currently unreliable)


### 2. World Bank — West Bank and Gaza

- **Data portal:** https://data.worldbank.org/country/west-bank-and-gaza
- **API:** https://api.worldbank.org/v2/country/PSE/indicator/{indicator_code}?format=json
- **Format:** JSON API (well-structured), CSV, Excel
- **License:** Creative Commons Attribution 4.0
- **Update frequency:** Varies (annual for most indicators)

**Key indicators (API codes):**

| Indicator | API Code | Description |
|-----------|----------|-------------|
| GDP (current USD) | NY.GDP.MKTP.CD | Gross Domestic Product |
| GDP per capita | NY.GDP.PCAP.CD | GDP per capita, current USD |
| GDP growth | NY.GDP.MKTP.KD.ZG | Annual GDP growth rate |
| Population | SP.POP.TOTL | Total population |
| Poverty rate | SI.POV.NAHC | National poverty headcount ratio |
| Unemployment | SL.UEM.TOTL.ZS | Unemployment rate (ILO modeled) |
| Life expectancy | SP.DYN.LE00.IN | Life expectancy at birth |
| Infant mortality | SP.DYN.IMRT.IN | Infant mortality rate |
| Literacy rate | SE.ADT.LITR.ZS | Adult literacy rate |
| School enrollment | SE.PRM.NENR | Net enrollment rate, primary |
| Access to electricity | EG.ELC.ACCS.ZS | % of population |
| Internet users | IT.NET.USER.ZS | % of population |

**API usage:**
```
GET https://api.worldbank.org/v2/country/PSE/indicator/NY.GDP.MKTP.CD?format=json&per_page=100&date=2000:2025
```

Response is paginated JSON. Country code for Palestine is `PSE`. Some indicators may be listed under `WBG` (West Bank and Gaza) instead.


### 3. B'Tselem Statistics

- **Website:** https://www.btselem.org/statistics
- **Interactive DB:** https://statistics.btselem.org/en/all-fatalities/by-date-of-incident
- **Format:** Interactive web database with filtering + downloadable results
- **License:** Not explicitly stated — contact for data sharing agreement
- **Update frequency:** Ongoing documentation

**Available datasets:**
- Fatalities database (2000-present): Palestinians and Israelis killed, with details on circumstances, participation in hostilities, age, gender
- Demolitions database: Palestinian structures demolished by Israeli authorities
- Detainee statistics: Palestinians held in Israeli custody
- Settler violence incidents

**Scraping notes:**
- The interactive database at statistics.btselem.org uses client-side rendering
- Best approach: check if they offer CSV export or API, contact directly for data access
- Alternatively, the database filtering generates URLs that can be programmatically queried
- Handle with extra care — this is sensitive human rights documentation data


---

## Tier 2: Secondary Sources (Phase 2)

### 4. OCHA oPt (Humanitarian Data)

- **Website:** https://www.ochaopt.org/data
- **HDX portal:** https://data.humdata.org/organization/ocha-occupied-palestinian-territory-opt
- **Format:** CSV, Excel, GeoJSON, API (HDX HAPI)
- **License:** Various — mostly open
- **Update frequency:** Weekly situation reports, various dataset updates

**Key datasets on HDX (31+ datasets):**
- Administrative boundaries (COD-AB) — GeoJSON/Shapefile
- Demolitions and displacement data
- Multi-Sector Needs Assessment (MSNA)
- Road network data
- Humanitarian funding flows (FTS)
- Flood-affected households
- Population statistics by admin level

**HDX API (HAPI):**
```
GET https://hapi.humdata.org/api/v1/metadata/dataset?location_code=PSE&output_format=json
```

**OCHA mapping tools (ochaopt.org/data):**
- Gaza crossings monitor
- West Bank demolition database
- Vulnerability Profile (Area C)
- Settlement monitoring
- Electricity tracking (Gaza)

### 5. UNRWA

- **Website:** https://www.unrwa.org/
- **Data:** Annual reports, statistics on registered refugees
- **Format:** PDF reports, some interactive dashboards
- **Key data:** Refugee population by field (Jordan, Lebanon, Syria, West Bank, Gaza), education enrollment, health clinic visits

### 6. WHO — Palestine Health Data

- **Global Health Observatory:** https://www.who.int/countries/pse
- **Format:** API + CSV
- **Key indicators:** Disease burden, health workforce, immunization coverage, maternal/child health

### 7. UNESCO — Education Data

- **UIS portal:** http://data.uis.unesco.org/
- **API available:** Yes
- **Key indicators:** Enrollment rates, completion rates, literacy, education spending, teacher ratios

### 8. Tech for Palestine

- **Website:** https://data.techforpalestine.org/
- **GitHub:** https://github.com/TechForPalestine/palestine-datasets
- **Format:** JSON, API, npm package
- **Focus:** Post-Oct 7 conflict data — casualty lists with names, ages; daily summary updates
- **Relationship:** Potential collaboration partner. Their data is narrowly focused on conflict documentation; Data Palestine is broader.


---

## Tier 3: Supplementary Sources (Phase 3)

### 9. Gisha — Movement & Access
- **Website:** https://gisha.org/
- **Data:** Gaza crossings data, movement restrictions, import/export tracking

### 10. Peace Now — Settlement Data
- **Website:** https://peacenow.org.il/en/settlements-watch
- **Data:** Settlement construction, outpost tracking, land takeover

### 11. Palestinian Water Authority
- **Website:** https://www.pwa.ps/
- **Data:** Water access, consumption, quality metrics

### 12. Palestine Monetary Authority
- **Website:** https://www.pma.ps/
- **Data:** Banking statistics, monetary indicators, financial stability reports

### 13. Palestinian Ministry of Health
- **Data:** Hospital capacity, disease surveillance, mortality/morbidity statistics
- **Note:** Current data from Gaza MoH is frequently cited in media for casualty figures

### 14. FRED (Federal Reserve Economic Data)
- **URL:** https://fred.stlouisfed.org/series/NYGDPPCAPKDPSE
- **Format:** API (well-documented)
- **Data:** Select economic indicators mirrored from World Bank

### 15. IDMC (Internal Displacement Monitoring Centre)
- **Website:** https://www.internal-displacement.org/countries/palestine
- **Data:** Internal displacement figures, conflict vs. disaster displacement


---

## Pipeline Priority Order

**Month 1-2 (Phase 1 launch):**
1. World Bank API → Economic indicators (easiest — clean API)
2. PCBS → Population demographics (HTML scraping)
3. PCBS → CPI and economic indices (HTML scraping)

**Month 3-4:**
4. PCBS → Labor Force Survey (PDF + HTML)
5. B'Tselem → Casualty and demolition data
6. PCBS → Education statistics

**Month 5-6:**
7. HDX/OCHA → Humanitarian datasets
8. WHO → Health indicators
9. UNESCO → Education indicators
10. PCBS → Foreign trade data

**Phase 2 (Month 7+):**
11. UNRWA refugee data
12. Tech for Palestine integration
13. Gisha movement data
14. PMA financial data
15. Settlement and demolition data expansion
