# Architecture Research

**Domain:** Statistical open data platform — chart rendering and data cleaning pipelines
**Researched:** 2026-03-24
**Confidence:** HIGH (based on direct codebase inspection + established patterns)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       FRONTEND (Next.js 15)                      │
├──────────────────┬──────────────────┬───────────────────────────┤
│  DataExplorer    │  Chart Layer     │  Selection Manager        │
│  (parent state)  │  (pure render)   │  (cap enforcement)        │
│                  │                  │                           │
│  - URL sync      │  - LineChart     │  - MAX_SERIES = 5         │
│  - filter state  │  - BarChart      │  - visible set            │
│  - obs fetch     │  - CustomLegend  │  - toggle/overflow UI     │
└────────┬─────────┴────────┬─────────┴───────────────────────────┘
         │                  │
         │ observations[]   │ seriesNames[] (capped)
         │                  │
┌────────▼──────────────────▼─────────────────────────────────────┐
│                   chartData transform (useMemo)                   │
│  Observation[] → { period, [seriesKey]: value }[]                │
│  seriesNames[] → first 5 (visible) + rest (hidden/badge)         │
└─────────────────────────────────────────────────────────────────┘
         │
         │ REST /api/v1/observations
         │
┌────────▼─────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                               │
│  GET /observations?dataset=X&indicator=1,2,3&geography=PS         │
└────────┬─────────────────────────────────────────────────────────┘
         │
┌────────▼─────────────────────────────────────────────────────────┐
│                  PostgreSQL + TimescaleDB                          │
│  observations (clean values)  indicators (canonical names)        │
└────────┬─────────────────────────────────────────────────────────┘
         │
┌────────▼─────────────────────────────────────────────────────────┐
│                 DATA PIPELINE LAYER (Python scripts)              │
├──────────────────┬──────────────────┬───────────────────────────┤
│  Extractor       │  Normalizer      │  Loader                   │
│  (source-        │  (canonical      │  (upsert with             │
│   specific)      │   names, geo     │   provenance)             │
│                  │   codes, dedup)  │                           │
└──────────────────┴──────────────────┴───────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `DataExplorer` | Parent state, URL sync, data fetching | Single large client component (existing) |
| `ChartContainer` | Chart type routing, empty/loading states | Thin wrapper component, split from DataExplorer |
| `LineChartView` / `BarChartView` | Pure Recharts rendering with bounded series | Isolated presentational components |
| `ChartLegend` | Visible series list + overflow badge | Custom component replacing Recharts Legend |
| `SeriesSelector` | Enforces MAX_SERIES=5, exposes visible/hidden sets | Hook or selector function |
| `IndicatorNormalizer` | Canonical name mapping, deduplication rules | Python module in pipeline layer |
| `GeoTagger` | Geography extraction from indicator names | Python module, standalone from ingest |
| `DatasetConsolidator` | Merge duplicate/redundant datasets | Python module, runs as migration step |

## Recommended Project Structure

### Chart Layer (frontend)

```
apps/web/components/charts/
├── DataChart.tsx          # Route: decides LineChart vs BarChart
├── LineChartView.tsx      # Pure Recharts LineChart, bounded series
├── BarChartView.tsx       # Pure Recharts BarChart, bounded series
├── ChartLegend.tsx        # Custom legend with overflow indicator
├── ChartEmptyState.tsx    # "Select indicators" / "needs 3+ periods" UI
├── Sparkline.tsx          # Existing — server-side SVG, no changes needed
└── BarSparkline.tsx       # Existing — server-side SVG, no changes needed
```

### Data Pipeline Layer (scripts/pipeline)

```
scripts/pipeline/
├── shared/
│   ├── normalizer.py      # Canonical name rules (regex replacements)
│   ├── geo_tagger.py      # Geography extraction + GEO_MAP
│   ├── deduplicator.py    # Indicator/dataset dedup logic
│   └── db.py              # psycopg2 connection helper
├── pcbs/
│   ├── ingest.py          # Raw → staging table
│   └── clean.py           # Staging → clean indicators/observations
├── worldbank/
│   └── ingest.py
└── run_cleanup.py         # Orchestrator: runs normalizer + dedup on DB
```

