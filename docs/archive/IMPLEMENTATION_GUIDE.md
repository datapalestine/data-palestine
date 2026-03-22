# Data Palestine — Implementation Guide for Claude Code

## How to Use This Guide

This document contains step-by-step implementation instructions. Work through each step sequentially. Each step includes exactly what to create and what the expected result should be.

**Important:** The `CLAUDE.md` file in the project root contains the full project context, design principles, and technical decisions. Read it before starting any work.

The bootstrap files in this directory should be placed as follows:
- `CLAUDE.md` → project root (`/CLAUDE.md`)
- `schema.sql` → `packages/db/schema.sql`
- `docker-compose.yml` → project root (`/docker-compose.yml`)
- `.env.example` → project root (`/.env.example`)
- `ci.yml` → `.github/workflows/ci.yml`
- `messages-en.json` → `apps/web/messages/en.json`
- `messages-ar.json` → `apps/web/messages/ar.json`

---

## STEP 1: Initialize Monorepo Structure

Create the full directory structure:

```
data-palestine/
├── .github/
│   └── workflows/
│       └── ci.yml
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py         # FastAPI app entry point
│   │   │   ├── config.py       # Settings via pydantic-settings
│   │   │   ├── database.py     # SQLAlchemy async engine + session
│   │   │   ├── models/         # SQLAlchemy ORM models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── geography.py
│   │   │   │   ├── source.py
│   │   │   │   ├── dataset.py
│   │   │   │   ├── indicator.py
│   │   │   │   └── observation.py
│   │   │   ├── schemas/        # Pydantic request/response schemas
│   │   │   │   ├── __init__.py
│   │   │   │   ├── geography.py
│   │   │   │   ├── source.py
│   │   │   │   ├── dataset.py
│   │   │   │   ├── indicator.py
│   │   │   │   ├── observation.py
│   │   │   │   └── common.py   # Pagination, error responses, etc.
│   │   │   ├── routers/        # API route handlers
│   │   │   │   ├── __init__.py
│   │   │   │   ├── datasets.py
│   │   │   │   ├── indicators.py
│   │   │   │   ├── observations.py
│   │   │   │   ├── geographies.py
│   │   │   │   ├── sources.py
│   │   │   │   ├── search.py
│   │   │   │   └── export.py
│   │   │   ├── services/       # Business logic
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dataset_service.py
│   │   │   │   ├── indicator_service.py
│   │   │   │   └── search_service.py
│   │   │   └── utils/
│   │   │       ├── __init__.py
│   │   │       └── pagination.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py     # Fixtures: test DB, client, seed data
│   │   │   ├── test_datasets.py
│   │   │   ├── test_indicators.py
│   │   │   └── test_observations.py
│   │   ├── alembic/
│   │   │   ├── alembic.ini
│   │   │   └── versions/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   └── web/                    # Next.js frontend
│       ├── app/
│       │   └── [locale]/       # i18n routing
│       │       ├── layout.tsx
│       │       ├── page.tsx            # Homepage
│       │       ├── explore/
│       │       │   └── page.tsx        # Data Explorer
│       │       ├── datasets/
│       │       │   ├── page.tsx        # Data Catalog
│       │       │   └── [slug]/
│       │       │       └── page.tsx    # Dataset Detail
│       │       ├── indicators/
│       │       │   └── [id]/
│       │       │       └── page.tsx    # Indicator Detail
│       │       ├── methodology/
│       │       │   └── page.tsx
│       │       ├── about/
│       │       │   └── page.tsx
│       │       └── developers/
│       │           └── page.tsx        # API Docs
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Header.tsx
│       │   │   ├── Footer.tsx
│       │   │   ├── Navigation.tsx
│       │   │   └── LanguageSwitcher.tsx
│       │   ├── data/
│       │   │   ├── KeyIndicatorCard.tsx
│       │   │   ├── DatasetCard.tsx
│       │   │   ├── IndicatorChart.tsx  # D3 time-series
│       │   │   ├── DataTable.tsx
│       │   │   ├── ExportButton.tsx
│       │   │   └── SearchBar.tsx
│       │   ├── maps/
│       │   │   └── PalestineMap.tsx    # Mapbox GL
│       │   └── ui/                     # Shared UI primitives
│       │       ├── Button.tsx
│       │       ├── Card.tsx
│       │       ├── Select.tsx
│       │       ├── Skeleton.tsx
│       │       └── Badge.tsx
│       ├── lib/
│       │   ├── api-client.ts       # Typed API client
│       │   ├── formatters.ts       # Number/date formatting
│       │   └── constants.ts        # Geography codes, category slugs
│       ├── messages/
│       │   ├── en.json
│       │   └── ar.json
│       ├── i18n.ts
│       ├── middleware.ts           # i18n locale detection
│       ├── next.config.ts
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       ├── package.json
│       └── Dockerfile
│
├── packages/
│   ├── db/
│   │   └── schema.sql
│   └── pipeline/
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── base.py             # BasePipeline abstract class
│       │   ├── models.py           # Shared Pydantic models for pipeline I/O
│       │   └── sources/
│       │       ├── __init__.py
│       │       ├── pcbs_population.py
│       │       ├── pcbs_economy.py
│       │       ├── pcbs_labor.py
│       │       ├── btselem_casualties.py
│       │       └── worldbank.py
│       ├── tests/
│       │   ├── __init__.py
│       │   ├── fixtures/           # Sample HTML/PDF/Excel for testing
│       │   └── test_pcbs_population.py
│       └── pyproject.toml
│
├── docs/
│   ├── methodology.md
│   ├── api-guide.md
│   └── contributing.md
│
├── scripts/
│   └── seed_db.py                  # Load seed data into DB
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── LICENSE                         # MIT for code, CC-BY-4.0 for data
├── README.md
└── CLAUDE.md
```

