# Data Palestine

## What This Is

An open data platform that aggregates, modernizes, and serves Palestinian statistical, humanitarian, and socioeconomic data. It pulls from PCBS, World Bank, Tech for Palestine, B'Tselem, and other sources — transforming scattered data into a unified, bilingual (Arabic RTL / English LTR), API-driven platform at datapalestine.org.

## Core Value

Researchers, journalists, and policymakers can explore and download reliable Palestinian data through a professional, institutional-quality interface — in both Arabic and English.

## Requirements

### Validated

- ✓ FastAPI REST API with paginated endpoints for datasets, indicators, observations, geographies, sources, and export — existing
- ✓ PostgreSQL 16 + TimescaleDB schema with 9 tables, seed geographies, and pipeline run tracking — existing
- ✓ Data pipelines for World Bank, Tech for Palestine, PCBS population, PCBS economy, PCBS labor, and B'Tselem casualties — existing
- ✓ Next.js 15 bilingual frontend with Arabic RTL / English LTR via next-intl — existing
- ✓ Homepage dashboard with key statistics and dataset highlights — existing
- ✓ Dataset catalog with search and filtering — existing
- ✓ Individual dataset pages with metadata and data table — existing
- ✓ Data Explorer page with indicator selection, geography/time filters, and table view — existing
- ✓ Line chart and bar chart views in Data Explorer (basic rendering) — existing
- ✓ Sparkline charts on homepage — existing
- ✓ CSV export / download functionality — existing
- ✓ Copy API URL and Source File links — existing
- ✓ Docker Compose setup for local development and production — existing
- ✓ CI pipeline with linting, testing, and deployment workflows — existing
- ✓ About, Methodology, and Developers pages — existing
- ✓ Charts cap at 5 indicators with overflow badge, institutional styling — Phase 1
- ✓ Professional chart rendering (muted gridlines, K/M/B axes, source attribution) — Phase 1
- ✓ Development disclaimer banner on Data Explorer (dismissible per session) — Phase 1

### Active

- [ ] Post-MVP: Comprehensive data cleanup and wrangling for professional-grade accuracy

### Out of Scope

- Left panel redesign — deferred until data is cleaned up post-MVP
- New data sources — after MVP launch and data cleanup
- Data Stories section — Phase 2
- Embeddable chart widgets — Phase 2
- API client libraries — Phase 2
- PWA / offline support — Phase 2
- User accounts / authentication — not needed for public data platform
- Real-time data — all data is periodic/statistical, not live

## Context

- MVP is ready for launch. Phase 1 (chart fix and explorer polish) is complete.
- Charts now cap at 5 visible indicators with professional institutional styling.
- The explore page's left panel shows messy indicator names due to unclean source data — acceptable for MVP, will be addressed in data cleanup phase.
- Data comes from multiple sources with varying quality — PCBS data especially needs cleanup (indicator naming, categorization, deduplication).
- The platform should feel like a data institution (World Bank, UN OCHA), not an advocacy campaign.
- Palestinian flag colors (green, red, black, white) used as accents only.

## Constraints

- **Tech stack**: Next.js 15 + FastAPI + PostgreSQL 16 + TimescaleDB — already built, no changes
- **Bilingual**: Every user-facing string must work in both English and Arabic RTL
- **Performance**: Pages must work on 3G connections, < 200KB initial bundle per page
- **Accessibility**: WCAG 2.1 AA compliance minimum
- **Privacy**: No user data collection beyond anonymous analytics
- **Source attribution**: Every data point traces back to its original source
- **No editorializing**: Platform presents data, not opinions

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Cap chart indicators at 5 for MVP | Too many indicators breaks chart rendering; proper multi-indicator UX is a larger effort | — Pending |
| Add development disclaimer to Explorer | Data isn't fully clean yet; sets user expectations | — Pending |
| Defer left panel fixes to post-MVP | Root cause is data quality, not UI — fix data first | — Pending |
| Data cleanup as first post-MVP milestone | Professional data quality is the core differentiator | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-24 after Phase 1 completion*
