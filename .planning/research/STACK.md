# Stack Research

**Domain:** Institutional open data platform — chart styling and data cleanup
**Researched:** 2026-03-24
**Confidence:** HIGH (core Recharts/library findings verified via official sources and npm; data tools verified via PyPI)

## Context

This is a brownfield milestone on an existing platform (Next.js 15 + Recharts 3.8 + FastAPI + PostgreSQL/TimescaleDB + Python pipelines). No stack replacements. This research covers two focused problems:

1. Making Recharts charts professional and institutional-quality (World Bank / UN OCHA tier)
2. Best practices for statistical data cleanup in the existing pipeline architecture

---

## Recommended Stack

### Core Technologies (already in use — confirming correct choices)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Recharts | 3.8.0 | Chart rendering | Correct choice for this stack. Built on D3, SVG-native, React composable. v3.8 adds `niceTicks`, `labelStyle` on Legend, and new coordinate hooks. Do not replace — the existing investment is sound. |
| pandas | 2.2+ | DataFrame transformations in pipelines | Correct choice. All existing pipelines already use it. Mature, well-documented. Polars is faster but migration cost is not justified for this dataset scale. |

### Supporting Libraries — Chart Improvements (new additions)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none needed) | — | Chart styling is done via Recharts props + CSS, not a new library | See configuration patterns below — do not add dependencies for chart styling |

### Supporting Libraries — Data Cleanup (new additions to pipeline)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandera | 0.30.1 | Schema validation and statistical checks on DataFrames | Add to the `transform()` stage of every pipeline. Define a `DataFrameSchema` per dataset that asserts column types, value ranges, and non-null constraints. Fails loudly with clear error messages before bad data reaches the DB. |
| pyjanitor | 0.32.20 | Chainable pandas cleaning utilities (`clean_names`, `remove_empty`, `collapse_levels`) | Use in `transform()` for PCBS data specifically. `clean_names()` normalizes column headers to snake_case, stripping accents and special characters. Eliminates custom normalization code. |
| rapidfuzz | 3.14.3 | Fuzzy string deduplication for indicator names | Use in a one-time data audit script and ongoing deduplication checks. `rapidfuzz.process.dedupe()` identifies near-duplicate indicator names (e.g., "Unemployment Rate %" vs "unemployment rate (%)"). MIT licensed — use instead of TheFuzz (GPL). |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Biome (already installed) | Lint/format frontend code | Already in devDependencies. No change needed. |
| ruff (already installed) | Python lint/format | Already in pipeline pyproject.toml. No change needed. |
| pytest (already installed) | Pipeline tests | Already configured. Add pandera schema validation assertions to existing test suite. |

---

## Recharts Configuration Patterns for Institutional Quality

Recharts does not need additional libraries to look professional. The gap between "basic" and "institutional" is entirely configuration. These are the specific patterns to apply.

### Pattern 1: Constrain indicator count and fail gracefully

The root cause of the chart breakage is that `selectedIndicators` is auto-set to ALL indicators, then passed to Recharts with no cap. The legend then consumes the entire chart area.

**Fix:** Cap visible series at 5 in the chart render, distinct from the data selection. The user selects what they want in the left panel; the chart shows the first 5 with a "showing 5 of N" notice.

```tsx
const MAX_CHART_SERIES = 5;
const chartIndicators = selectedIndicators.slice(0, MAX_CHART_SERIES);
const hiddenCount = selectedIndicators.length - MAX_CHART_SERIES;
```

### Pattern 2: Custom Legend with fixed height and overflow control

The built-in `<Legend />` expands vertically and can consume the entire chart. Use `wrapperStyle` to fix its height and clip overflow, or implement a custom legend with the `content` prop.

```tsx
<Legend
  verticalAlign="bottom"
  height={40}
  wrapperStyle={{
    paddingTop: "12px",
    fontSize: "11px",
    overflowX: "auto",
    overflowY: "hidden",
    whiteSpace: "nowrap",
  }}
  iconType="circle"
  iconSize={8}
/>
```