### Structure Rationale

- **charts/ stays flat:** Each chart type is a separate file so changes to LineChart don't risk BarChart.
- **ChartLegend extracted:** The existing inline `<Legend />` from Recharts cannot be controlled — a custom component is the only way to cap display and show overflow counts.
- **pipeline/shared/ modules:** `normalizer.py`, `geo_tagger.py`, and `deduplicator.py` already exist as logic scattered across archive scripts (`deep_cleanup.py`, `shorten_names.py`, `consolidate_indicators.py`). Consolidating them into `shared/` makes them reusable and testable.

## Architectural Patterns

### Pattern 1: Visible Series Cap with Overflow Badge

**What:** Limit rendered chart series to MAX_SERIES (5), derived from the full selected indicator set. Show a badge: "+8 more — narrow selection to compare."

**When to use:** Whenever the user can select more series than a chart can meaningfully display.

**Trade-offs:** Prevents broken renders immediately; defers a proper multi-indicator UX (grouped comparisons, faceted charts) to Phase 2. Acceptable for MVP.

**Example:**
```typescript
const MAX_CHART_SERIES = 5;

// In DataExplorer or a useSeries() hook:
const visibleSeries = seriesNames.slice(0, MAX_CHART_SERIES);
const overflowCount = Math.max(0, seriesNames.length - MAX_CHART_SERIES);

// Pass to chart:
<LineChartView
  data={chartData}
  series={visibleSeries}
  colors={CHART_COLORS}
/>
{overflowCount > 0 && (
  <p className="text-xs text-neutral-500 mt-1">
    +{overflowCount} more — select fewer indicators to compare
  </p>
)}
```

### Pattern 2: Custom Recharts Legend

**What:** Replace `<Legend />` (which overflows vertically and consumes chart area) with a hand-rolled legend that renders a fixed number of color swatches and truncates long names.

**When to use:** Any Recharts chart showing more than 3 indicators. Recharts' built-in Legend has no max-height or truncation support.

**Trade-offs:** Minor maintenance overhead vs. built-in. Worth it — the built-in is the root cause of the current layout collapse bug.

**Example:**
```typescript
// ChartLegend.tsx
interface ChartLegendProps {
  series: { name: string; color: string }[];
}

export function ChartLegend({ series }: ChartLegendProps) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 px-4 pb-2">
      {series.map(({ name, color }) => (
        <div key={name} className="flex items-center gap-1.5 min-w-0">
          <span
            className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
            style={{ backgroundColor: color }}
          />
          <span
            className="text-[11px] text-neutral-600 truncate"
            style={{ maxWidth: "180px" }}
            title={name}
          >
            {name}
          </span>
        </div>
      ))}
    </div>
  );
}
```

Pass `wrapperStyle={{ position: "relative" }}` and remove `<Legend />` from the Recharts tree entirely. Mount `<ChartLegend />` above the `<ResponsiveContainer>`.

### Pattern 3: Extract-Normalize-Load Pipeline

**What:** Data flows through three discrete, composable stages. Each stage has a single responsibility and can be run independently.

**When to use:** All data source integrations. Normalization must be decoupled from extraction so it can be re-run on existing data without re-fetching from source.

**Trade-offs:** More files than a single script; required for maintainability as more sources are added.

**Example:**
```
1. Extractor: source CSV/API → raw row dicts (no transformation)
2. Normalizer: raw row → canonical IndicatorRecord
   - apply REPLACEMENTS regex list to names
   - apply GEO_MAP to extract geography codes
   - deduplicate against existing indicators
3. Loader: IndicatorRecord → upsert into DB with pipeline_run provenance
```

### Pattern 4: Idempotent Cleanup Migration

**What:** Normalization scripts run against the live database and are safe to run multiple times. They use `--dry-run` flags and produce `(old → new)` change logs before committing.

**When to use:** One-off data quality fixes that transform existing records rather than re-ingesting from source.