**Verification:** All directories exist. Running `find . -type f -name "*.py" | head -20` shows Python files in the expected locations.

---

## STEP 2: Set Up Python Backend (apps/api)

### pyproject.toml

```toml
[project]
name = "data-palestine-api"
version = "0.1.0"
description = "Data Palestine API — Palestinian Open Data Platform"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29.0",
    "psycopg2-binary>=2.9.9",
    "alembic>=1.13.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "httpx>=0.27.0",
    "redis>=5.0.0",
    "meilisearch-python-sdk>=3.0.0",
    "python-multipart>=0.0.9",
    "openpyxl>=3.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "httpx>=0.27.0",
    "ruff>=0.4.0",
]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### Core Files to Implement

**app/config.py** — Use pydantic-settings to load environment variables. Include all vars from .env.example. Provide sensible defaults for development.

**app/database.py** — Create async SQLAlchemy engine and session factory. Include a `get_db` dependency for FastAPI. Create a sync engine for Alembic.

**app/main.py** — FastAPI application with:
- CORS middleware (allow all origins in dev, configurable in prod)
- Health check endpoint at `/health`
- API router prefix at `/api/v1`
- OpenAPI customization (title: "Data Palestine API", description, version)
- Include all routers from app/routers/
- On startup: verify DB connection, initialize Meilisearch indexes

**app/models/** — SQLAlchemy 2.0 ORM models matching the schema.sql exactly. Use mapped_column syntax. Include relationships.

**app/schemas/** — Pydantic v2 models for API request/response. Every response model should include both `_en` and `_ar` fields. Include a `PaginatedResponse[T]` generic.

**app/routers/** — RESTful route handlers. Each router handles one entity type. Use dependency injection for DB sessions. Return proper HTTP status codes. Include query parameter filtering.

**Verification:** Run `uvicorn app.main:app --reload` and confirm:
- `GET /health` returns `{"status": "ok"}`
- `GET /docs` shows Swagger UI
- `GET /api/v1/datasets` returns `{"data": [], "meta": {...}}`
- `GET /api/v1/geographies` returns seeded geography data

---

## STEP 3: Set Up Next.js Frontend (apps/web)

### Initialize with:
```bash
npx create-next-app@latest web --typescript --tailwind --app --src-dir=false
```

Then configure:

**next.config.ts** — Enable i18n with next-intl plugin. Configure image domains. Set API rewrites for development.

**middleware.ts** — Detect locale from Accept-Language header or cookie. Redirect to `/en/` or `/ar/` as appropriate. Default to Arabic (primary audience).

**i18n.ts** — Configure next-intl with the messages from `messages/en.json` and `messages/ar.json`.

**tailwind.config.ts** — Custom theme:
```typescript
{
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#1B5E20', light: '#2E7D32', dark: '#0D3B10' },
        accent: '#2E7D32',
        secondary: '#C62828',
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'IBM Plex Arabic', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
    },
  },
}
```

**app/[locale]/layout.tsx** — Root layout with:
- HTML dir attribute (`dir="rtl"` for Arabic, `dir="ltr"` for English)
- HTML lang attribute
- Google Fonts: IBM Plex Sans, IBM Plex Arabic, IBM Plex Mono
- Header and Footer components
- next-intl provider

**lib/api-client.ts** — Typed fetch wrapper:
```typescript
class DataPalestineAPI {
  constructor(private baseUrl: string, private locale: string) {}

