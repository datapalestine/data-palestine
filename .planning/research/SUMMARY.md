# Project Research Summary

**Project:** Data Palestine — Chart Fix and Data Cleanup Milestone
**Domain:** Institutional open data portal — chart rendering and statistical data quality
**Researched:** 2026-03-24
**Confidence:** HIGH

## Executive Summary

This is a brownfield milestone on an existing, partially functional platform. The stack (Next.js 15, Recharts 3.8, FastAPI, PostgreSQL/TimescaleDB, Python pipelines) is sound and should not change. The two parallel problems to solve are: (1) a known production bug causing chart collapse when many indicators are selected, and (2) dirty indicator data that makes the Explorer left panel untrustworthy. These are independent workstreams with a clear sequencing dependency — fix the chart rendering first so the platform no longer looks broken, then clean the data so the platform can be trusted.

The recommended approach is surgical and incremental: cap visible chart series at 5, move the Recharts legend outside the SVG, add a development disclaimer banner, and ship a clean-looking Explorer. Then run the data normalization pipeline — centralizing scattered cleanup scripts into a shared `normalizer.py` and applying pandera schema validation per dataset. The chart styling pass (professional institutional aesthetics matching World Bank/Eurostat quality) should happen last, after the chart is structurally fixed and the indicator names are clean enough to display.

The primary risk is provenance destruction during data cleanup. PCBS and World Bank observations look similar but must never be merged under a single indicator ID. The cleanup mandate is rename-and-group, never merge-and-delete. The secondary risk is silent pipeline failures: PCBS CSV patterns change without notice, and the current pipeline completes with "success" even when 0 observations are inserted. Both risks have concrete, low-cost mitigations that should be built into the data cleanup phase.

---

## Key Findings

### Recommended Stack

The existing stack requires no changes. Three lightweight libraries should be added to the pipeline layer: **pandera 0.30.1** for per-dataset schema validation (replaces ad-hoc assertions with a declarative contract), **pyjanitor 0.32.20** for chainable PCBS column normalization (eliminates custom `clean_names` code), and **rapidfuzz 3.14.3** for fuzzy indicator deduplication audits (MIT licensed, 100x faster than the deprecated fuzzywuzzy). No new frontend dependencies are needed — chart improvement is entirely a configuration problem.

**Core technologies:**
- Recharts 3.8.0: chart rendering — correct choice, do not replace; v3.8 adds `niceTicks`, `responsive` prop, and `labelStyle`
- pandas 2.2+: DataFrame transformations — adequate for current data volumes; Polars only if rows exceed 10M
- pandera 0.30.1: pipeline schema validation — schema-as-code, raises on bad data before it reaches the DB
- pyjanitor 0.32.20: PCBS data normalization — `clean_names()` + `transform_column()` replaces custom regexes
- rapidfuzz 3.14.3: fuzzy deduplication audits — run post-ingest, output CSV for human review; never auto-merge

### Expected Features

The chart fix milestone is narrowly scoped. All P1 features are low-complexity configuration or small components. The only anti-feature that must be actively removed is the current auto-select-all behavior on dataset load, which is the root cause of the chart bug.

**Must have (table stakes — this milestone):**
- Hard cap at 5 visible series in chart view — prevents the layout collapse bug; expected by all institutional portals
- Legend rendered outside chart SVG with fixed height — Recharts built-in Legend is incompatible with many-series datasets
- Development disclaimer banner (dismissible, session-persistent) — sets honest expectations; unique differentiator
- Source attribution below charts — required for any chart image to be publishable
- Recharts animations disabled (`isAnimationActive={false}`) — matches institutional standard; eliminates flicker
- Institutional axis/grid styling — clean typography, horizontal-only gridlines, formatted tick values

**Should have (add post-data-cleanup):**
- Chart PNG download — requires data to be clean enough to share; use `html-to-image` on chart container
- Auto-generated chart title from selection — requires clean indicator names first
- "N indicators hidden" disclosure — after cap is working smoothly

**Defer (v2+):**
- Embeddable chart widgets — already in project roadmap
- Cross-dataset comparison in Explorer — requires data alignment work across sources
- User-saved chart configurations — requires auth, out of scope

### Architecture Approach

The fix involves three discrete refactors that do not depend on each other but should ship in order. First, the chart layer in `apps/web/components/charts/` gets split: `ChartLegend.tsx` is extracted as a standalone component rendered outside `ResponsiveContainer`, and series are capped at render time (not at fetch time — the table view still needs all observations). Second, the pipeline layer consolidates normalization logic currently scattered across `scripts/archive/` into `scripts/pipeline/shared/` modules (`normalizer.py`, `geo_tagger.py`, `deduplicator.py`). Third, pandera schemas are added per dataset to the `transform()` stage of each pipeline.