**Trade-offs:** Direct DB manipulation risks are mitigated by dry-run mode and transaction rollback on error. This is preferable to re-running full ingest pipelines which may be slow or rate-limited.

## Data Flow

### Chart Render Flow

```
User selects indicators (N)
    ↓
DataExplorer: selectedIndicators[] (all N)
    ↓
fetchObservations() — requests all N, 1000 row cap
    ↓
observations[] → chartData (useMemo) → { period, [seriesKey]: value }[]
    ↓
seriesNames[] = Object.keys(chartData[0]).filter(k => k !== "period")
    ↓
visibleSeries = seriesNames.slice(0, MAX_CHART_SERIES)  ← CAP HERE
    ↓
<LineChartView series={visibleSeries} />
    ↓
<ChartLegend series={visibleSeries} />  ← custom, no overflow
overflowCount > 0 → disclaimer badge
```

### Pipeline Normalization Flow

```
Source (PCBS CSV / World Bank API / B'Tselem)
    ↓
Extractor: raw rows → raw IndicatorRecord[]
    ↓
Normalizer.normalize_name(raw_name)
    - apply REPLACEMENTS regex list
    - trim to ≤ 85 chars at word boundary
    → canonical_name
    ↓
GeoTagger.match_geography(canonical_name)
    - GEO_MAP exact match → (geo_code, remainder)
    - remainder becomes new canonical_name
    → (geo_code, canonical_name)
    ↓
Deduplicator.find_or_create_indicator(dataset_id, canonical_name)
    - exact match on (dataset_id, canonical_name) → reuse existing
    - no match → INSERT new indicator
    → indicator_id
    ↓
Loader.upsert_observation(indicator_id, geo_code, period, value, source_doc_id)
    - ON CONFLICT (indicator_id, geography_code, time_period) DO UPDATE
    → observation record with provenance
```

### Key Data Flows

1. **Auto-select all indicators on dataset change:** DataExplorer fetches dataset detail, calls `setLocalIndicators(allInds)`, then immediately pushes to URL. This triggers the observation fetch. With many indicators this creates the chart overflow problem — the cap must happen at render time, not at fetch time (fetching all is correct for the table view).

2. **Cleanup migration:** `run_cleanup.py` reads all indicators from DB, applies normalization rules, detects changes, and runs UPDATE statements in a transaction. Can be re-run safely. Does not touch observations — only `indicator.name_en` and `dataset.name_en`.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (MVP, small user base) | Monolith is correct. Single DataExplorer component, direct DB cleanup scripts. |
| 1k-10k users | Add observation response caching (FastAPI `functools.lru_cache` or Redis) for hot indicator queries. Chart capping already prevents large data renders client-side. |
| 10k+ users | TimescaleDB compression on observations table. Read replicas for the API. No frontend architecture changes needed. |

### Scaling Priorities

1. **First bottleneck:** `GET /observations` with many indicators and all geographies — already limited to 1000 rows per_page, but the query itself can be slow without a compound index on `(indicator_id, geography_code, time_period)`. Ensure this index exists.
2. **Second bottleneck:** Dataset detail endpoint (fetches all indicators for a dataset) — cache this response server-side; it changes only on pipeline runs.

## Anti-Patterns

### Anti-Pattern 1: Recharts Legend for Multi-Indicator Charts

**What people do:** Leave `<Legend />` as a child of `<LineChart>` with many series.

**Why it's wrong:** Recharts Legend grows vertically without bound. With 10+ series, it consumes the entire chart height. The `<ResponsiveContainer height={400}>` becomes 80% legend, 20% chart — or the chart disappears entirely. This is the current bug.

**Do this instead:** Remove `<Legend />` from the Recharts tree. Render `<ChartLegend />` as a separate sibling above `<ResponsiveContainer>`. Cap visible series at 5 before constructing the Recharts `<Line>` or `<Bar>` elements.

### Anti-Pattern 2: Normalization Logic Duplicated Across Pipeline Scripts

**What people do:** Each pipeline script (`pcbs/`, `worldbank/`, `btselem/`) contains its own copy of name-cleaning regexes and geography mapping.

