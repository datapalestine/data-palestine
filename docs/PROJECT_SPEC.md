# Data Palestine — Full Technical Specification

## 1. Backend API (FastAPI)

### Project Setup

```toml
# apps/api/pyproject.toml
[project]
name = "datapalestine-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy[asyncio]>=2.0.25",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-multipart>=0.0.6",
    "httpx>=0.26.0",
    "openpyxl>=3.1.0",
    "orjson>=3.9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.26.0",
    "ruff>=0.1.0",
]
```

### Configuration (Pydantic Settings)

```python
# apps/api/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://datapalestine:localdev@localhost:5432/datapalestine"
    meilisearch_url: str = "http://localhost:7700"
    meilisearch_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    default_page_size: int = 20
    max_page_size: int = 100
    export_max_rows: int = 100000

    class Config:
        env_file = ".env"

settings = Settings()
```

### SQLAlchemy Models

Follow the schema in `schemas/001_initial.sql` exactly. Use:
- `mapped_column` with type annotations (SQLAlchemy 2.0 style)
- `AsyncSession` for all database operations
- UUID primary keys via `uuid7` or `gen_random_uuid()`
- Relationships with `lazy="selectin"` for async compatibility
- JSONB columns using `sqlalchemy.dialects.postgresql.JSONB`

### API Structure

```python
# apps/api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.config import settings

app = FastAPI(
    title="Data Palestine API",
    description="Open API for Palestinian statistical and humanitarian data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
```

### Response Schema Pattern

Every endpoint uses this consistent pattern:

```python
# apps/api/app/schemas/common.py
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar("T")

class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: PaginationMeta

class SingleResponse(BaseModel, Generic[T]):
    data: T

class ErrorDetail(BaseModel):
    code: str
    message: str
    detail: Optional[str] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
```

### Query Parameter Pattern

Use dependency injection for common query params:

```python
# apps/api/app/api/deps.py
from fastapi import Query

class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        sort: str = Query("name"),
        order: str = Query("asc", pattern="^(asc|desc)$"),
        lang: str = Query("en", pattern="^(en|ar)$"),
    ):
        self.page = page
        self.per_page = per_page
        self.sort = sort
        self.order = order
        self.lang = lang
        self.offset = (page - 1) * per_page
```


---

## 2. Frontend (Next.js)

### Project Setup

```json
// apps/web/package.json — key dependencies
{
  "dependencies": {
    "next": "^14.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "next-intl": "^3.4.0",
    "d3": "^7.8.0",
    "@visx/visx": "^3.5.0",
    "mapbox-gl": "^3.1.0",
    "swr": "^2.2.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "tailwindcss": "^3.4.0",
    "@types/react": "^18.2.0",
    "@types/d3": "^7.4.0"
  }
}
```

### Internationalization Setup (next-intl)

```typescript
// apps/web/src/lib/i18n.ts
import { getRequestConfig } from 'next-intl/server';

export const locales = ['en', 'ar'] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = 'en';

export default getRequestConfig(async ({ locale }) => ({
  messages: (await import(`../../messages/${locale}.json`)).default,
}));
```

### Locale Layout

```typescript
// apps/web/src/app/[locale]/layout.tsx
import { IBM_Plex_Sans, IBM_Plex_Sans_Arabic } from 'next/font/google';
// Note: If IBM Plex Arabic is unavailable in next/font, use Noto Sans Arabic

export default function LocaleLayout({
  children,
  params: { locale },
}: {
  children: React.ReactNode;
  params: { locale: string };
}) {
  const dir = locale === 'ar' ? 'rtl' : 'ltr';

  return (
    <html lang={locale} dir={dir}>
      <body className={locale === 'ar' ? fontArabic.className : fontEnglish.className}>
        {children}
      </body>
    </html>
  );
}
```

### API Client

```typescript
// apps/web/src/lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchAPI<T>(
  endpoint: string,
  params?: Record<string, string | number | undefined>,
  locale: string = 'en'
): Promise<T> {
  const url = new URL(`${API_URL}/api/v1${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) url.searchParams.set(key, String(value));
    });
  }
  url.searchParams.set('lang', locale);

  const res = await fetch(url.toString(), {
    next: { revalidate: 3600 }, // Cache for 1 hour
  });

  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
```

### Homepage Dashboard

The homepage should display a grid of key indicator cards, each showing:
- Indicator name (bilingual)
- Latest value with unit
- Sparkline showing trend (last 10 data points)
- Source attribution
- Time period

**Key indicators for homepage:**
1. Total Population (Palestine)
2. GDP (current USD)
3. Unemployment Rate
4. Poverty Rate
5. CPI / Inflation
6. Population — Gaza Strip
7. Population — West Bank

Below the indicators: a search bar, category navigation, and 2-3 featured data stories.

### Data Explorer Page

The most complex frontend component. Features:
- Dataset selector (dropdown or search)
- Indicator selector (filtered by selected dataset)
- Geography filter (hierarchical: territory → governorate)
- Time range selector (year range slider)
- Visualization toggle: table / line chart / bar chart / map
- Export button (CSV, JSON, Excel)
- Shareable URL (all filters encoded in query params)

Use `swr` for client-side data fetching with automatic caching and revalidation.

### Chart Components

Build reusable chart components using D3 or visx:

```typescript
// apps/web/src/components/charts/LineChart.tsx
interface LineChartProps {
  data: { date: string; value: number; label?: string }[];
  width?: number;
  height?: number;
  color?: string;
  showAxis?: boolean;
  locale?: string;
}
```

Charts must:
- Be responsive (use ResizeObserver or container queries)
- Support RTL layout (axis labels, legends)
- Have accessible alt text via `aria-label`
- Include tabular data fallback for screen readers
- Use the project color palette

### Tailwind Configuration

```typescript
// apps/web/tailwind.config.ts
import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#E8F5E9',
          100: '#C8E6C9',
          200: '#A5D6A7',
          300: '#81C784',
          400: '#66BB6A',
          500: '#4CAF50',
          600: '#43A047',
          700: '#388E3C',
          800: '#2E7D32',
          900: '#1B5E20',
        },
        accent: {
          50: '#FFEBEE',
          100: '#FFCDD2',
          500: '#EF5350',
          700: '#C62828',
          900: '#B71C1C',
        },
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'sans-serif'],
        arabic: ['IBM Plex Sans Arabic', 'Noto Sans Arabic', 'sans-serif'],
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
};
```


---

## 3. Data Pipelines

### Pipeline Architecture

Each pipeline follows this pattern:

```python
# pipelines/shared/models.py
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID
from typing import Optional

