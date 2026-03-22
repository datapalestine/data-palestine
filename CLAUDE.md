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
