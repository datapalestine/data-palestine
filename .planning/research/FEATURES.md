# Feature Research

**Domain:** Institutional open data portal — chart/data explorer UX
**Researched:** 2026-03-24
**Confidence:** HIGH (World Bank, OECD, Eurostat, Datawrapper studied directly; Urban Institute style guide reviewed)

## Context

This research targets a specific milestone: fixing broken charts and achieving professional/institutional quality. The platform already has a functional DataExplorer (Recharts, line + bar views, table view, CSV export). The current bugs: selecting many indicators causes the Recharts Legend to overflow and consume the entire chart area, leaving no space for the actual chart.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume any serious data portal has. Missing them signals "amateur project."

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Hard cap on visible series | Every institutional portal (Eurostat: 24 max, Urban Institute: 7 max) enforces this; users expect it to "just work" | LOW | Cap at 5 for MVP. Show a chip/badge "5 of 12 shown" so users know truncation occurred. Already a KEY DECISION in PROJECT.md. |
| Legend that doesn't break layout | Recharts default Legend grows without bound — all real portals constrain it | LOW | Render legend as a fixed-height, scrollable or wrapping list outside the chart SVG, not inside it. |
| Tooltips on hover | Every chart tool from Eurostat to Datawrapper has rich hover tooltips | LOW | Recharts Tooltip already present; ensure it shows indicator name, value with unit, and time period. |
| Readable axis labels | Truncated or overlapping axis labels are a red flag for institutional quality | LOW | Rotate year labels if needed; abbreviate long indicator names to ~30 chars in axis. |
| Subtle grid lines | All institutional charts (World Bank, Eurostat, Urban Institute) use light horizontal grid lines only | LOW | `CartesianGrid` with `strokeDasharray="3 3"` and `stroke="#E0E0E0"` — horizontal only, no vertical. |
| Source attribution in chart area | Every real data portal (Datawrapper, World Bank, OECD) shows "Source: PCBS / World Bank" below the chart | LOW | Static footer under chart with dataset source name and year of last update. |
| Download chart as PNG | Datawrapper, Eurostat, OECD all offer PNG download; researchers expect this for reports | MEDIUM | Use `html-to-image` or `dom-to-image-more` on the chart container. Include title + source in the download frame. |
| Loading state during fetch | Users get confused by empty charts while data loads | LOW | Already exists (obsLoading); ensure chart skeleton is shown, not a blank white area. |
| Empty state with guidance | When no data matches filters, explain why and offer next steps | LOW | "No data found for this combination. Try selecting a different geography or time range." |
| Accessible color palette | Color-blind safe palette is standard for institutional data; multiple portals explicitly use diverging/accessible palettes | LOW | Current palette is reasonable; ensure no two adjacent series are green+red or blue+purple confusion pairs. |

### Differentiators (Competitive Advantage)

