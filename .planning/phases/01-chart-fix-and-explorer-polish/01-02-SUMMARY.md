---
phase: 01-chart-fix-and-explorer-polish
plan: "02"
subsystem: frontend-charts
tags: [charts, recharts, data-explorer, disclaimer, integration, rtl]
dependency_graph:
  requires:
    - 01-01 (LineChartView, BarChartView, ExplorerDisclaimer, constants)
  provides:
    - DataExplorer wired with LineChartView and BarChartView components
    - Series cap enforcement (MAX_CHART_SERIES=5) in DataExplorer
    - Overflow badge showing "Showing 5 of N indicators"
    - Source attribution below charts
    - ExplorerDisclaimer banner wired into explorer render tree
    - Auto-select first 3 indicators (not all) on dataset load
    - Arabic dataset select with dir="rtl"
    - Polished ExplorerDisclaimer with gradient, info icon, rounded close button
  affects:
    - apps/web/app/[locale]/explore/page.tsx (added translation keys)
tech_stack:
  added: []
  patterns:
    - Import chart views as static components (not inline Recharts dynamic imports)
    - Pass visibleSeries (capped slice) to chart components
    - Source attribution via datasetDetail.source.organization
    - dir attribute on select elements for RTL locale
key_files:
  created: []
  modified:
    - apps/web/components/data/DataExplorer.tsx
    - apps/web/components/data/ExplorerDisclaimer.tsx
    - apps/web/app/[locale]/explore/page.tsx
    - apps/web/components/charts/BarChartView.tsx
    - apps/web/components/charts/LineChartView.tsx
decisions:
  - Use datasetDetail.source.organization for source attribution (plan specified source_name which does not exist on DatasetDetail type)
  - TooltipContentProps instead of TooltipProps for Recharts v3 custom tooltip (payload property moved)
  - Arabic select dir="rtl" applied at element level not wrapper div
  - ExplorerDisclaimer gradient redesign keeps no additional library dependency (SVG icon inline)
requirements-completed: [CHART-01, CHART-02, CHART-03, UX-01, UX-02]
metrics:
  duration: ~30 minutes
  completed: "2026-03-24"
  tasks: 2 of 2 (complete — checkpoint approved)
  files: 5
---

# Phase 01 Plan 02: DataExplorer Integration Summary

**DataExplorer refactored to use LineChartView/BarChartView with 5-series cap, dismissible ExplorerDisclaimer banner, source attribution, first-3 auto-select, and Arabic RTL dropdown — verified by human in both English and Arabic**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-03-24T22:00:00Z
- **Completed:** 2026-03-24T22:47:00Z
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint, approved with minor fixes)
- **Files modified:** 5

## What Was Built

Task 1 integrated all components created in Plan 01 into DataExplorer.tsx:

1. **Replaced inline Recharts rendering** — All direct Recharts dynamic imports (LineChart, BarChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer) removed from DataExplorer.tsx. Charts are now rendered via `<LineChartView>` and `<BarChartView>`.

2. **Series cap enforced** — `visibleSeries = seriesNames.slice(0, MAX_CHART_SERIES)` computed and passed to chart views. Chart components only see max 5 series.

3. **Overflow badge** — When `seriesNames.length > MAX_CHART_SERIES`, a badge renders above the chart: "Showing 5 of N indicators — select fewer to compare all" (bilingual).

4. **Source attribution** — Below each chart, `datasetDetail.source.organization` renders as "Source: [org]" (bilingual).

5. **Auto-select changed** — `detail.data.indicators.slice(0, 3).map(...)` replaces the prior all-indicator auto-select. First 3 indicators load by default.

6. **ExplorerDisclaimer wired** — Banner renders in a `shrink-0 mb-3` div before the tab bar in the main column.

7. **CHART_COLORS removed inline** — Imported from `@/lib/constants` alongside `MAX_CHART_SERIES`.

8. **T interface updated** — `results.chartError` and `chart.overflowBadge`, `chart.source` added to match translation keys from Plan 01.

Post-checkpoint fixes applied in commit d9d0287:

9. **Arabic dropdown dir="rtl"** — Dataset select element now has `dir={locale === "ar" ? "rtl" : "ltr"}` for correct RTL rendering.

10. **ExplorerDisclaimer redesign** — Gradient background (green-50 to emerald-50), inline SVG info icon, rounded close button for better visual hierarchy.

## Task Commits

Each task was committed atomically:

1. **Task 1: Refactor DataExplorer to use new components and add cap logic** - `0a9c4f8` (feat)
2. **Task 2: Visual verification checkpoint (approved with fixes)** - `d9d0287` (fix)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed source_name → source.organization**
- **Found during:** Build verification after Task 1
- **Issue:** Plan specified `datasetDetail?.source_name` but `DatasetDetail` type has no `source_name` field — it has `source: SourceRef | null` where `SourceRef.organization: string`
- **Fix:** Changed both line and bar chart attribution to `datasetDetail?.source?.organization`
- **Files modified:** apps/web/components/data/DataExplorer.tsx
- **Committed in:** 0a9c4f8 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed Recharts v3 TooltipProps → TooltipContentProps**
- **Found during:** Build verification after Task 1
- **Issue:** Recharts v3 moved `payload`, `active`, and `label` out of `TooltipProps` (they're Omit'd). Custom tooltip components in BarChartView and LineChartView used `TooltipProps` causing TS errors.
- **Fix:** Changed `import type { TooltipProps }` to `import type { TooltipContentProps }` and updated interface and cast in both files.
- **Files modified:** apps/web/components/charts/BarChartView.tsx, apps/web/components/charts/LineChartView.tsx
- **Committed in:** 0a9c4f8 (Task 1 commit)

**3. [Rule 1 - Bug] Fixed entry.name NameType type error**
- **Found during:** Build verification after TooltipContentProps fix
- **Issue:** `TooltipPayloadEntry.name` is `NameType = string | number`, but `series.indexOf()` and template literals require `string`.
- **Fix:** Added `const entryName = String(entry.name ?? "")` and used `entryName` throughout. Also fixed `entry.value` rendering with `String(entry.value ?? "")` fallback.
- **Files modified:** apps/web/components/charts/BarChartView.tsx, apps/web/components/charts/LineChartView.tsx
- **Committed in:** 0a9c4f8 (Task 1 commit)

**4. [Rule 3 - Blocking] Added missing translation keys to explore page**
- **Found during:** Build verification after Task 1
- **Issue:** DataExplorer T interface now requires `results.chartError`, `chart.overflowBadge`, `chart.source` but explore/page.tsx was not passing them. TS error at DataExplorer usage site.
- **Fix:** Added the three keys to the translations object in `apps/web/app/[locale]/explore/page.tsx`. Translation strings already existed in messages/en.json and messages/ar.json from Plan 01.
- **Files modified:** apps/web/app/[locale]/explore/page.tsx
- **Committed in:** 0a9c4f8 (Task 1 commit)

**5. [Rule 1 - Bug] Added dir="rtl" to Arabic dataset select (post-checkpoint)**
- **Found during:** Task 2 visual verification (user-reported)
- **Issue:** Dataset dropdown in Arabic locale did not render RTL — select element was missing dir attribute
- **Fix:** Added `dir={locale === "ar" ? "rtl" : "ltr"}` to the dataset `<select>` element
- **Files modified:** apps/web/components/data/DataExplorer.tsx
- **Committed in:** d9d0287 (post-checkpoint fix commit)

**6. [Rule 1 - Bug] Polished ExplorerDisclaimer visual design (post-checkpoint)**
- **Found during:** Task 2 visual verification (user-reported)
- **Issue:** Disclaimer banner styling was plain/flat; user requested gradient, info icon, better visual hierarchy
- **Fix:** Redesigned ExplorerDisclaimer with gradient background (green-50 to emerald-50), inline SVG info icon, rounded close button
- **Files modified:** apps/web/components/data/ExplorerDisclaimer.tsx
- **Committed in:** d9d0287 (post-checkpoint fix commit)

---

**Total deviations:** 6 auto-fixed (5 bugs, 1 blocking)
**Impact on plan:** All fixes necessary for type correctness, localization quality, and visual quality. No scope creep.

## Known Stubs

None — all wiring is real. The disclaimer reads from actual sessionStorage. Source attribution reads from real dataset source data. Chart data flows from real API observations.

## Next Phase Readiness

- Chart rendering is stable with proper series capping and institutional styling
- DataExplorer component is clean — no Recharts imports at the consumer layer
- Bilingual (EN/AR) rendering verified including RTL dropdown direction
- Potential follow-up: full RTL axis direction in Arabic locale (Recharts has no native RTL; `reversed` workaround tracked as concern in STATE.md)

---
*Phase: 01-chart-fix-and-explorer-polish*
*Completed: 2026-03-24*