For more than 5 series: use the `content` prop to render a custom component that is scrollable horizontally and shows truncated names with full name in a `title` attribute.

### Pattern 3: Professional axis styling (World Bank tier)

```tsx
<XAxis
  dataKey="period"
  tick={{ fontSize: 11, fill: "#757575", fontFamily: "inherit" }}
  tickLine={false}
  axisLine={{ stroke: "#E0E0E0" }}
  tickMargin={8}
/>
<YAxis
  tick={{ fontSize: 11, fill: "#757575", fontFamily: "inherit" }}
  tickLine={false}
  axisLine={false}
  tickFormatter={(v) => formatAxisValue(v)}  // see Pattern 5
  width={56}
/>
```

Key decisions: no tick lines on X or Y (cleaner), no left axis line (use grid only), subtle `#E0E0E0` bottom axis line, small `#757575` secondary-text-colored tick labels.

### Pattern 4: Professional grid and chart margin

```tsx
<CartesianGrid
  strokeDasharray="3 3"
  stroke="#E0E0E0"
  vertical={false}
/>

<LineChart
  data={chartData}
  margin={{ top: 8, right: 16, bottom: 4, left: 0 }}
>
```

Horizontal-only grid lines (`vertical={false}`) match World Bank DataBank and OCHA HDX chart aesthetics. Top margin 8px prevents line clipping.

### Pattern 5: Axis tick number formatting

The existing `formatValue()` in DataExplorer handles tooltip values but is not wired to axis ticks. A separate lighter formatter for axis ticks:

```tsx
function formatAxisValue(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
  if (abs < 1 && abs > 0) return v.toFixed(2);
  return v.toLocaleString("en-US", { maximumFractionDigits: 0 });
}
```

Pass as `tickFormatter={formatAxisValue}` on YAxis. This prevents tick labels like "1234567" overflowing the chart area.

### Pattern 6: Professional custom tooltip

The default Recharts tooltip has a visible border and generic styling. Replace with a custom content component:

```tsx
<Tooltip
  content={<CustomTooltip indicators={chartIndicators} colors={CHART_COLORS} />}
  cursor={{ stroke: "#E0E0E0", strokeWidth: 1 }}
/>
```

Custom tooltip design: white background, `1px solid #E0E0E0` border, `4px` border-radius, `11px` font, `#212121` text, listed series values with colored dots, period label in `#757575`. No shadows — cleaner on light institutional backgrounds.

### Pattern 7: Recharts 3.8 `niceTicks` prop

In v3.8, the `niceTicks` prop on `YAxis` can be set to `"nice"` for human-readable tick values (avoids awkward values like 12,347). This replaces the need for a custom domain prop in most cases.

```tsx
<YAxis niceTicks="nice" />
```

Verified: released in v3.8.0 (March 6, 2026).

### Pattern 8: Responsive chart height that does not fight the legend

When using `ResponsiveContainer`, the legend height is not subtracted from the chart height, causing overlap when re-rendering. The fix is to set an explicit pixel height on `ResponsiveContainer` rather than `height="100%"`:

```tsx
<ResponsiveContainer width="100%" height={320}>
```

Or use the new `responsive` prop added in Recharts v3.8 directly on `LineChart`/`BarChart`, which eliminates the need for `ResponsiveContainer` entirely:

```tsx
<LineChart responsive height={320} width={600} data={chartData}>
```

