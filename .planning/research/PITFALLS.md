# Pitfalls Research

**Domain:** Open data platform — chart rendering and statistical data cleanup
**Researched:** 2026-03-24
**Confidence:** HIGH (chart pitfalls confirmed by Recharts issue tracker + UX literature; data quality pitfalls confirmed by direct codebase inspection)

---

## Critical Pitfalls

### Pitfall 1: Recharts Legend Consumes All Vertical Space When Series Count Is Uncapped

**What goes wrong:**
When 10+ series are passed to a Recharts `LineChart` or `BarChart`, the horizontal legend wraps onto multiple rows. Recharts calculates available chart height by subtracting the rendered legend height — but it does this in a two-pass render. On the first pass, the legend height is zero. On the second pass, the legend has grown to fill available space. The net result is a chart container with near-zero height: the legend renders, the chart area does not. This is the exact bug already observed in the Data Explorer.

**Why it happens:**
The current `DataExplorer.tsx` auto-selects ALL indicators when a dataset is chosen and passes all of them to `seriesNames` without capping. Some PCBS datasets have 30–80 indicators. The `ResponsiveContainer` + `Legend` interaction in Recharts has been a known issue since at least 2019 (GitHub issues #671, #1198, #2636) and is not fully resolved in the library.

**How to avoid:**
Cap the visible series passed to the chart at 5. Do NOT pass all `seriesNames` to the chart — only pass `seriesNames.slice(0, MAX_VISIBLE_SERIES)`. Let users toggle which 5 are visible using a separate legend UI outside the chart. Alternatively, render the `Legend` outside the `ResponsiveContainer` entirely with a fixed pixel height reserved for it above the chart.

**Warning signs:**
- Chart area height collapses to 0–20px on dataset selection
- Legend renders correctly but no lines/bars appear
- The issue appears only after selecting a dataset with many indicators, not on initial load

**Phase to address:** Chart fix milestone (current) — this is the primary known bug to fix

---

### Pitfall 2: Indicator Deduplication That Destroys Provenance

**What goes wrong:**
When cleaning up duplicate or near-duplicate indicator names (e.g., PCBS `GDP at Current Prices` vs World Bank `GDP (current USD)`), the temptation is to merge them into a single indicator record. This silently discards source attribution — observations that originally pointed to PCBS are now indistinguishable from World Bank observations in queries. The platform's "every data point traces back to its original source" constraint is violated.

**Why it happens:**
Cleanup scripts that run `UPDATE indicators SET name_en = 'X'` across source boundaries, or that merge observations under a single indicator ID, collapse provenance. The scripts in `scripts/archive/` (e.g., `consolidate_indicators.py`, `deep_cleanup.py`) suggest this pattern has already been attempted.

**How to avoid:**
Never merge observations across source boundaries. Deduplication operates on display names, not on database identity. Each source's indicator keeps its own `id` and `dataset_id`. Use a `canonical_name` or `display_group` column to group related indicators for UI display — keep the raw `name_en` for audit trails. Cleanup = rename + group, not merge + delete.

**Warning signs:**
- A cleanup script runs UPDATE on `indicators.name_en` across multiple `dataset_id` values
- An observation's `source_document_id` becomes NULL after a cleanup run
- Source attribution panel on the frontend shows the wrong organization after cleanup

**Phase to address:** Data cleanup milestone (post-MVP)

---

### Pitfall 3: Mixed Units on a Single Y-Axis

**What goes wrong:**
Users select multiple indicators with different units (e.g., "GDP in USD billions" and "Unemployment rate %") and the chart plots them on a shared Y-axis. A GDP value of 14,000 and an unemployment rate of 8.5 on the same axis produces either a flat unemployment line barely visible near zero, or a completely meaningless scale. This actively misleads readers — a core violation of the platform's "never editorialize / never mislead" principle.

**Why it happens:**
The current chart implementation in `DataExplorer.tsx` builds a single shared Y-axis for all series with no unit-awareness. When the multi-indicator selection is uncapped (see Pitfall 1), different-unit series will inevitably be co-plotted.

**How to avoid:**
- When indicators with different `unit_symbol` values are selected together, either: (a) refuse to chart them on the same axis and show a clear warning, or (b) normalize to percentage change (indexed) — make this opt-in, not default.
- As part of the 5-indicator cap, add a unit-mismatch warning when selected indicators have different `unit_symbol` values.
- Best practice from institutional data portals (World Bank, OCHA): segregate charts by unit, or use the indexed/normalized view as the default for multi-indicator comparison.

**Warning signs:**
- A user selects GDP + unemployment rate and the chart shows one flat line near zero
- The Y-axis label shows no unit or a concatenated "USD / %" string
- Dual-axis approach is added without explicit UX guidance that the axes are independent

**Phase to address:** Chart fix milestone (current)

---

### Pitfall 4: Indicator Rename Without a Migration Guard Leaves Stale URL State

**What goes wrong:**
Data Explorer state is stored in URL params (`?indicators=42,87,103`). After a data cleanup run renames or renumbers indicators, shared links break silently — the URL resolves to zero results instead of an error. Users who bookmarked a query get an empty chart with no explanation.

**Why it happens:**
Indicator IDs in the current schema are auto-increment integers (`id: Mapped[int] = mapped_column(Integer, primary_key=True)`). If cleanup scripts delete and re-insert indicators (common in `reingest_pcbs.py`, `seed_db.py` patterns), IDs shift. Even if IDs are stable, if an indicator is removed from a dataset, the API returns 0 observations for that ID without indicating it no longer exists.

**How to avoid:**
- Never delete-and-reinsert indicators during cleanup — update in place.
- Add a `deprecated_at` timestamp column to indicators. When an indicator is removed, mark it deprecated rather than deleting it. The API can return a 410 Gone response for deprecated indicator IDs.
- During cleanup runs, log old-ID → new-ID mappings if any IDs change.

**Warning signs:**
- A data cleanup run shows "0 records inserted, N records skipped" for indicators that previously had data
- The explore page loads with `?indicators=42` but shows "No results" with no error
- Indicator count in the dataset detail API response drops after a pipeline run

**Phase to address:** Data cleanup milestone (post-MVP)

---

### Pitfall 5: PCBS CSV Pattern Detection Fails Silently on New File Formats

**What goes wrong:**
`pcbs/csv_parser.py` detects one of 9 patterns for PCBS CSV files. When PCBS publishes a new file with a slightly different header format, the pattern detector falls through to a default or returns empty observations. The pipeline run completes with status "success", records_processed=N, records_inserted=0 — and the data gap is invisible to the platform's users.

**Why it happens:**
PCBS reformats their CSV exports periodically without notice. The parser's `PATTERNS` list is a closed enum. The pipeline run logger tracks counts but does not alert on "high skipped ratio" conditions.

**How to avoid:**
- Add an assertion in the pipeline: if `records_inserted / records_processed < 0.5`, set pipeline run status to "warning" and log which file triggered the issue.
- Log the detected pattern per file in the pipeline run metadata JSONB column.
- Write a test that runs the parser against a representative file from each known pattern and asserts at least one observation is returned.

**Warning signs:**
- `pipeline_runs` table shows `records_processed=200, records_inserted=0` for a PCBS pipeline run
- The most recent observation `time_period` for a PCBS indicator is 12+ months old
- A new PCBS CSV file is added to the discovery JSON but never appears in the DB

**Phase to address:** Data cleanup milestone (post-MVP) — but the assertion guard should be added now

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Auto-select all indicators on dataset load | Users immediately see data | Triggers chart rendering bug; URL becomes unwieldy with 80 indicator IDs | Never — replace with smart default (top 3 by sort_order) |
| Each recharts primitive imported via individual `dynamic()` calls | Avoids SSR errors | 10+ separate dynamic imports; increases hydration complexity and bundle waterfall | MVP only — consolidate into a single `dynamic(() => import('./ChartWrapper'))` |
| Integer auto-increment IDs for indicators | Simple schema | ID collisions if data is re-seeded; brittle URL state | Only if delete-and-reinsert is never done during cleanup |
| Storing indicator names as raw PCBS export strings | Easy ingestion | Unusable for display; names like `"% Change  Monthly" - Unnamed: 3_level_1` appear in the UI | Never for production — raw names must be cleaned before insert |
| Overflow: hidden on the explore page body | Prevents double scrollbars | Any content taller than viewport is inaccessible; modal/tooltip content may clip | MVP only — fix when left panel is redesigned |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Recharts + ResponsiveContainer | Wrapping in a container with `height: 100%` and no explicit pixel height set on the parent | Give the parent a known pixel height (e.g., `calc(100vh - 350px)`) before ResponsiveContainer resolves |
| Recharts Legend | Placing `<Legend />` inside the chart SVG for many-series datasets | Render a custom legend as a separate div outside the chart; pass `legend={false}` to the chart |
| PCBS CSV discovery | Treating the discovery JSON as stable — re-running discovery overwrites it | Treat the discovery JSON as append-only; new entries are added, existing entries are not modified |
| World Bank API | Fetching all indicators for country `PS` in one request | The API paginates at 32,000 records; use `per_page=32000&mrv=20` params and check `pages` in response |
| next-intl + "use client" DataExplorer | Translation strings passed as props from Server Component to Client Component must be fully resolved | Never pass the `t()` function itself — pass the resolved string object; otherwise hydration fails |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Fetching 1,000 observations client-side then building chart data in `useMemo` | Page feels slow; JS thread blocks on large datasets | Server-side aggregation: API should return pre-pivoted chart data for chart view, not raw observation rows | At ~500 observations (PCBS datasets can have 800+) |
| URL-encoded indicator list exceeds browser URL length limit | Navigation silently truncates the URL; some indicators drop from the query | Cap indicators in URL at 5; store larger selections in session state | At ~50 indicator IDs in the URL (around 200 chars) |
| `seriesNames` derived from `chartData` keys via `Object.keys` on every render | Causes chart key flicker and re-animation on every filter change | Derive `seriesNames` from the indicator list, not from chart data keys | Immediately visible on any dataset with 5+ indicators |
| Re-fetching all datasets on every locale change | Datasets list refetches on language switch | Cache dataset list; only refetch when locale-specific name fields are needed | Harmless at <100 datasets, annoying at 500+ |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No visual indication that chart is capped at 5 series | Users don't know they're not seeing all data | Show "Showing 5 of N indicators" badge above chart; provide a selector for which 5 |
| Raw indicator names from PCBS source files displayed in the left panel | Names like `"Unnamed: 3_level_1"` or `"% Change  Monthly"` erode trust in data quality | Display `name_en` after cleanup; show a "data under review" badge for uncleaned datasets |
| Chart renders immediately on dataset selection (auto-apply) without user intent | First load shows a broken or confusing chart for datasets with many indicators | Auto-select 3 indicators by `sort_order`; require user to hit "Apply" for additional selections |
| Development disclaimer placed inside the chart area | Users skip it; disclaimer text sits in chart whitespace | Place the disclaimer as a dismissible banner at the top of the explore page, styled distinctly from data |
| Color palette is not colorblind-safe for 8 colors | ~8% of users cannot distinguish red/green series | Replace `#C62828` (red) in the chart palette with `#EF6C00` (orange); use Okabe-Ito ordering |

---

## "Looks Done But Isn't" Checklist

- [ ] **Chart cap at 5:** Indicator list is capped but chart still receives all series via `seriesNames` — verify `seriesNames.length <= 5` in all code paths
- [ ] **Legend fix:** Legend renders visibly but the chart area still collapses to near-zero height — verify chart wrapper div has a minimum pixel height independent of legend
- [ ] **Data cleanup:** Indicator display names look clean in the UI but raw names survive in `name_en` DB column — verify with a direct DB query, not just visual inspection
- [ ] **Provenance after cleanup:** Data looks correct post-cleanup but source attribution links are broken — verify every observation has a non-null `source_document_id` after any cleanup run
- [ ] **Bilingual chart labels:** English chart works correctly but Arabic locale shows LTR axis labels on an RTL page — verify X-axis label direction and tooltip positioning in `dir="rtl"` context
- [ ] **Export after cap:** Chart shows 5 series but CSV export still exports all 80 indicators — verify export respects the active filter state, not the full indicator list

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Legend takeover breaks chart | LOW | Add `seriesNames.slice(0, 5)` cap + fixed-height chart wrapper; no data changes needed |
| Observations merged across source boundaries during cleanup | HIGH | Restore from backup; re-run source-specific pipelines; re-validate source attribution |
| Indicator IDs shifted after re-seed | MEDIUM | Write a migration script mapping old → new IDs; update any cached/bookmarked URLs in docs |
| PCBS pattern detector silently drops data | MEDIUM | Identify which files were affected via pipeline run logs; re-run parser with new pattern; backfill observations |
| RTL axis direction wrong in Arabic locale | LOW | Recharts does not have native RTL; workaround: use `reversed={locale === "ar"}` on XAxis and mirror tooltip position |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Legend consumes chart area (Pitfall 1) | Chart fix milestone (current) | Chart renders with height > 200px when 10+ indicators are in the dataset |
| Mixed units on single Y-axis (Pitfall 3) | Chart fix milestone (current) | Selecting GDP + unemployment rate shows a warning, not a broken chart |
| Stale URL state after indicator rename (Pitfall 4) | Data cleanup milestone | Bookmarked URLs still resolve after a full cleanup pipeline run |
| Indicator deduplication destroys provenance (Pitfall 2) | Data cleanup milestone | Every observation has a non-null `source_document_id`; source panel shows correct org |
| PCBS pattern detector silent failures (Pitfall 5) | Data cleanup milestone | Pipeline runs with >50% skip rate set status to "warning" not "success" |
| Mixed indicator names in display (UX Pitfall) | Data cleanup milestone | No indicator name contains "Unnamed", "level_", or double spaces |

---

## Sources

- Recharts GitHub issues: #671 (legend height), #1198 (height consistency), #2636 (ResponsiveContainer + legend overlap), #682 (RTL stacked bar) — confirmed existing bugs, not fixed as of 2025
- Datawrapper blog: "Why not to use two axes" — dual-axis misleading visualization patterns
- ONS Digital blog: "Dueling with axis: the problems with dual axis charts"
- Metabase blog: "Your chart has too many series" — UX guidance on series caps
- Codebase inspection: `apps/web/components/data/DataExplorer.tsx` lines 191-209 (auto-select all indicators), lines 375-384 (seriesNames from chartData keys)
- Codebase inspection: `packages/pipeline/pcbs/csv_parser.py` (9-pattern detector, no skip-rate alerting)
- Codebase inspection: `apps/api/app/models/indicator.py` (integer PK, no deprecated_at column)
- Codebase inspection: `scripts/archive/` directory (consolidate_indicators.py, deep_cleanup.py — prior merge attempts)
- Okabe-Ito colorblind-safe 8-color palette — Color Universal Design standard for categorical charts

---
*Pitfalls research for: Data Palestine — chart rendering and data cleanup*
*Researched: 2026-03-24*
