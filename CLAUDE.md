# Data Palestine — Claude Code Instructions

## Project Overview

**Data Palestine** is a nonprofit open data platform that aggregates, modernizes, and serves Palestinian statistical, humanitarian, and socioeconomic data. It pulls from PCBS, OCHA, World Bank, B'Tselem, UNRWA, HDX, and other sources — transforming scattered PDFs, outdated interfaces, and siloed databases into a unified, searchable, API-driven platform.

**Primary domain:** datapalestine.org
**Repository:** github.com/datapalestine

## Architecture Summary

- **Frontend:** Next.js 14+ (App Router) with Tailwind CSS, fully bilingual (Arabic RTL / English LTR)
- **Backend API:** FastAPI (Python 3.11+) — REST + future GraphQL
- **Database:** PostgreSQL 16 with TimescaleDB extension (time-series) + PostGIS (geographic)
- **Data Pipelines:** Python scripts orchestrated by GitHub Actions (Dagster later)
- **Search:** Meilisearch (Arabic support)
- **File Storage:** Local filesystem initially, MinIO later
- **Hosting target:** DigitalOcean Droplet (EU), behind Cloudflare CDN
- **CI/CD:** GitHub Actions

## Repository Structure

This is a **monorepo**. Everything lives in one repository.

```
data-palestine/
├── CLAUDE.md                    # This file
├── README.md                    # Public-facing project description
├── LICENSE                      # MIT License
├── .github/
│   └── workflows/
│       ├── ci.yml               # Lint, test, type-check on PR
│       ├── deploy.yml           # Deploy on merge to main
│       └── data-update.yml      # Scheduled data pipeline runs
├── apps/
│   ├── web/                     # Next.js frontend
│   │   ├── package.json
│   │   ├── next.config.ts
│   │   ├── tailwind.config.ts
│   │   ├── tsconfig.json
│   │   ├── messages/            # i18n translation files
│   │   │   ├── en.json
│   │   │   └── ar.json
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── [locale]/
│   │   │   │   │   ├── layout.tsx
│   │   │   │   │   ├── page.tsx          # Homepage dashboard
│   │   │   │   │   ├── explore/
│   │   │   │   │   │   └── page.tsx      # Data Explorer
│   │   │   │   │   ├── datasets/
│   │   │   │   │   │   ├── page.tsx      # Dataset catalog
│   │   │   │   │   │   └── [slug]/
│   │   │   │   │   │       └── page.tsx  # Individual dataset
│   │   │   │   │   ├── stories/
│   │   │   │   │   │   ├── page.tsx      # Data stories listing
│   │   │   │   │   │   └── [slug]/
│   │   │   │   │   │       └── page.tsx  # Individual story
│   │   │   │   │   ├── methodology/
│   │   │   │   │   │   └── page.tsx
│   │   │   │   │   ├── about/
│   │   │   │   │   │   └── page.tsx
│   │   │   │   │   └── api-docs/
│   │   │   │   │       └── page.tsx      # Interactive API docs
│   │   │   │   └── middleware.ts          # Locale detection
│   │   │   ├── components/
│   │   │   │   ├── layout/
│   │   │   │   │   ├── Header.tsx
│   │   │   │   │   ├── Footer.tsx
│   │   │   │   │   ├── LocaleSwitcher.tsx
│   │   │   │   │   └── MobileNav.tsx
│   │   │   │   ├── charts/
│   │   │   │   │   ├── LineChart.tsx
│   │   │   │   │   ├── BarChart.tsx
│   │   │   │   │   ├── MapView.tsx
│   │   │   │   │   └── SparkLine.tsx
│   │   │   │   ├── data/
│   │   │   │   │   ├── DataExplorer.tsx
│   │   │   │   │   ├── DatasetCard.tsx
│   │   │   │   │   ├── IndicatorTable.tsx
│   │   │   │   │   └── DownloadButton.tsx
│   │   │   │   └── ui/                   # Shared primitives
│   │   │   │       ├── Button.tsx
│   │   │   │       ├── Card.tsx
│   │   │   │       ├── Input.tsx
│   │   │   │       ├── Select.tsx
│   │   │   │       └── Skeleton.tsx
│   │   │   ├── lib/
│   │   │   │   ├── api.ts               # API client for backend
│   │   │   │   ├── i18n.ts              # Internationalization config
│   │   │   │   ├── utils.ts
│   │   │   │   └── formatters.ts        # Number/date formatters
│   │   │   └── styles/
│   │   │       └── globals.css
│   │   └── public/
│   │       ├── fonts/
│   │       └── images/
│   └── api/                     # FastAPI backend
│       ├── pyproject.toml
│       ├── alembic.ini
│       ├── alembic/
│       │   └── versions/
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py          # FastAPI app entry point
│       │   ├── config.py        # Settings via pydantic-settings
│       │   ├── database.py      # SQLAlchemy engine + session
│       │   ├── models/          # SQLAlchemy ORM models
│       │   │   ├── __init__.py
│       │   │   ├── dataset.py
│       │   │   ├── indicator.py
│       │   │   ├── observation.py
│       │   │   ├── source.py
│       │   │   └── geography.py
│       │   ├── schemas/         # Pydantic request/response schemas
│       │   │   ├── __init__.py
│       │   │   ├── dataset.py
│       │   │   ├── indicator.py
│       │   │   ├── observation.py
│       │   │   └── common.py
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   ├── deps.py      # Shared dependencies
│       │   │   └── v1/
│       │   │       ├── __init__.py
│       │   │       ├── router.py
│       │   │       ├── datasets.py
│       │   │       ├── indicators.py
│       │   │       ├── observations.py
│       │   │       ├── geographies.py
│       │   │       └── export.py
│       │   └── services/
│       │       ├── __init__.py
│       │       ├── dataset_service.py
│       │       └── export_service.py
│       └── tests/
│           ├── conftest.py
│           ├── test_datasets.py
│           └── test_indicators.py
├── pipelines/                   # Data ingestion pipelines
│   ├── pyproject.toml
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── extractors.py       # PDF, HTML, Excel extraction utils
│   │   ├── validators.py       # Data quality checks
│   │   ├── loaders.py          # Database loading utilities
│   │   └── models.py           # Shared pipeline data models
│   ├── pcbs/
│   │   ├── __init__.py
│   │   ├── scraper.py          # PCBS website scraper
│   │   ├── population.py       # Population dataset pipeline
│   │   ├── economic.py         # Economic indicators pipeline
│   │   └── labor.py            # Labor force pipeline
│   ├── worldbank/
│   │   ├── __init__.py
│   │   └── indicators.py       # World Bank API integration
│   ├── ocha/
│   │   ├── __init__.py
│   │   └── hdx.py              # HDX dataset integration
│   └── btselem/
│       ├── __init__.py
│       └── casualties.py       # B'Tselem data integration
├── schemas/                     # Database migration SQL + reference
│   ├── 001_initial.sql
│   └── seed_geographies.sql
├── docs/
│   ├── PROJECT_SPEC.md          # Full technical specification
│   ├── API_REFERENCE.md         # API endpoint documentation
│   ├── DATA_SOURCES.md          # All data sources with notes
│   ├── CONTRIBUTING.md
│   └── METHODOLOGY.md
└── docker/
    ├── docker-compose.yml       # Local development
    ├── Dockerfile.api
    └── Dockerfile.web
```