**Why it's wrong:** When a rule changes (e.g., a new governorate spelling variant), it must be updated in N places. The archive scripts show this already happening — `GEO_MAP` and `REPLACEMENTS` are duplicated.

**Do this instead:** Centralize in `scripts/pipeline/shared/normalizer.py` and `geo_tagger.py`. Import from there in every pipeline. Run `normalizer.py` as a post-ingest step that can also be run standalone.

### Anti-Pattern 3: Indicator Naming Inherited from Source

**What people do:** Store the raw source string as the indicator name (e.g., `"Bethlehem"` where the indicator is actually "Criminal Offenses in Bethlehem").

**Why it's wrong:** The name means nothing without the dataset context. It pollutes the indicator list in the Explorer with single-word entries that are useless when shown alongside other datasets.

**Do this instead:** The `consolidate_indicators.py` script has the right approach — detect when indicators are geography names, create one canonical indicator (named from the dataset title), retag observations to that indicator with the correct geography code, and delete the per-geography indicator rows.

### Anti-Pattern 4: Fetching Fewer Observations to Work Around Chart Overflow

**What people do:** Limit the observation fetch to `per_page=5` (matching the chart cap) when in chart view.

**Why it's wrong:** The table view needs all observations. The chart cap is a rendering concern, not a data concern. Changing the fetch based on the active tab creates inconsistency and breaks "show as table" after switching views.

**Do this instead:** Always fetch all observations for the selected filters (up to the 1000-row cap). Apply the `MAX_CHART_SERIES` slice at the `seriesNames` computation step, not at the API call level.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Recharts | Direct import via `dynamic()` (existing) | Keep SSR:false pattern — Recharts uses browser APIs. Splitting into sub-components doesn't change this requirement. |
| PostgreSQL | asyncpg via SQLAlchemy (existing) | Cleanup scripts use psycopg2 (sync) — this is intentional for one-off scripts, not a problem. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `DataExplorer` ↔ `ChartContainer` | Props: `observations[]`, `seriesNames[]`, `activeTab`, `locale` | ChartContainer should be pure — no state, no fetching. DataExplorer owns all state. |
| `DataExplorer` ↔ `ChartLegend` | Props: `series: {name, color}[]`, `overflowCount: number` | Legend is display-only. Hover/highlight interactions are Phase 2. |
| Pipeline scripts ↔ shared normalizer | Python module import | `from shared.normalizer import normalize_name, REPLACEMENTS` |
| Cleanup script ↔ database | Direct psycopg2, wrapped in transaction with `--dry-run` | Always dry-run first. Always log `(old_name → new_name)` before commit. |

## Build Order Implications

The chart fix and data cleanup are independent work streams that can proceed in parallel, but the chart fix should ship first:

1. **Chart fix (immediate):** `ChartLegend.tsx` + cap logic in DataExplorer. No pipeline work needed. Unblocks the platform from looking broken.
2. **Data cleanup (post-chart-fix):** Consolidate `shared/normalizer.py` from archive scripts, run cleanup migration. Improves indicator names visible in the Explorer left panel.
3. **Chart styling (after both above):** Once charts render correctly and indicator names are clean, professional styling (axis formatting, gridlines, typography) makes sense. Styling broken charts wastes effort.

## Sources

- Direct inspection of `/apps/web/components/data/DataExplorer.tsx` (the existing chart rendering code)
- Direct inspection of `/apps/web/components/charts/Sparkline.tsx` (existing SVG chart pattern)
- Direct inspection of `/scripts/archive/deep_cleanup.py`, `consolidate_indicators.py`, `shorten_names.py` (existing normalization logic)
- Direct inspection of `/apps/api/app/models/indicator.py`, `observation.py` (data model)
- Recharts documentation: known issue with `<Legend />` height overflow in bounded containers (MEDIUM confidence — consistent with observable behavior in the codebase)

---
*Architecture research for: Data Palestine — chart rendering and data cleaning pipelines*
*Researched: 2026-03-24*