  async getDatasets(params?: DatasetQueryParams): Promise<PaginatedResponse<Dataset>> { ... }
  async getDataset(slug: string): Promise<Dataset> { ... }
  async getIndicators(params?: IndicatorQueryParams): Promise<PaginatedResponse<Indicator>> { ... }
  async getObservations(indicatorId: number, params?: ObservationQueryParams): Promise<PaginatedResponse<Observation>> { ... }
  async getGeographies(): Promise<Geography[]> { ... }
  async search(query: string): Promise<SearchResult[]> { ... }
}
```

**Verification:** Run `npm run dev` and confirm:
- `http://localhost:3000` redirects to `http://localhost:3000/ar` (Arabic default)
- Language switcher toggles between `/ar` and `/en`
- RTL layout works correctly in Arabic
- Header and Footer render in both languages

---

## STEP 4: Build Homepage

The homepage is the most important page — it's what people see first.

### Sections (top to bottom):

1. **Hero Section** — Full-width, clean. "Palestine in Data" / "فلسطين في أرقام" heading. Subtitle explaining the platform. Large search bar. Two CTA buttons: "Explore Data" and "API Access".

2. **Platform Stats Bar** — Horizontal strip showing: X Datasets, X Indicators, X Data Points, X Sources. Animated count-up on scroll.

3. **Key Indicators Grid** — 4-6 cards showing the most important current statistics (population, GDP, unemployment, etc.). Each card shows: indicator name, current value with unit, sparkline trend, source attribution, "as of [date]" timestamp. Pull from the API.

4. **Featured Datasets** — 3-4 cards for highlighted datasets. Each shows: dataset name, category badge, indicator count, last updated, brief description. Links to dataset detail page.

5. **Data Stories** (placeholder for Phase 2) — Section header with "Coming Soon" or first 2 stories if available.

6. **Open Data CTA** — Section promoting the API and open-source nature. Links to API docs and GitHub.

### Design Notes:
- The hero should feel authoritative and institutional, not flashy
- Use the green color palette sparingly — the page should feel mostly white/neutral with green accents
- Key indicator cards should be the visual centerpiece
- Everything must work in RTL Arabic layout
- Mobile-first responsive design

