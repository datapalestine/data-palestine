---
phase: 01-chart-fix-and-explorer-polish
plan: "01"
subsystem: frontend-charts
tags: [charts, recharts, i18n, components, disclaimer]
dependency_graph:
  requires: []
  provides:
    - ChartLegend component with flex-wrap legend outside SVG
    - LineChartView with institutional Recharts styling
    - BarChartView with institutional Recharts styling
    - ExplorerDisclaimer dismissible banner
    - MAX_CHART_SERIES and CHART_COLORS constants
    - i18n keys for disclaimer, chartError, overflowBadge, source
  affects:
    - apps/web/components/charts/
    - apps/web/components/data/
    - apps/web/lib/constants.ts
    - apps/web/messages/
tech_stack:
  added: []
  patterns:
    - Recharts dynamic() imports for SSR safety
    - sessionStorage for client-side dismiss persistence
    - next-intl useTranslations for component-level i18n
key_files:
  created:
    - apps/web/components/charts/ChartLegend.tsx
    - apps/web/components/charts/LineChartView.tsx
    - apps/web/components/charts/BarChartView.tsx
    - apps/web/components/data/ExplorerDisclaimer.tsx
  modified:
    - apps/web/lib/constants.ts
    - apps/web/messages/en.json
    - apps/web/messages/ar.json
    - .gitignore
decisions:
  - "ChartLegend renders outside Recharts SVG tree to prevent legend overflow collapsing chart area"
  - "Both chart views accept pre-capped series array — capping responsibility stays in DataExplorer caller"
  - "ExplorerDisclaimer defaults dismissed=true to prevent SSR flash; useEffect checks sessionStorage on mount"
metrics:
  duration_seconds: 224
  completed_date: "2026-03-24"
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  files_modified: 4
---

# Phase 01 Plan 01: Create Chart Components and Support Files Summary

**One-liner:** New ChartLegend, LineChartView, BarChartView, and ExplorerDisclaimer components with institutional Recharts styling, K/M/B axis formatting, and sessionStorage-persisted dismiss banner.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add constants and i18n keys | d5e6da1 | constants.ts, en.json, ar.json |
| 2 | Create ChartLegend, LineChartView, BarChartView | d2c3eb0 | 3 new chart component files |
| 3 | Create ExplorerDisclaimer component | 7e0c5d6 | ExplorerDisclaimer.tsx, .gitignore fix |

## What Was Built

**ChartLegend** (`apps/web/components/charts/ChartLegend.tsx`): Custom flex-wrap legend rendered as a sibling div above `<ResponsiveContainer>`, never inside the Recharts SVG tree. Each series item shows a colored swatch (10x10px rounded-sm) and a truncated name (max 180px) with full name in `title` attribute for tooltip accessibility.

**LineChartView** (`apps/web/components/charts/LineChartView.tsx`): Recharts `LineChart` with institutional styling — muted `#E0E0E0` grid (horizontal only), 11px `#757575` axis ticks, no animations, K/M/B Y-axis abbreviation, and a custom tooltip showing period label + series rows with 8px colored dots. Uses `dynamic()` imports for all Recharts components to ensure SSR safety.

**BarChartView** (`apps/web/components/charts/BarChartView.tsx`): Matching `BarChart` with identical grid/axis/tooltip config. Bar-specific: `barSize=24` for single series, `barSize=16` for 2–5 series, `radius=[2,2,0,0]` for top corner rounding. No built-in Recharts `<Legend />` — replaced by `<ChartLegend />`.

**ExplorerDisclaimer** (`apps/web/components/data/ExplorerDisclaimer.tsx`): Yellow dismissible banner (`#FFFDE7` background, `#F9A825` border) with `role="status"` for accessibility. Defaults to `dismissed=true` to prevent SSR flash; `useEffect` checks `sessionStorage` on mount. Dismiss sets `explorer_disclaimer_dismissed=1` in `sessionStorage`. Uses `useTranslations("explore.disclaimer")` from next-intl.

**Constants and i18n**: `MAX_CHART_SERIES=5` and `CHART_COLORS` array exported from `constants.ts`. All new i18n keys added to both `en.json` and `ar.json` under `explore.disclaimer`, `explore.results.chartError`, `explore.chart.overflowBadge`, and `explore.chart.source`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed overly broad .gitignore pattern blocking components/data/ tracking**
- **Found during:** Task 3 commit
- **Issue:** The pattern `data/` in `.gitignore` (intended for raw data directories) was also matching `apps/web/components/data/`, preventing ExplorerDisclaimer.tsx and DataExplorer.tsx from being tracked
- **Fix:** Replaced generic `data/` with specific paths: `/data/`, `pipelines/data/`, `apps/api/data/`
- **Files modified:** `.gitignore`
- **Commit:** 7e0c5d6
- **Side effect:** Also added previously untracked `DataExplorer.tsx` to version control

## Known Stubs

None — all components are fully implemented with real logic. No placeholder data, no hardcoded empty values flowing to UI.

## Self-Check: PASSED

Files verified:
- `apps/web/components/charts/ChartLegend.tsx` — FOUND
- `apps/web/components/charts/LineChartView.tsx` — FOUND
- `apps/web/components/charts/BarChartView.tsx` — FOUND
- `apps/web/components/data/ExplorerDisclaimer.tsx` — FOUND
- `apps/web/lib/constants.ts` contains `MAX_CHART_SERIES = 5` — VERIFIED
- `apps/web/messages/en.json` contains all required keys — VERIFIED
- `apps/web/messages/ar.json` contains all required keys — VERIFIED

Commits verified:
- d5e6da1 — FOUND (feat: constants and i18n)
- d2c3eb0 — FOUND (feat: chart components)
- 7e0c5d6 — FOUND (feat: ExplorerDisclaimer + gitignore fix)