Features that go beyond PCBS/World Bank's own portals and give Data Palestine its edge.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Development disclaimer banner | No real institutional portal launches with a quality caveat — this is honest and builds trust instead of eroding it. Differentiates from PCBS's opaque data | LOW | Sticky banner at top of Explorer with amber/yellow styling. Text: "Data Explorer is in active development. Some indicators may have incomplete or unverified values." Dismissible per session (localStorage). |
| Indicator count badge on chart | OECD Data Explorer shows real-time count of selected data points; makes selection tangible | LOW | "Showing 3 of 7 indicators" badge above chart when cap is in effect. |
| Chart title auto-generated from selection | Datawrapper always shows a descriptive title; World Bank DataBank charts have titles | LOW | Auto-generate: "{IndicatorName} — {Geography}, {YearFrom}–{YearTo}". Use the first selected indicator name if multiple. |
| Institutional color scheme applied to charts | Current CHART_COLORS are reasonable but not styled for institutional quality — legend uses no typography spec | LOW | Match Urban Institute pattern: clean sans-serif, subdued gridlines, chart colors with clear visual hierarchy. Ensure primary series (#2E7D32) is visually dominant. |
| Clear "N indicators hidden" disclosure | When cap truncates, show which indicators are hidden — Eurostat does this; OECD shows data availability warnings | LOW | After the legend, show a collapsed section: "3 more indicators not shown — adjust selection to view them." |
| Sharable URL state | All filters in URL (already implemented); this is actually rare in basic portals like PCBS | LOW | Already works — just needs documentation on the developers page. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| "Select all indicators" as default | Convenience — auto-populate on dataset select | Already causing the chart-breaking bug. Selecting all makes charts unreadable and is the root cause of the current issue. | Auto-select the 5 most recent / most complete indicators, or the first 3. Show "select all" as a button with a warning tooltip. |
| Unlimited series on one chart | Power users want to compare everything | Creates a "spaghetti chart" that is unreadable. Eurostat caps at 24; Urban Institute recommends <7; best practice is 5. | Suggest "Compare in table view" when >5 series selected. |
| Real-time legend inside SVG | Recharts default puts Legend inside the responsive container, sharing SVG space with the chart | When legend has 10+ items, it consumes the chart area entirely — this is the current production bug | Render legend as a separate React element outside the ResponsiveContainer, with fixed max-height and overflow scroll. |
| Animated chart transitions | Looks polished | Recharts animations cause performance issues with many data points, and re-render flicker on filter changes. Eurostat and World Bank DataBank use no animation. | Set `isAnimationActive={false}` on all Line and Bar components. |
| Tooltips showing all series at once | "Cross-hair" tooltip for every series | With 5+ series, tooltips become unreadably tall | Show only the hovered series value prominently; list other series values in smaller text or omit. |
| "Pivot" or cross-dataset joins in UI | Power user request — combine World Bank and PCBS data in one chart | Massive complexity, data alignment problems (different geographies, time periods, units), creates misleading comparisons | Mark as Phase 2 feature after data cleanup. |
| Excel export from chart view | Common request from NGO researchers | Replicates existing CSV export with extra complexity; Excel export from the DataExplorer table view already planned | Keep CSV. Add note on developers page that CSV opens in Excel. |

---

## Feature Dependencies

```
[Hard indicator cap (5)]
    └──enables──> [Readable legend layout]
                      └──enables──> [Chart PNG download] (can't screenshot broken chart)

[Source attribution in chart]
    └──required by──> [Chart PNG download] (attribution must travel with the image)

[Development disclaimer banner]
    └──independent──> [No dependencies — standalone UI element]

[Auto-generated chart title]
    └──enhances──> [Chart PNG download] (title appears in downloaded image)

[Indicator cap] ──conflicts──> [Auto-select all indicators on dataset load]
```

### Dependency Notes

- **Hard indicator cap requires legend fix:** Capping at 5 is meaningless if the legend still overflows at 5. Both must be implemented together.
- **PNG download requires attribution:** A chart image without a source line is not publishable by journalists or researchers. Source must be in the downloaded frame.
- **Cap conflicts with current auto-select behavior:** The existing auto-apply on dataset load selects ALL indicators and all geographies. This must change to "select first 3-5 indicators" when implementing the cap.

---

## MVP Definition

This milestone is narrowly scoped. The platform is near-MVP launch.

### Launch With (v1 — this milestone)

- [x] Hard cap: max 5 indicators visible in chart views (already decided, just implement)
- [x] Legend rendered outside chart SVG — fixed height, never overlaps chart area
- [x] Development disclaimer banner — dismissible, session-persistent
- [x] Source attribution line below charts
- [x] Disable Recharts animations (`isAnimationActive={false}`)
- [x] Institutional chart styling: subdued gridlines, clean axis typography, consistent palette

### Add After Validation (v1.x — post-MVP / data cleanup milestone)

- [ ] Chart PNG download — trigger: data is clean enough to be share-worthy
- [ ] Auto-generated chart title — trigger: after indicator naming is cleaned up (messy names now)
- [ ] "N indicators hidden" disclosure — trigger: after cap is working smoothly
- [ ] Remove development disclaimer — trigger: data cleanup milestone complete

### Future Consideration (v2+)

- [ ] Embeddable chart widgets — Phase 2 (already in PROJECT.md)
- [ ] Cross-dataset comparison — after data cleanup + schema validation
- [ ] User-saved chart configurations — requires auth (out of scope)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Hard indicator cap (5 max) | HIGH — fixes production bug | LOW — clamp array in chart render | P1 |
| Legend outside SVG | HIGH — fixes production bug | LOW — restructure JSX layout | P1 |
| Development disclaimer banner | HIGH — trust / expectation setting | LOW — banner component + localStorage | P1 |
| Disable Recharts animations | MEDIUM — performance + stability | LOW — one prop per chart element | P1 |
| Institutional chart styling | MEDIUM — professional appearance | LOW-MEDIUM — styling pass | P1 |
| Source attribution below chart | MEDIUM — required for PNG sharing | LOW — static text element | P1 |
| Chart PNG download | HIGH — researchers publish charts | MEDIUM — html-to-image library | P2 |
| Auto-generated chart title | MEDIUM — polish | LOW — string interpolation | P2 |
| "N indicators hidden" disclosure | LOW-MEDIUM — transparency | LOW — conditional text render | P2 |
| Chart type toggle (line/bar) | MEDIUM — already exists | — | done |
| CSV export | HIGH — primary download path | — | done |
| URL-based filter state | HIGH — shareability | — | done |

**Priority key:**
- P1: Must have for this milestone launch
- P2: Should have, add when possible (post data cleanup)
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | World Bank DataBank | Eurostat Data Browser | OECD Data Explorer | Our Approach |
|---------|--------------------|-----------------------|-------------------|--------------|
| Series limit | Enforced (cell count limit) | Hard cap: 24 lines | Warns when too many | Cap at 5 for MVP; show count badge |
| Legend placement | Below chart, separate | Below chart, interactive (click to highlight) | Sidebar configuration | Outside SVG, below chart, fixed height |
| Series highlighting | No (all equal weight) | Yes — click to highlight one line | Yes — "spotlight" mode | Phase 2; overkill for MVP |
| Chart download | PNG + PDF (DataBank) | PNG + PDF with title/source | PNG + CSV | PNG download in v1.x after data cleanup |
| Source attribution | Footer: "World Bank" | Footer: "Eurostat, [year]" | Footer: "OECD, [year]" | Static line: "Source: [dataset.source_name]" |
| Development/beta notice | None (stable platform) | None | None | Unique to us — honest about data quality |
| Tooltips | Value + country + year | Value + flags (data quality indicators) | Value + time period | Value + indicator name + unit |
| Chart title | User-editable | Auto-generated from selection | Auto-generated | Auto-generated (after name cleanup) |
| Animated transitions | None | None | None | Disable — match institutional standard |
| Grid lines | Light horizontal only | Light horizontal only | Light horizontal + vertical (subtle) | Light horizontal only |

---

## Sources

- [Eurostat Data Browser — Line Chart User Guide](https://ec.europa.eu/eurostat/web/user-guides/data-browser/data-selection-display/line-charts) — HIGH confidence, official documentation
- [World Bank DataBank](https://databank.worldbank.org/source/world-development-indicators) — HIGH confidence, direct observation
- [OECD Data Explorer](https://data-explorer.oecd.org/) — HIGH confidence, direct fetch
- [Urban Institute Graphics Style Guide](http://urbaninstitute.github.io/graphics-styleguide/) — HIGH confidence, published style guide; rule: <7 categories per chart
- [Datawrapper — Download as PNG](https://academy.datawrapper.de/article/204-how-to-download-your-chart-as-a-png) — HIGH confidence, official docs
- [Datawrapper — Footer and attribution features](https://www.datawrapper.de/blog/footer-options-let-readers-download-and-embed-your-datavis) — HIGH confidence, official blog
- [Line Chart Best Practices — useful data tips](https://usefuldatatips.com/tips/visualization/line-chart-best-practices) — MEDIUM confidence, practitioner guide; recommendation: 1-5 lines max
- [Pencil & Paper — Dashboard UX Patterns](https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards) — MEDIUM confidence, UX practitioner guide
- [CKAN Data Visualization (Keitaro, 2024)](https://www.keitaro.com/insights/2024/05/30/ckan-data-visualization-creating-compelling-insights/) — MEDIUM confidence, HDX is CKAN-based
- [Data visualization best practices 2025](https://www.timetackle.com/data-visualization-best-practices/) — LOW confidence (general blog, but corroborates institutional patterns)

---

*Feature research for: institutional open data portal — chart/data explorer UX*
*Researched: 2026-03-24*