## Implementation Phases — What to Build and When

### PHASE 1A: Project Scaffold (Do This First)

1. Initialize the monorepo with the directory structure above
2. Set up `apps/api/` with FastAPI, SQLAlchemy, Alembic
3. Set up `apps/web/` with Next.js 14 App Router, Tailwind, next-intl
4. Set up `docker/docker-compose.yml` for local PostgreSQL + Meilisearch
5. Write the README.md with mission statement

### PHASE 1B: Database & API

1. Create PostgreSQL schema (see `schemas/001_initial.sql` in this kit)
2. Build SQLAlchemy models matching the schema
3. Build Alembic migrations
4. Implement API endpoints:
   - `GET /api/v1/datasets` — list all datasets with pagination + filtering
   - `GET /api/v1/datasets/{slug}` — single dataset with metadata
   - `GET /api/v1/indicators` — list indicators, filter by dataset/geography/category
   - `GET /api/v1/indicators/{id}` — single indicator with observations
   - `GET /api/v1/observations` — query observations with filters (geography, time range, indicator)
   - `GET /api/v1/geographies` — hierarchical geography tree
   - `GET /api/v1/export/{dataset_slug}` — export as CSV/JSON/Excel
5. Write tests for all endpoints

### PHASE 1C: Data Pipelines (First 3 Datasets)

1. Build PCBS scraper for population statistics
2. Build World Bank API integration for economic indicators
3. Build PCBS economic indicators pipeline (CPI, GDP, trade)
4. All pipelines must: extract → validate → load with full source provenance
5. Populate the database with real data

### PHASE 1D: Frontend

1. Build the layout shell: Header (bilingual), Footer, navigation
2. Homepage: key indicators dashboard with sparklines
3. Dataset catalog: searchable grid of all datasets
4. Individual dataset page: metadata + data table + chart
5. Data Explorer: multi-dataset query builder with visualization
6. Methodology page
7. About page

### PHASE 2: Expand (After Phase 1 is solid)