**Major components:**
1. `ChartLegend.tsx` (new) — custom legend with fixed height, overflow badge, rendered above `ResponsiveContainer`
2. `LineChartView` / `BarChartView` (refactored) — pure presentational; receive `series[]` already capped at 5
3. `scripts/pipeline/shared/normalizer.py` (consolidated) — canonical name rules extracted from archive scripts
4. `scripts/pipeline/shared/geo_tagger.py` (consolidated) — GEO_MAP extracted and centralized
5. `scripts/pipeline/shared/deduplicator.py` (consolidated) — find-or-create indicator logic
6. Per-dataset pandera schemas in `transform()` — fail loudly before bad data reaches the DB

### Critical Pitfalls

1. **Recharts Legend consumes chart area** — cap `seriesNames.slice(0, 5)` before passing to chart components; render `<ChartLegend />` as a sibling div above `<ResponsiveContainer>`, not inside the Recharts tree. Recovery cost is LOW once the cap exists.

2. **Provenance destruction during cleanup** — never merge observations across `dataset_id` boundaries; deduplication is rename + display-group, not merge + delete. If this goes wrong, recovery requires a full backup restore. Prevention cost is LOW; recovery cost is HIGH.

3. **Mixed units on shared Y-axis** — when selected indicators have different `unit_symbol` values, show a unit-mismatch warning rather than silently plotting incompatible series on one axis. Add unit awareness to the selection UI alongside the 5-indicator cap.

4. **Stale URL state after indicator rename** — never delete-and-reinsert indicators during cleanup; update in place. Add a `deprecated_at` column to indicators so removals produce a 410 response instead of silent empty results.

5. **PCBS CSV silent failures** — add an assertion: if `records_inserted / records_processed < 0.5`, set pipeline run status to `"warning"` not `"success"`. This is a one-line guard with no architectural cost.

---

## Implications for Roadmap

Based on the combined research, two phases are clearly indicated with a hard dependency between them.

### Phase 1: Chart Fix

**Rationale:** The platform currently looks broken when any PCBS dataset is selected. This is the highest-visibility problem and blocks any meaningful user testing. The fix requires no data changes and no new backend work — it is entirely a frontend restructure. Ship this first to unblock everything else.

**Delivers:** A functional, professional-looking Data Explorer where charts always render correctly, regardless of how many indicators are in a dataset. Includes the development disclaimer banner and source attribution.

**Addresses:**
- Hard indicator cap (5 max visible in chart)
- Legend outside SVG with fixed height
- Development disclaimer banner
- Source attribution below charts
- Disable Recharts animations
- Institutional axis/grid styling
- Unit-mismatch warning (alongside cap implementation)

**Avoids:**
- Pitfall 1 (legend consumes chart area)
- Pitfall 3 (mixed units on Y-axis)
- Anti-pattern: auto-select all indicators replaced with smart default (first 3 by sort_order)

### Phase 2: Data Cleanup

**Rationale:** Once the chart is fixed and visually trustworthy, the next trust problem is indicator name quality. Raw PCBS strings like `"Unnamed: 3_level_1"` and `"% Change  Monthly"` appear in the Explorer left panel and erode confidence. The data cleanup phase also enables the P2 chart features (PNG download, auto-generated title) that were deferred because dirty names make them unusable.

**Delivers:** Clean canonical indicator names in the DB, shared normalization pipeline infrastructure, pandera schema validation on all pipelines, and pipeline run alerting for silent failures.

**Uses:**
- pandera 0.30.1 (new) — schema validation in `transform()` stage
- pyjanitor 0.32.20 (new) — PCBS column normalization
- rapidfuzz 3.14.3 (new) — fuzzy dedup audit script
- pandas 2.2+ (existing) — no change

**Implements:**
- `scripts/pipeline/shared/normalizer.py` (consolidated from archive scripts)
- `scripts/pipeline/shared/geo_tagger.py` (consolidated)
- `scripts/pipeline/shared/deduplicator.py` (consolidated)
- Per-dataset pandera schemas
- Pipeline run warning status for high skip rates

**Avoids:**
- Pitfall 2 (provenance destruction) — rename-and-group, never merge-and-delete
- Pitfall 4 (stale URL state) — update-in-place, add `deprecated_at` column
- Pitfall 5 (PCBS silent failures) — skip-rate assertion guard

### Phase 3: Chart Polish and P2 Features

**Rationale:** After the chart is structurally fixed (Phase 1) and the indicator names are clean (Phase 2), professional styling and publishable features become worthwhile. Styling a broken chart or a chart with dirty labels wastes effort. This phase removes the development disclaimer and adds the features that make charts share-worthy.