**Verification:** Homepage renders with all sections. Indicator cards show real data from the API (or placeholder data if API isn't seeded yet). Language switching works. Mobile layout is clean.

---

## STEP 5: Build First Data Pipeline (PCBS Population)

### Target Data:
Population statistics from PCBS — specifically:
- Total population by territory (West Bank, Gaza)
- Population by governorate
- Population by gender and age group
- Population growth rate
- Historical estimates (2000-present)

### Data Source URLs:
- Main statistics page: `https://www.pcbs.gov.ps/site/lang__en/507/default.aspx`
- Population statistics: navigate from Statistics > Demography
- Press releases with population estimates: `https://www.pcbs.gov.ps/pcbs_2012/PressEn.aspx`

### Pipeline Implementation (packages/pipeline):

**pipeline/base.py** — Abstract base class:
```python
class BasePipeline(ABC):
    """Base class for all data ingestion pipelines."""

    @abstractmethod
    async def collect(self) -> list[RawFile]: ...

    @abstractmethod
    async def extract(self, raw_files: list[RawFile]) -> pd.DataFrame: ...

    @abstractmethod
    async def transform(self, df: pd.DataFrame) -> pd.DataFrame: ...

    @abstractmethod
    async def load(self, df: pd.DataFrame) -> LoadResult: ...

    async def run(self) -> PipelineRunResult:
        """Execute full pipeline: collect → extract → transform → load."""
        # Create pipeline_runs record
        # Execute each stage with error handling
        # Update pipeline_runs record with results
        ...
```

**pipeline/sources/pcbs_population.py** — Implement all 4 stages. The PCBS website uses HTML tables extensively. Parse these with BeautifulSoup. Handle both Arabic and English pages. Map governorate names to geography codes.

### Testing:
Save sample HTML pages from PCBS in `tests/fixtures/`. Test each pipeline stage independently:
- `test_collect`: Mock HTTP, verify file downloads
- `test_extract`: Feed fixture HTML, verify DataFrame structure
- `test_transform`: Feed raw DataFrame, verify normalized output
- `test_load`: Use test DB, verify records inserted with source tracking

**Verification:** Run the pipeline against live PCBS data. Database should contain population observations with:
- Proper geography codes (PS, PS-WBK, PS-GZA, governorates)
- Source document records linking to PCBS URLs
- Historical data points across multiple years

---

## STEP 6: Build Data Explorer Page

The data explorer (`/[locale]/explore`) is the core user tool.

### Layout:
- Left sidebar: Filters (category, geography, time range, source)
- Main area: Results grid + visualization area
- Top: Search bar + active filter chips

### Functionality:
1. Browse all indicators grouped by category
2. Filter by geography (dropdown with governorate hierarchy)
3. Filter by time range (date range picker)
4. Filter by source
5. Click an indicator to see its time-series chart
6. Toggle between chart types: line, bar, table
7. Export filtered data as CSV, JSON, or Excel
8. Copy API endpoint for current query

### Chart Component (IndicatorChart.tsx):
Use D3.js for the time-series chart:
- Line chart with area fill
- Hover tooltip showing exact values
- Responsive (resizes with container)
- Support for multiple series (e.g., West Bank vs Gaza)
- Proper number formatting (Arabic numerals in AR locale)
- Source attribution below chart

### Data Table Component (DataTable.tsx):
- Sortable columns
- Pagination
- Alternating row colors
- RTL-compatible column alignment

**Verification:** Explorer page loads with real data. Filters work. Charts render. Export produces valid CSV. RTL layout works.

---

## STEP 7: Build Dataset & Indicator Detail Pages

### Dataset Detail (`/[locale]/datasets/[slug]`):
- Dataset name, description, category badge
- Metadata panel: source, methodology, coverage, frequency, license, version
- List of all indicators in this dataset (linked)
- Download button for full dataset (CSV, JSON, Excel)
- Citation generator (APA/Chicago format)
- Source attribution with link to original

### Indicator Detail (`/[locale]/indicators/[id]`):
- Indicator name, description, unit
- Time-series chart (D3, same component as explorer)
- Disaggregation selector (if dimensions available): gender, age group, etc.
- Geography selector: switch between national/territory/governorate views
- Data table with all observations
- Download button
- Related indicators sidebar
- Methodology notes
- Source attribution

**Verification:** Navigate from explorer → dataset → indicator. All data renders. Disaggregation filters work. Downloads work.

---

## STEP 8: Build Remaining Pages

### Data Catalog (`/[locale]/catalog`):
- Searchable grid of all datasets
- Filter by category, source, update frequency
- Card view with: name, category, indicator count, last updated, coverage
- Sort by name, date, relevance

### Methodology (`/[locale]/methodology`):
- Static content page (can be MDX or hardcoded initially)
- Sections: Our Approach, Data Sources (with links), Processing Pipeline, Quality Assurance, Limitations, Transparency Commitment
- Include a diagram of the data flow (collect → extract → transform → validate → publish)

### About (`/[locale]/about`):
- Mission statement
- Team (just founder for now)
- Contact information
- Open source links (GitHub)
- Partner acknowledgments
- Data license information

### API Docs (`/[locale]/developers`):
- Embedded Swagger/OpenAPI docs (iframe or rendered)
- Quick-start guide with code examples (Python, JavaScript, R, curl)
- Rate limiting information
- Authentication (none required for read access — note this)
- Link to GitHub for API client libraries

**Verification:** All pages render in both languages. Navigation works. No broken links.

---

## STEP 9: Add More Data Pipelines

Build pipelines for remaining Phase 1 datasets:

### PCBS Economic Indicators (pcbs_economy.py):
- GDP (annual, quarterly)
- Consumer Price Index (monthly)
- Trade balance (imports/exports)
- Construction cost index
- Source: PCBS economic statistics + press releases

### PCBS Labor Force (pcbs_labor.py):
- Unemployment rate (by territory, gender, age)
- Labor force participation rate
- Employment by sector
- Source: PCBS quarterly Labor Force Survey

### B'Tselem Casualties (btselem_casualties.py):
- Fatalities by year, territory, participation status
- Minors, women breakdowns
- Source: B'Tselem statistics database (https://statistics.btselem.org)
- Note: Handle with extreme care — these are human lives, not just data points

### World Bank Indicators (worldbank.py):
- GDP per capita, poverty rate
- Use World Bank API: `https://api.worldbank.org/v2/country/PSE/indicator/{code}`
- Map World Bank indicator codes to Data Palestine indicator codes

**Verification:** Each pipeline runs successfully. Database has 15+ indicators across 5 datasets. API serves all data correctly.

---

## STEP 10: Polish & Deploy

### Performance:
- API response caching with Redis (cache dataset/indicator lists for 5 minutes)
- Next.js static generation for relatively static pages (about, methodology)
- Image optimization
- Lazy-load charts and maps
- Gzip compression

### SEO:
- Proper meta tags (title, description, og:image) per page
- Structured data (JSON-LD) for datasets
- Sitemap.xml
- robots.txt

### Accessibility:
- ARIA labels on all interactive elements
- Keyboard navigation for charts and filters
- Color contrast compliance (WCAG AA)
- Screen reader-friendly data tables

### Deployment:
- Dockerfile for API (Python + uvicorn)
- Dockerfile for Web (Next.js standalone build)
- Docker Compose for production (or separate files)
- Cloudflare DNS configuration
- SSL via Cloudflare
- Health check monitoring

**Verification:** Lighthouse scores: Performance >90, Accessibility >90, SEO >90. All pages work in Chrome, Firefox, Safari. Mobile responsive. Both languages work end-to-end.

---

## Key Technical Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Monorepo vs polyrepo | Monorepo | Solo developer, shared types, simpler CI/CD |
| Python vs Node for API | Python (FastAPI) | Aligns with data science ecosystem, pipeline synergy |
| Next.js vs plain React | Next.js | SSR for SEO, i18n routing, API routes, ISR |
| PostgreSQL vs alternatives | PostgreSQL + TimescaleDB | Time-series optimized, PostGIS for geo, mature ecosystem |
| Dagster vs Airflow | Dagster | More modern, better for solo dev, excellent testing story |
| D3 vs Chart.js | D3 | More control for custom visualizations, better for maps |
| i18n approach | next-intl with path-based routing | Clean URLs (/ar/, /en/), good SSR support |
| Hosting region | EU (Hetzner) | Political resilience, good latency for MENA region, affordable |