- Add 5+ more datasets (B'Tselem, OCHA, education, health, labor)
- API client libraries (Python package, npm package)
- Data Stories section (MDX-based long-form articles)
- Embeddable chart widgets
- Social sharing / OG images for datasets
- PWA offline support

## Critical Design Decisions

### Bilingual (Arabic RTL / English LTR)

- Use `next-intl` for internationalization
- All routes are `/{locale}/...` where locale is `en` or `ar`
- Arabic pages must have `dir="rtl"` on the html element
- Tailwind RTL: use logical properties (`ps-4` not `pl-4`, `ms-auto` not `ml-auto`)
- All user-facing text goes through translation files in `messages/`
- Font pairing: IBM Plex Sans (English) + IBM Plex Arabic (Arabic)
- Numbers should be displayed in Western Arabic numerals (0-9) in both languages

### API Design Principles

- All responses use consistent envelope: `{ data: T, meta: { total, page, per_page } }`
- Dates in ISO 8601, always UTC
- Filter via query params: `?geography=PS-GZA&year_from=2020&year_to=2025`
- Slug-based identification for datasets (e.g., `population-census-2017`)
- ID-based for indicators and observations (UUIDs)
- CORS enabled for all origins (public API)
- Rate limiting: 100 requests/minute unauthenticated, 1000 with API key

### Data Pipeline Standards

- Every observation must link to a source record (URL, document, page number)
- Every pipeline run is logged with timestamp, record counts, and errors
- Data is never overwritten — new versions are appended, old versions archived
- Validation rules run before loading: completeness, range checks, type checks
- Pipelines are idempotent: running them twice produces the same result

### Frontend Standards

- Mobile-first responsive design
- Lighthouse score targets: Performance > 90, Accessibility > 95
- Server-side render data pages for SEO
- Charts must have accessible alt text and tabular fallback
- All interactive elements keyboard-navigable
- Loading states with skeletons, not spinners
- Error boundaries with helpful messages

## Color System

```
Primary Green:    #1B5E20 (dark), #2E7D32 (medium), #4CAF50 (light)
Accent Red:       #B71C1C (dark), #C62828 (medium), #EF5350 (light)
Neutral:          #212121 (text), #757575 (secondary text), #E0E0E0 (borders), #FAFAFA (background)
Chart palette:    #2E7D32, #1565C0, #EF6C00, #6A1B9A, #C62828, #00838F
```

Use the Palestinian flag colors (green, red, black, white) as accents only — the UI should feel like a data institution, not an advocacy campaign.

## Environment Variables

```env
# API
DATABASE_URL=postgresql+asyncpg://datapalestine:localdev@localhost:5432/datapalestine
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_KEY=local-dev-key
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Web
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
NEXT_PUBLIC_DEFAULT_LOCALE=en
```

## Commands Reference

```bash
# Development
docker compose -f docker/docker-compose.yml up -d   # Start PostgreSQL + Meilisearch
cd apps/api && uvicorn app.main:app --reload         # Start API
cd apps/web && npm run dev                           # Start frontend

# Database
cd apps/api && alembic upgrade head                  # Run migrations
cd apps/api && alembic revision --autogenerate -m "description"  # New migration

# Pipelines
cd pipelines && python -m pcbs.population            # Run a specific pipeline
cd pipelines && python -m worldbank.indicators       # Run World Bank pipeline

# Testing
cd apps/api && pytest                                # API tests
cd apps/web && npm test                              # Frontend tests

# Linting
cd apps/api && ruff check . && ruff format .         # Python
cd apps/web && npm run lint                          # TypeScript/Next.js
```

## Key File References in This Kit

- `docs/PROJECT_SPEC.md` — Full technical specification with detailed requirements
- `docs/API_REFERENCE.md` — Complete API endpoint documentation
- `docs/DATA_SOURCES.md` — All data sources with URLs, formats, and integration notes
- `docs/EXTRACTION_STRATEGY.md` — **Critical**: How to actually extract PCBS data (CSV downloads, HTML scraping, PDF extraction) with real URL patterns and code
- `schemas/001_initial.sql` — PostgreSQL database schema
- `schemas/seed_geographies.sql` — Geography seed data (Palestine → Territories → Governorates)
- `reference/pcbs_datasets.md` — PCBS data categories and URLs for scraping

## Non-Negotiable Rules

1. **Source attribution**: Every data point must trace back to its original source. No orphan data.
2. **Never editorialize**: The platform presents data, not opinions. No editorial framing of numbers.
3. **Bilingual always**: No page ships without both Arabic and English translations.
4. **API-first**: Every feature works through the API. The frontend is just one client.
5. **Accessibility**: WCAG 2.1 AA compliance minimum.
6. **Performance**: Pages must work on 3G connections. Target < 200KB initial bundle per page.
7. **Privacy**: Never collect user data beyond anonymous analytics. No tracking pixels.

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Data Palestine**

An open data platform that aggregates, modernizes, and serves Palestinian statistical, humanitarian, and socioeconomic data. It pulls from PCBS, World Bank, Tech for Palestine, B'Tselem, and other sources — transforming scattered data into a unified, bilingual (Arabic RTL / English LTR), API-driven platform at datapalestine.org.

**Core Value:** Researchers, journalists, and policymakers can explore and download reliable Palestinian data through a professional, institutional-quality interface — in both Arabic and English.

### Constraints

- **Tech stack**: Next.js 15 + FastAPI + PostgreSQL 16 + TimescaleDB — already built, no changes
- **Bilingual**: Every user-facing string must work in both English and Arabic RTL
- **Performance**: Pages must work on 3G connections, < 200KB initial bundle per page
- **Accessibility**: WCAG 2.1 AA compliance minimum
- **Privacy**: No user data collection beyond anonymous analytics
- **Source attribution**: Every data point traces back to its original source
- **No editorializing**: Platform presents data, not opinions
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12+ (3.14 in local venv) - Backend API (`apps/api/`) and data pipelines (`packages/pipeline/`)
- TypeScript 5.5+ - Frontend (`apps/web/`)
- SQL (PostgreSQL 16 dialect) - Schema definitions and seed data (`packages/db/schema.sql`)
## Runtime
- Python 3.12+ (CI uses 3.12, local venv uses 3.14)
- Node.js 20 (specified in CI and Dockerfiles)
- npm (frontend) - Lockfile: `apps/web/package-lock.json` present
- pip (Python) - No lockfile; dependencies specified in `pyproject.toml` with minimum versions only
## Frameworks
- FastAPI >=0.111.0 - REST API server (`apps/api/app/main.py`)
- Next.js ^15.0.0 (App Router) - Frontend SSR application (`apps/web/`)
- React ^19.0.0 - UI rendering
- pytest >=8.2.0 - Python test runner for API and pipeline tests
- pytest-asyncio >=0.23.0 - Async test support (mode: `auto`)
- pytest-cov >=5.0.0 - Coverage reporting
- uvicorn[standard] >=0.30.0 - ASGI server for FastAPI
- Tailwind CSS ^4.0.0 - Utility-first CSS via `@tailwindcss/postcss` plugin
- PostCSS ^8.5.8 - CSS processing (`apps/web/postcss.config.mjs`)
## Key Dependencies
- `asyncpg` >=0.29.0 - Async PostgreSQL driver; used directly for connection pool in `apps/api/app/main.py` (lifespan) AND via SQLAlchemy async engine in `apps/api/app/database.py`
- `sqlalchemy` (imported in `apps/api/app/database.py`) - ORM with async support; note: NOT listed in `apps/api/pyproject.toml` dependencies (likely installed transitively or missing)
- `pydantic` >=2.7.0 - Data validation for request/response schemas
- `pydantic-settings` >=2.3.0 - Environment-based configuration (`apps/api/app/config.py`)
- `httpx` >=0.27.0 - Async HTTP client for API fetching (World Bank, PCBS, Tech for Palestine)
- `psycopg2` / `psycopg2-binary` - Sync PostgreSQL driver for pipeline database operations (used directly, not via ORM)
- `pandas` >=2.2.0 - DataFrame processing for CSV/data transformation
- `beautifulsoup4` >=4.12.0 - HTML parsing for PCBS discovery crawler
- `openpyxl` >=3.1.0 - Excel file parsing for PCBS XLSX files
- `camelot-py[base]` >=0.11.0 - PDF table extraction (declared but not yet used in implemented pipelines)
- `tabula-py` >=2.9.0 - PDF table extraction (declared but not yet used in implemented pipelines)
- `next-intl` ^4.0.0 - Internationalization (Arabic RTL / English LTR); configured in `apps/web/i18n.ts` and `apps/web/next.config.ts`
- `recharts` ^3.8.0 - Chart rendering library
- `starlette` (via FastAPI) - CORS middleware, rate limiting middleware (`apps/api/app/main.py`)
## Database
- PostgreSQL 16 via `timescale/timescaledb-ha:pg16` Docker image
- TimescaleDB extension - Hypertable on `observations` table for time-series partitioning
- PostGIS extension - Geometry column on `geographies` table (MultiPolygon, SRID 4326)
- API uses dual connections: asyncpg pool directly (`app.state.pool`) AND SQLAlchemy async engine (`apps/api/app/database.py`)
- Pipelines use `psycopg2` (sync) directly with raw SQL and `execute_values` for bulk inserts
## Linting & Formatting
- Ruff >=0.4.0 - Linter and formatter
- Target: Python 3.12
- Line length: 100
- Lint rules: `["E", "F", "I", "N", "W", "UP"]` (pycodestyle, pyflakes, isort, pep8-naming, warnings, pyupgrade)
- Config: `[tool.ruff]` sections in `apps/api/pyproject.toml` and `packages/pipeline/pyproject.toml`
- Biome ^1.8.0 - Linter and formatter (replaces ESLint+Prettier)
- No `biome.json` config file found; uses defaults
- Lint command: `biome check .`
- Fix command: `biome check --write .`
- TypeScript strict mode enabled (`apps/web/tsconfig.json`: `"strict": true`)
- Command: `npx tsc --noEmit`
## Configuration
- Settings loaded via pydantic-settings from `.env` file (`apps/api/app/config.py`)
- Key env vars: `DATABASE_URL`, `DATABASE_URL_SYNC`, `ENVIRONMENT`, `SECRET_KEY`, `CORS_ORIGINS`, `RATE_LIMIT_PER_MINUTE`
- Frontend env vars: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_MAPBOX_TOKEN`
- Reference files: `.env.example`, `.env.production.example`
- `apps/web/next.config.ts` - Next.js config with next-intl plugin, standalone output, API proxy rewrites
- `apps/web/postcss.config.mjs` - PostCSS with Tailwind v4
- `apps/web/tsconfig.json` - TypeScript config with `@/*` path alias
- `@/*` maps to `apps/web/*` (configured in `apps/web/tsconfig.json`)
## Platform Requirements
- Docker (for PostgreSQL/TimescaleDB)
- Python 3.12+
- Node.js 20+
- No workspace/monorepo tool (Turborepo, Nx, etc.) - apps are managed independently
- DigitalOcean Droplet (IP: 64.225.65.231, EU region)
- Docker Compose (`docker/docker-compose.prod.yml`)
- Caddy 2 as reverse proxy with automatic HTTPS
- Deployed via SSH + `git pull` + `docker compose up --build` (`.github/workflows/deploy.yml`)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Snake_case for all Python modules: `dataset.py`, `api_fetch.py`, `pcbs_population.py`
- ORM models: singular noun (`dataset.py`, `indicator.py`, `observation.py`)
- Routers: plural noun matching the resource (`datasets.py`, `indicators.py`, `observations.py`)
- Tests: `test_` prefix matching the module under test (`test_datasets.py`, `test_pcbs_population.py`)
- PascalCase for React components: `Header.tsx`, `Footer.tsx`, `DataExplorer.tsx`, `Sparkline.tsx`
- kebab-case for lib modules: `api-client.ts`, `api-fetch.ts`
- camelCase for non-component TS modules: `formatters.ts`, `constants.ts`
- Route pages: `page.tsx` inside directory-based routing (`[locale]/datasets/page.tsx`)
- snake_case: `list_datasets`, `get_indicator`, `export_dataset`
- Router handlers match HTTP method + resource: `list_datasets`, `get_dataset`, `get_dataset_geographies`
- Test functions: `test_` prefix with descriptive name: `test_list_datasets`, `test_get_dataset_not_found`
- camelCase: `formatValue`, `formatYear`, `getHighlightData`
- API client functions: `get` prefix for server-side (`getDatasets`, `getIndicators`)
- API fetch functions: `fetch` prefix for client-side (`fetchDatasets`, `fetchIndicators`)
- Builder functions: `build` prefix (`buildApiUrl`, `buildExportUrl`)
- PascalCase: `BasePipeline`, `PCBSPopulationPipeline`, `RateLimitMiddleware`
- ORM models: singular PascalCase (`Dataset`, `Indicator`, `Observation`)
- Pydantic schemas: descriptive PascalCase (`PaginationMeta`, `PaginatedResponse`, `ErrorDetail`)
- Enums: PascalCase class, lowercase values (`DatasetStatus.draft`, `ObservationStatus.final`)
- PascalCase: `Dataset`, `Indicator`, `Observation`, `Geography`
- Ref suffix for nested references: `CategoryRef`, `SourceRef`, `IndicatorRef`
- Extended types use `extends`: `DatasetDetail extends Dataset`
- Python: snake_case (`pool`, `count_sql`, `data_sql`, `name_key`)
- TypeScript: camelCase (`keyIndicators`, `highlightData`, `totalDatasets`)
- Constants (TS): SCREAMING_SNAKE_CASE (`KEY_INDICATOR_CODES`, `GEOGRAPHY_CODES`, `CATEGORY_SLUGS`)
- Constants (Python): PascalCase for Settings class fields, snake_case for module-level
## Code Style
- Tool: Ruff (format + lint combined)
- Config: `apps/api/pyproject.toml` and `packages/pipeline/pyproject.toml`
- Line length: 100
- Target: Python 3.12
- Run: `ruff format .` and `ruff check .`
- CI enforces: `ruff format --check .`
- Tool: Ruff
- Rules enabled: `["E", "F", "I", "N", "W", "UP"]`
- Tool: Biome (not ESLint/Prettier)
- Config: managed via `@biomejs/biome` package in `apps/web/package.json`
- Run: `biome check .` (lint), `biome check --write .` (fix)
- No `.prettierrc` or `.eslintrc` files
- Strict TypeScript via `apps/web/tsconfig.json`
- Run: `npx tsc --noEmit`
- CI runs type check as a separate step
## Import Organization
- Use `from X import Y` for specific items
- Use `from collections.abc import AsyncIterator` (modern style, enforced by `UP` rule)
- noqa comments where needed: `# noqa: E402` for late imports, `# noqa: F821` for forward references
- `@/` maps to `apps/web/` root (configured in `apps/web/tsconfig.json`)
- Usage: `@/components/layout/Header`, `@/lib/api-client`, `@/app/globals.css`
## API Response Format
- All endpoints accept `lang` query parameter: `Literal["en", "ar"]`, default `"en"`
- Bilingual fields use `_{lang}` suffix in DB: `name_en`, `name_ar`, `description_en`, `description_ar`
- Response returns localized field without suffix: `"name": row[f"name_{lang}"]`
- Pattern used consistently across all routers:
## Database Query Patterns
## Error Handling
- Use `HTTPException` for expected errors: `raise HTTPException(status_code=404, detail="...")`
- Global 404 handler in `apps/api/app/main.py` wraps exceptions in error envelope
- Rate limiting returns 429 with `Retry-After` header
- Production startup fails loudly if `SECRET_KEY` is not set (see `apps/api/app/config.py`)
- API client throws on non-200: `if (!res.ok) throw new Error(...)`
- Page-level data fetching uses try/catch with fallback:
- Empty catch blocks used for non-critical data: `try { ... } catch {}`
- Null checks used to gracefully skip missing data in JSX: `if (!data) return null`
- `BasePipeline.run()` in `packages/pipeline/pipeline/base.py` wraps entire execution in try/catch
- Returns `PipelineRunResult` with `status: "failed"` and `error_message` on exception
- Never crashes; always returns a result object
## Component Patterns (React/Next.js)
- Pages are async server components: `export default async function HomePage({ params })`
- Use `getTranslations` from `next-intl/server` for i18n
- Fetch data directly with async/await (no useEffect)
- Example: `apps/web/app/[locale]/page.tsx`
- Mark with `"use client"` directive at top of file
- Use `useTranslations` from `next-intl` (not `next-intl/server`)
- Use `useLocale`, `usePathname`, `useRouter` for navigation
- Example: `apps/web/components/layout/Header.tsx`, `apps/web/components/data/DataExplorer.tsx`
- Named exports (not default): `export function Header()`, `export function Footer()`
- Page components use default export: `export default async function HomePage()`
- Use `next/dynamic` with `{ ssr: false }` for heavy client libs (recharts):
- Route params are `Promise`-based: `params: Promise<{ locale: string }>`
- Always await: `const { locale } = await params;`
## i18n Patterns
- `apps/web/i18n.ts` — server-side config, loads JSON messages
- `apps/web/i18n/routing.ts` — defines locales `["en", "ar"]`, default `"ar"`
- `apps/web/middleware.ts` — locale detection middleware
- `apps/web/messages/en.json` — English translations
- `apps/web/messages/ar.json` — Arabic translations
- Structure: nested by page/section (`home.hero.title`, `nav.explore`, `common.loading`)
## RTL/LTR Handling
- English: IBM Plex Sans (loaded via `next/font/google`)
- Monospace: IBM Plex Mono
- Arabic: Not separately loaded yet (relies on system Arabic fonts)
- Font variables: `--font-plex-sans`, `--font-plex-mono`
## Logging
## Comments and Docstrings
- Every module has a top-level docstring: `"""Dataset API routes: wired to real PostgreSQL data."""`
- Every function/method has a docstring: `"""List all datasets with pagination, search, and category filter."""`
- Inline comments for complex SQL or logic
- Use `# noqa` comments with specific codes when suppressing lints
- JSDoc-style comments on module exports: `/** Typed API client for Data Palestine backend. */`
- Inline comments for non-obvious logic
- No TSDoc on individual functions (kept minimal)
## Module Design
- `__init__.py` files use explicit `__all__` lists (see `apps/api/app/models/__init__.py`)
- Re-export from package init for convenience: `from app.models.dataset import Dataset`
- Named exports preferred over default exports for non-page modules
- Type re-exports: `export type { Dataset, Indicator, ... }` at bottom of `apps/web/lib/api-client.ts`
- Two API client files with distinct purposes:
- `apps/api/app/models/__init__.py` — re-exports all ORM models
- `apps/api/app/schemas/__init__.py` — exists but content not heavy
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- API-first design: all data access goes through the FastAPI REST API
- Database is the single source of truth; pipelines write, API reads, frontend consumes API
- Bilingual throughout: every user-facing string has `_en` and `_ar` variants at the database, API, and UI layers
- No ORM queries at runtime: routers use raw asyncpg SQL, not SQLAlchemy (ORM models exist for Alembic/reference only)
- Server-side rendering: Next.js pages fetch from the API at request time with 5-minute revalidation
## System Architecture
```
```
## Layers
- Purpose: Persistent storage for all statistical data with time-series optimization
- Location: `packages/db/schema.sql`
- Contains: DDL for 9 tables, 7 enums, 2 views, seed data for geographies/categories/sources
- Key feature: `observations` table is a TimescaleDB hypertable partitioned by `time_period`
- Extensions: TimescaleDB (time-series), PostGIS (geometry, not yet actively used in queries)
- Purpose: RESTful JSON API serving all data to any client
- Location: `apps/api/`
- Entry point: `apps/api/app/main.py` -- FastAPI app with lifespan-managed asyncpg pool
- Contains: Routers (raw SQL queries), Pydantic schemas (response types), SQLAlchemy models (reference/migrations)
- Depends on: PostgreSQL via asyncpg connection pool (`request.app.state.pool`)
- Used by: Next.js frontend, potential third-party consumers
- Purpose: Server-rendered bilingual web UI for exploring Palestinian data
- Location: `apps/web/`
- Entry point: `apps/web/app/[locale]/layout.tsx`
- Contains: Next.js App Router pages, React components, i18n config, API client
- Depends on: FastAPI backend via HTTP (typed client in `apps/web/lib/api-client.ts`)
- Purpose: Ingest data from external sources into the database
- Location: `packages/pipeline/`
- Contains: Abstract base class, source-specific pipeline implementations, shared models
- Depends on: PostgreSQL via psycopg2 (sync), external HTTP APIs via httpx
- Used by: Manual execution (`python -m pipeline.sources.worldbank`), future GitHub Actions
## Data Flow
## API Architecture
- Import `APIRouter` and `paginate` from `apps/api/app/schemas/common.py`
- Acquire asyncpg pool from `request.app.state.pool`
- Build SQL dynamically with whitelist-validated sort columns
- Use `$N` parameterized queries (never string interpolation of user input into SQL)
- Return consistent envelope: `{ data: [...], meta: {...} }` for lists, `{ data: {...} }` for singles
| Router | File | Endpoints |
|--------|------|-----------|
| Datasets | `apps/api/app/routers/datasets.py` | `GET /datasets`, `GET /datasets/{slug}`, `GET /datasets/{slug}/geographies` |
| Indicators | `apps/api/app/routers/indicators.py` | `GET /indicators`, `GET /indicators/{id}` |
| Observations | `apps/api/app/routers/observations.py` | `GET /observations` (main data query) |
| Geographies | `apps/api/app/routers/geographies.py` | `GET /geographies`, `GET /geographies/{code}` |
| Sources | `apps/api/app/routers/sources.py` | `GET /sources`, `GET /sources/{id}` |
| Export | `apps/api/app/routers/export.py` | `GET /export/{dataset_slug}` (CSV download) |
- CORS: allows all origins in development, configurable in production
- Rate limiting: custom in-memory `RateLimitMiddleware` (100 req/min default per IP)
```python
```
## Database Schema
```
```
| Table | Purpose | Primary Key | Row Volume |
|-------|---------|-------------|------------|
| `geographies` | Palestine hierarchy (national/territory/governorate) | `id` (serial), unique on `code` | ~19 rows |
| `sources` | Data provider organizations (PCBS, World Bank, etc.) | `id` (serial), unique on `slug` | ~10 rows |
| `source_documents` | Specific documents/API calls data was extracted from | `id` (serial) | Grows per pipeline run |
| `categories` | Topic groupings (economy, health, conflict, etc.) | `id` (serial), unique on `slug` | 10 rows |
| `datasets` | Top-level data containers | `id` (serial), unique on `slug` | ~10-50 |
| `indicators` | Measurable variables within datasets | `id` (serial), unique on `(dataset_id, code)` | ~100-1000 |
| `observations` | Actual data points (TimescaleDB hypertable) | `(id, time_period)` composite | 10K-1M+ |
| `pipeline_runs` | Audit trail for data ingestion | `id` (serial) | Grows per pipeline run |
| `data_stories` | Phase 2 MDX articles (schema exists, not populated) | `id` (serial) | 0 |
```
```
## Frontend Architecture
- next-intl App Router with `[locale]` dynamic segment
- Supported locales: `en`, `ar` (default: `ar`)
- Middleware in `apps/web/middleware.ts` handles locale detection/redirect
- RTL is set via `dir` attribute on `<html>` in layout
| Category | Location | Rendering |
|----------|----------|-----------|
| Pages | `apps/web/app/[locale]/*/page.tsx` | Server components (async) |
| Layout | `apps/web/components/layout/` | Client components (`"use client"`) |
| Charts | `apps/web/components/charts/` | Server components (SVG) |
| Data | `apps/web/components/data/` | Client components (interactive) |
- `apps/web/lib/api-client.ts` -- Server-side: used in page components, has `next: { revalidate: 300 }`, prefers `API_INTERNAL_URL`
- `apps/web/lib/api-fetch.ts` -- Client-side: used in `"use client"` components, plain fetch, uses `NEXT_PUBLIC_API_URL`
- `apps/web/i18n.ts` -- next-intl server config, loads messages from `apps/web/messages/{locale}.json`
- `apps/web/i18n/routing.ts` -- defines locales and default locale
- `apps/web/messages/en.json` and `apps/web/messages/ar.json` -- translation files
- Tailwind CSS v4 with PostCSS
- No component library (all custom primitives)
- Color tokens defined inline: primary green `#1B5E20`/`#2E7D32`/`#4CAF50`, accent red `#C62828`, neutrals
- Fonts: IBM Plex Sans (latin), IBM Plex Mono (code) -- loaded via next/font/google
## Pipeline Architecture
- Abstract `BasePipeline` with four-stage pattern: `collect -> extract -> transform -> load`
- `run()` method orchestrates the four stages with error handling and timing
- Returns `PipelineRunResult` dataclass
- `RawFile` -- downloaded file metadata (path, URL, type, checksum)
- `LoadResult` -- insertion counts (processed, inserted, updated, skipped)
- `PipelineRunResult` -- full pipeline execution result
| Pipeline | File | Status | Pattern |
|----------|------|--------|---------|
| World Bank | `packages/pipeline/pipeline/sources/worldbank.py` | Working | Standalone `run_pipeline()` function with psycopg2 |
| Tech for Palestine | `packages/pipeline/pipeline/sources/techforpalestine.py` | Working | Standalone `run()` function with psycopg2 |
| PCBS Population | `packages/pipeline/pipeline/sources/pcbs_population.py` | Stub | Extends `BasePipeline`, all methods raise `NotImplementedError` |
| PCBS Economy | `packages/pipeline/pipeline/sources/pcbs_economy.py` | Unknown | Listed in sources |
| PCBS Labor | `packages/pipeline/pipeline/sources/pcbs_labor.py` | Unknown | Listed in sources |
| PCBS CSV Ingest | `packages/pipeline/pipeline/sources/pcbs_csv_ingest.py` | Unknown | Listed in sources |
| PCBS Discovery | `packages/pipeline/pipeline/sources/pcbs_discovery.py` | Unknown | Listed in sources |
| B'Tselem | `packages/pipeline/pipeline/sources/btselem_casualties.py` | Unknown | Listed in sources |
## Entry Points
- Location: `apps/api/app/main.py`
- Run: `cd apps/api && uvicorn app.main:app --reload`
- The `app` object is created at module level with lifespan-managed asyncpg pool
- Location: `apps/web/app/[locale]/layout.tsx` (root layout)
- Run: `cd apps/web && npm run dev`
- Config: `apps/web/next.config.ts` (standalone output, API proxy rewrites)
- Run individually: `python -m pipeline.sources.worldbank` (from `packages/pipeline/`)
- Each pipeline script has `if __name__ == "__main__"` block
- DB URL passed via CLI arg or `DATABASE_URL` env var
- `packages/db/schema.sql` is mounted into Docker entrypoint
- Run: `docker compose up db` auto-initializes schema + seed data
## Error Handling
- `HTTPException(status_code=404)` caught by custom handler returning `{"error": {"code": "NOT_FOUND", "message": "..."}}`
- Rate limit returns 429 with `Retry-After` header
- No global exception handler for 500s (unhandled errors return default FastAPI response)
- Page components wrap API calls in try/catch, render "not found" fallback on error
- `api-client.ts` throws on non-2xx status codes
- No error boundary components yet
- Pipelines wrap all DB operations in a transaction
- On failure: rollback, record failed pipeline_run, re-raise
- Errors logged via Python `logging` module
## Cross-Cutting Concerns
- API: FastAPI default (stdout in development)
- Pipelines: Python `logging` module with `INFO` level
- Frontend: `console.error` for failed API calls
- API: FastAPI `Query()` params with type hints and constraints (`ge=1`, `le=1000`)
- SQL injection prevention: parameterized queries with `$N` placeholders throughout
- Sort column whitelisting: only predefined column names allowed in ORDER BY
- Next.js ISR: `{ next: { revalidate: 300 } }` (5-minute) on all server-side API fetches
- No server-side caching in the API layer
- asyncpg connection pooling (2-10 connections) for database
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