@dataclass
class RawObservation:
    """A single data point extracted from a source, before loading."""
    indicator_code: str
    indicator_name_en: str
    indicator_name_ar: str
    geography_code: str
    time_period: date
    time_precision: str  # "year", "quarter", "month", "day"
    value: float
    value_status: str = "final"
    unit: str = ""
    dimensions: dict = field(default_factory=dict)
    notes: str = ""

@dataclass
class PipelineResult:
    """Result of a pipeline run."""
    pipeline_name: str
    status: str  # "success", "failed", "partial"
    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: list = field(default_factory=list)
```

### Pipeline Template

```python
# Example: pipelines/worldbank/indicators.py
import httpx
from shared.models import RawObservation, PipelineResult
from shared.loaders import load_observations
from shared.validators import validate_observations

# World Bank indicator codes to fetch
INDICATORS = {
    "NY.GDP.MKTP.CD": ("GDP (current USD)", "الناتج المحلي الإجمالي (بالدولار الأمريكي الجاري)", "USD", "economy"),
    "SP.POP.TOTL": ("Total Population", "إجمالي السكان", "persons", "demographics"),
    "SL.UEM.TOTL.ZS": ("Unemployment Rate", "معدل البطالة", "percent", "economy"),
    # ... more indicators
}

WB_API_BASE = "https://api.worldbank.org/v2"
COUNTRY_CODE = "PSE"

async def fetch_indicator(client: httpx.AsyncClient, code: str) -> list[dict]:
    """Fetch all available data for a World Bank indicator."""
    url = f"{WB_API_BASE}/country/{COUNTRY_CODE}/indicator/{code}"
    params = {"format": "json", "per_page": 500, "date": "1990:2025"}
    response = await client.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    if len(data) < 2:
        return []
    return [item for item in data[1] if item.get("value") is not None]

async def run() -> PipelineResult:
    """Main pipeline entry point."""
    observations: list[RawObservation] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for code, (name_en, name_ar, unit, category) in INDICATORS.items():
            raw_data = await fetch_indicator(client, code)
            for item in raw_data:
                obs = RawObservation(
                    indicator_code=f"WB_{code}",
                    indicator_name_en=name_en,
                    indicator_name_ar=name_ar,
                    geography_code="PS",  # National level
                    time_period=date(int(item["date"]), 1, 1),
                    time_precision="year",
                    value=float(item["value"]),
                    unit=unit,
                )
                observations.append(obs)

    # Validate
    valid, errors = validate_observations(observations)

    # Load into database
    result = await load_observations(
        valid,
        dataset_slug="world-bank-indicators",
        source_organization="World Bank",
        source_url="https://data.worldbank.org/country/west-bank-and-gaza",
    )
    result.errors = errors
    return result

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(run())
    print(f"Pipeline complete: {result.status}")
    print(f"  Created: {result.records_created}")
    print(f"  Errors: {len(result.errors)}")
```


---

## 4. Docker Compose (Local Development)

```yaml
# docker/docker-compose.yml
version: "3.9"

services:
  db:
    image: timescale/timescaledb-ha:pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: datapalestine
      POSTGRES_PASSWORD: localdev
      POSTGRES_DB: datapalestine
    volumes:
      - pgdata:/home/postgres/pgdata/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U datapalestine"]
      interval: 10s
      timeout: 5s
      retries: 5

  search:
    image: getmeili/meilisearch:v1.6
    ports:
      - "7700:7700"
    environment:
      MEILI_ENV: development
      MEILI_MASTER_KEY: local-dev-key
    volumes:
      - searchdata:/meili_data

volumes:
  pgdata:
  searchdata:
```


---

## 5. README.md Template

The public README should include:
1. Project name and one-line description
2. Mission statement (3-4 sentences)
3. What Data Palestine provides (bullet list)
4. Quick start guide for developers
5. Link to live site
6. How to contribute
7. Data sources list
8. License (MIT for code, CC-BY for data metadata)
9. Contact info

**Mission statement draft:**

> Data Palestine is an open data platform that makes Palestinian statistical and humanitarian data accessible to everyone. We aggregate data from the Palestinian Central Bureau of Statistics, international organizations, and human rights documentation groups into a unified, searchable, API-driven platform. Our goal is to ensure that accurate data about Palestine is findable, accessible, and usable by researchers, journalists, policymakers, and the public. بيانات فلسطين — Because data should be free, accurate, and accessible.
