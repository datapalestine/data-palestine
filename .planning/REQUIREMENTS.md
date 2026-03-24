# Requirements: Data Palestine

**Defined:** 2026-03-24
**Core Value:** Researchers, journalists, and policymakers can explore and download reliable Palestinian data through a professional, institutional-quality interface — in both Arabic and English.

## v1 Requirements

Requirements for MVP launch. Each maps to roadmap phases.

### Chart Rendering

- [ ] **CHART-01**: User can view line chart with up to 5 indicators rendered correctly (no legend overflow, actual lines visible)
- [ ] **CHART-02**: User can view bar chart with up to 5 indicators rendered correctly (no legend overflow, actual bars visible)
- [ ] **CHART-03**: When more than 5 indicators are selected, charts display only the first 5 with a clear indication that others are hidden
- [x] **CHART-04**: Chart legend renders outside the SVG container with fixed max-height, never consuming chart area

### Chart Styling

- [x] **STYLE-01**: Charts use clean, institutional styling — muted gridlines, professional axis labels, no chart border clutter
- [x] **STYLE-02**: Y-axis tick labels use abbreviated number formatting (K/M/B) to prevent label clipping
- [x] **STYLE-03**: Charts use the project's defined chart color palette (#2E7D32, #1565C0, #EF6C00, #6A1B9A, #C62828, #00838F)
- [x] **STYLE-04**: Source attribution line displays below charts showing the data source name

### Data Explorer UX

- [x] **UX-01**: Development disclaimer banner appears at the top of the Data Explorer page indicating data is still being refined
- [x] **UX-02**: Disclaimer banner is dismissible per session (localStorage)

## v2 Requirements

Deferred to data cleanup milestone. Tracked but not in current roadmap.

### Data Cleanup

- **DATA-01**: Indicator names are normalized and cleaned across all datasets (remove prefixes, standardize formatting)
- **DATA-02**: Consolidate normalization logic from archive scripts into reusable pipeline utilities
- **DATA-03**: Add pandera schema validation to all pipeline runs as data quality gates
- **DATA-04**: Left panel indicator list displays clean, readable names

### Chart Enhancements

- **CHART-05**: User can download chart as PNG image (deferred until data/labels are clean)
- **CHART-06**: Unit mismatch warning when comparing indicators with different units
- **CHART-07**: Auto-generated chart titles based on selected indicators

## Out of Scope

| Feature | Reason |
|---------|--------|
| Left panel redesign | Root cause is data quality, not UI — fix data first in v2 |
| Chart animations | Institutional portals use static charts; animations cause flicker |
| Recharts library replacement | Current library is correct, bug is configuration not library |
| Real-time data updates | All data is periodic/statistical |
| Chart zoom/pan | Complexity not justified for MVP; evaluate post-launch |
| Multiple Y-axes | High complexity; defer to future if user demand exists |
| New data source pipelines | After MVP launch and data cleanup |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CHART-01 | Phase 1 | Pending |
| CHART-02 | Phase 1 | Pending |
| CHART-03 | Phase 1 | Pending |
| CHART-04 | Phase 1 | Complete |
| STYLE-01 | Phase 1 | Complete |
| STYLE-02 | Phase 1 | Complete |
| STYLE-03 | Phase 1 | Complete |
| STYLE-04 | Phase 1 | Complete |
| UX-01 | Phase 1 | Complete |
| UX-02 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after roadmap creation*