**Delivers:** World Bank/Eurostat-quality chart aesthetics, PNG download capability, auto-generated chart titles, "N indicators hidden" disclosure, and removal of the development disclaimer banner.

**Addresses:**
- Chart PNG download (requires clean data and working chart)
- Auto-generated chart title (requires clean indicator names)
- "N indicators hidden" disclosure
- Remove development disclaimer

### Phase Ordering Rationale

- **Chart fix before data cleanup:** The chart bug is user-facing and breaks the product. Data cleanup is invisible until the chart works. Fixing the chart unblocks user testing and creates pressure to clean the data.
- **Data cleanup before polish:** Styling is wasted on dirty names. PNG download is unusable if indicator names are raw PCBS export strings. The disclaimer must stay until cleanup is done.
- **Polish last:** This phase has the lowest technical risk and highest visibility — save it for when the platform is functionally solid.

### Research Flags

Phases with standard patterns (skip `research-phase` — patterns are well-documented):
- **Phase 1 (Chart Fix):** Recharts configuration is thoroughly documented; patterns are verified and code-ready from this research. No additional research needed.
- **Phase 2 (Data Cleanup):** Pandera, pyjanitor, and rapidfuzz patterns are code-ready from this research. The consolidation work is pure refactoring of existing archive scripts.

Phases that may need targeted research during planning:
- **Phase 3 (Chart Polish):** The `html-to-image` PNG download approach should be validated against the Next.js 15 + Recharts 3.8 SSR environment before committing. RTL axis direction in Arabic locale (Recharts has no native RTL support) may need targeted investigation.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core libraries verified via PyPI and GitHub releases. Recharts 3.8 `responsive` prop is MEDIUM — new in March 2026, SSR behavior not yet tested in this codebase. |
| Features | HIGH | Institutional portal benchmarks (World Bank, Eurostat, OECD, Urban Institute) studied directly. Feature recommendations are grounded in observable patterns, not speculation. |
| Architecture | HIGH | Based on direct codebase inspection of `DataExplorer.tsx`, `csv_parser.py`, archive scripts, and ORM models. Component split is a refactor of existing code, not a rewrite. |
| Pitfalls | HIGH | Chart pitfalls confirmed via Recharts issue tracker (issues #671, #1198, #2636). Data pitfalls confirmed via direct inspection of archive cleanup scripts and pipeline code. |

**Overall confidence:** HIGH

### Gaps to Address

- **Recharts `responsive` prop SSR behavior:** The new `responsive` prop added in v3.8 may still require a `"use client"` boundary or `dynamic()` import. Keep the existing `dynamic()` pattern until tested. Do not refactor SSR handling until this is confirmed working.
- **RTL axis direction in Arabic locale:** Recharts has no native RTL support. The `reversed={locale === "ar"}` workaround for XAxis needs testing against the existing next-intl setup. Flag this during Phase 3 planning.
- **`deprecated_at` column migration:** Adding this column to the `indicators` table requires an Alembic migration. This is straightforward but must be coordinated with the data cleanup scripts that will set the column value.

---

## Sources

### Primary (HIGH confidence)
- Recharts GitHub issues #671, #1198, #2636 — legend height and ResponsiveContainer overlap bugs (confirmed existing, not fixed as of 2026)
- Recharts GitHub releases — v3.8.0 feature list (`niceTicks`, `responsive` prop, `labelStyle`)
- pandera PyPI — version 0.30.1, March 18 2026
- pyjanitor PyPI — version 0.32.20, February 18 2026
- rapidfuzz PyPI — version 3.14.3, November 2025
- World Bank DataBank (direct observation) — legend placement, series cap, chart aesthetics
- Eurostat Data Browser documentation — series cap (24 max), legend behavior
- Urban Institute Graphics Style Guide — <7 categories per chart rule
- OECD Data Explorer (direct observation) — tooltip and series count handling
- Direct codebase inspection: `apps/web/components/data/DataExplorer.tsx`, `packages/pipeline/pcbs/csv_parser.py`, `apps/api/app/models/indicator.py`, `scripts/archive/` directory

### Secondary (MEDIUM confidence)
- Datawrapper blog — PNG download patterns, source attribution in chart footer
- Recharts customize guide — SVG styling, tooltip/legend customization
- Data validation landscape 2025 (aeturrell.com) — pandera vs Great Expectations comparison
- Line chart best practices (usefuldatatips.com) — 1–5 lines max recommendation

### Tertiary (LOW confidence)
- General data visualization best practices blogs — corroborate institutional patterns but are not authoritative

---
*Research completed: 2026-03-24*
*Ready for roadmap: yes*