This prevents the re-render overlap bug (GitHub issue #2636).

---

## Data Cleanup Pipeline Patterns

### Pattern 1: Pandera schema per dataset

Every dataset should define a `DataFrameSchema` that the `transform()` stage validates against before `load()` is called. This provides a compile-time contract on what "clean" means for each dataset.

```python
import pandera as pa

population_schema = pa.DataFrameSchema({
    "indicator_code": pa.Column(str, nullable=False),
    "indicator_name": pa.Column(str, nullable=False),
    "geography_code": pa.Column(str, pa.Check.str_matches(r"^PS-")),
    "period": pa.Column(str, nullable=False),
    "value": pa.Column(float, pa.Check.greater_than_or_equal_to(0)),
    "unit": pa.Column(str, nullable=True),
})

# In BasePipeline.transform():
validated_df = population_schema.validate(df)
```

Pandera raises `SchemaError` with the offending row on failure — the pipeline should catch this and write to the pipeline run log before re-raising.

### Pattern 2: Indicator name normalization with pyjanitor + custom rules

PCBS data has indicator names like "Unemployment Rate (%)", "unemployment rate (%)", "Unemployment rate- Total", "Unempl. Rate (%)". The `transform()` stage must normalize these before load.

```python
import janitor

def normalize_indicator_names(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df
        .clean_names(strip_accents=True, remove_special=True)  # snake_case headers
        .transform_column(
            "indicator_name",
            lambda s: s.strip().lower()
                .replace("  ", " ")
                .replace("- ", " ")
                .replace("_", " ")
                .title()
        )
    )
```

pyjanitor's `clean_names()` operates on column headers (making them snake_case), not values. Use `.transform_column()` for cell-level normalization.

### Pattern 3: Fuzzy deduplication audit script (one-time + periodic)

A standalone script (not in the load pipeline) to identify near-duplicate indicator names in the database for human review:

```python
from rapidfuzz import process, fuzz

def find_duplicate_indicators(names: list[str], threshold: int = 85) -> list[tuple]:
    """Returns pairs of indicator names with similarity >= threshold."""
    dupes = []
    for i, name in enumerate(names):
        matches = process.extract(name, names[i+1:], scorer=fuzz.token_sort_ratio)
        for match, score, _ in matches:
            if score >= threshold:
                dupes.append((name, match, score))
    return dupes
```

Run this after each major data ingestion cycle. Output to a CSV for human review. Do not auto-merge — a human decides which name is canonical.

### Pattern 4: Idempotent value cleaning

The existing `BasePipeline` contract requires idempotent pipelines. Data cleaning must also be idempotent — running it twice on the same source produces the same result. Rules:

- Strip whitespace from all string columns
- Cast numeric strings to float (handle "N/A", "-", "", "..." as `None`)
- Normalize percentage values: if unit is "%" and value is 0–100, do not divide by 100

```python
def coerce_numeric(val) -> float | None:
    if pd.isna(val):
        return None
    s = str(val).strip().replace(",", "").replace("%", "")
    if s in ("", "-", "N/A", "...", "—"):
        return None
    try:
        return float(s)
    except ValueError:
        return None
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Recharts (keep) | Nivo, Victory, Chart.js | Only if switching to server-side SVG rendering or if Recharts v3 breaks unexpectedly. Nivo has better out-of-box aesthetics but larger bundle. Not worth migrating. |
| pandera | Great Expectations | Great Expectations when you need shareable "expectation suites" across a team, multi-engine pipelines (Spark + pandas), or generated HTML data quality reports for stakeholders. For a solo/small team pipeline like this, pandera is lighter and faster to iterate. |
| rapidfuzz | TheFuzz (fuzzywuzzy) | Never — TheFuzz is GPL licensed (incompatible with MIT), 10-100x slower, and is superseded by rapidfuzz (from the same original author). |
| pyjanitor | Custom cleaning functions | If the project outgrows pyjanitor or needs more complex reshaping. For the current PCBS data volume, pyjanitor is sufficient and avoids reinventing `clean_names`. |
| pandas (keep) | Polars | Polars if data volumes exceed ~10M rows per pipeline run. At current PCBS/World Bank scale (tens of thousands of rows), pandas is adequate and avoids a migration. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Highcharts | Commercial license, incompatible with open-source nonprofit platform | Recharts (already in use, MIT licensed) |
| TheFuzz / fuzzywuzzy | GPL license, slow, deprecated in favor of rapidfuzz | rapidfuzz 3.14.3 |
| Great Expectations (for this use case) | Heavyweight — requires a GX Cloud or local metadata store, generates HTML reports, takes 5-10 minutes to configure per dataset. Overkill for a 6-table pipeline. | pandera (schema-as-code, no infrastructure) |
| D3 directly | Would require significant custom code for a React component. Recharts already wraps D3 correctly for this use case. | Recharts composable components |
| Upgrading `dynamic()` imports for Recharts | The current pattern of per-component `dynamic()` imports (LineChart, Bar, XAxis, etc.) avoids SSR issues but creates many lazy chunks. In Recharts v3.8, the `responsive` prop on chart components removes the need for `dynamic(ResponsiveContainer)`. The other imports can be consolidated into a single `dynamic(() => import('recharts').then(...))`. | Single barrel dynamic import |

---

## Stack Patterns by Variant

**If adding more than 5 indicators to a chart view:**
- Use a custom `content` prop on `<Legend>` that renders a horizontally scrollable pill list
- Each pill shows a color dot + truncated name (max 20 chars) with full name in `title` attribute
- Do not let Recharts auto-size the legend height

**If PCBS data volume grows beyond current scale:**
- Swap pandas for Polars in extract/transform stages (pandera supports Polars natively from v0.20+)
- Keep load stage in SQLAlchemy/pandas for ORM compatibility

**If multi-language indicator names are needed:**
- Store canonical English and Arabic names in the `indicators` table
- The cleanup pipeline normalizes English names; Arabic names are a separate manual mapping exercise

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| recharts@3.8.0 | react@19, next@15 | HIGH confidence. Recharts 3.x is React 18/19 compatible. SSR via `dynamic()` is required (already in place). |
| pandera@0.30.1 | pandas@2.2+ | HIGH confidence. Verified via PyPI. |
| pyjanitor@0.32.20 | pandas@2.2+ | HIGH confidence. Verified via PyPI. |
| rapidfuzz@3.14.3 | Python 3.12+ | HIGH confidence. Verified via PyPI. Pure cleanup script — no web or API dependency. |
| recharts@3.8 `responsive` prop | next@15 SSR | MEDIUM confidence. The `responsive` prop is new in 3.8.0 (March 2026). It may still require a `"use client"` boundary. Keep current `dynamic()` pattern for SSR safety until tested. |

---

## Sources

- [recharts/recharts releases (GitHub)](https://github.com/recharts/recharts/releases) — v3.8.0 feature list (niceTicks, responsive prop, labelStyle, coordinate hooks)
- [Recharts customize guide](https://recharts.github.io/en-US/guide/customize/) — SVG styling, tooltip/legend customization approach
- [shadcn/ui chart docs](https://ui.shadcn.com/docs/components/chart) — CSS variable approach and ChartContainer pattern (reference only, not adopting)
- [pandera PyPI](https://pypi.org/project/pandera/) — version 0.30.1 confirmed, March 18 2026
- [pyjanitor PyPI](https://pypi.org/project/pyjanitor/) — version 0.32.20 confirmed, February 18 2026
- [rapidfuzz PyPI](https://pypi.org/project/rapidfuzz/) — version 3.14.3 confirmed, November 2025
- [Data validation landscape 2025](https://aeturrell.com/blog/posts/the-data-validation-landscape-in-2025/) — pandera vs GX comparison
- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) — MIT license confirmed, TheFuzz comparison
- [Recharts legend overlap issue #2636](https://github.com/recharts/recharts/issues/2636) — ResponsiveContainer legend re-render bug pattern

---
*Stack research for: Data Palestine — chart improvements and data cleanup milestone*
*Researched: 2026-03-24*
