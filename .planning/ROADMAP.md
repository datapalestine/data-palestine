# Roadmap: Data Palestine — Chart Fix Milestone

## Overview

The core platform is functional but the Data Explorer looks broken when any dataset with many indicators is loaded — the legend consumes the entire chart area and no chart renders. This milestone fixes the chart, styles it to institutional quality, and adds a development disclaimer banner so the Explorer can be shown to users without embarrassment. All 10 requirements are frontend changes to the Data Explorer. They ship together as one coherent delivery.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Chart Fix and Explorer Polish** - Fix chart rendering, apply institutional styling, add development disclaimer banner

## Phase Details

### Phase 1: Chart Fix and Explorer Polish
**Goal**: The Data Explorer reliably renders charts for any dataset, with professional institutional styling and an honest development disclaimer
**Depends on**: Nothing (first phase)
**Requirements**: CHART-01, CHART-02, CHART-03, CHART-04, STYLE-01, STYLE-02, STYLE-03, STYLE-04, UX-01, UX-02
**Success Criteria** (what must be TRUE):
  1. User can select a dataset with many indicators and see a line or bar chart render correctly — no legend overflow, actual chart visible
  2. When more than 5 indicators are selected, charts display only the first 5 and show a clear indication that others are hidden
  3. Charts display with clean institutional styling: muted gridlines, no border clutter, abbreviated Y-axis labels, correct color palette, and source attribution below the chart
  4. A dismissible development disclaimer banner appears at the top of the Data Explorer page and stays dismissed for the rest of the session
**Plans:** 1/2 plans executed
Plans:
- [x] 01-01-PLAN.md — Create new chart components (ChartLegend, LineChartView, BarChartView), ExplorerDisclaimer, constants, and i18n keys
- [ ] 01-02-PLAN.md — Wire components into DataExplorer with cap logic, auto-select fix, and visual verification
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Chart Fix and Explorer Polish | 1/2 | In Progress|  |
