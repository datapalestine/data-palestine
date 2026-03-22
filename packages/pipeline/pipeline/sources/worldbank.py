"""Pipeline for World Bank indicators for Palestine (PSE).

Uses the World Bank REST API v2:
  https://api.worldbank.org/v2/country/PSE/indicator/{code}?format=json&per_page=500&date=1990:2025

Fetches clean JSON, no scraping needed.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime

import httpx
import psycopg2
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)

# World Bank indicators to fetch
INDICATORS = [
    {
        "wb_code": "NY.GDP.MKTP.CD",
        "code": "gdp_current_usd",
        "name_en": "GDP (current US$)",
        "name_ar": "الناتج المحلي الإجمالي (بالدولار الأمريكي الجاري)",
        "unit_en": "US dollars",
        "unit_ar": "دولار أمريكي",
        "unit_symbol": "$",
        "decimals": 0,
        "category_slug": "economy",
    },
    {
        "wb_code": "SP.POP.TOTL",
        "code": "population_total",
        "name_en": "Population, total",
        "name_ar": "إجمالي عدد السكان",
        "unit_en": "persons",
        "unit_ar": "نسمة",
        "unit_symbol": "",
        "decimals": 0,
        "category_slug": "population",
    },
    {
        "wb_code": "SL.UEM.TOTL.ZS",
        "code": "unemployment_rate",
        "name_en": "Unemployment, total (% of total labor force, ILO modeled)",
        "name_ar": "معدل البطالة (% من إجمالي القوى العاملة، نموذج منظمة العمل الدولية)",
        "unit_en": "percent",
        "unit_ar": "نسبة مئوية",
        "unit_symbol": "%",
        "decimals": 1,
        "category_slug": "labor",
    },
    {
        "wb_code": "SP.DYN.LE00.IN",
        "code": "life_expectancy",
        "name_en": "Life expectancy at birth, total (years)",
        "name_ar": "العمر المتوقع عند الولادة (سنوات)",
        "unit_en": "years",
        "unit_ar": "سنة",
        "unit_symbol": "",
        "decimals": 1,
        "category_slug": "health",
    },
]

API_BASE = "https://api.worldbank.org/v2/country/PSE/indicator"
DATE_RANGE = "1990:2025"


async def fetch_indicator(client: httpx.AsyncClient, wb_code: str) -> list[dict]:
    """Fetch all observations for a single indicator from the World Bank API."""
    url = f"{API_BASE}/{wb_code}"
    params = {"format": "json", "per_page": "500", "date": DATE_RANGE}

    resp = await client.get(url, params=params)
    resp.raise_for_status()

    data = resp.json()
    # World Bank API returns [metadata, data_array]
    if not isinstance(data, list) or len(data) < 2 or data[1] is None:
        logger.warning("No data returned for %s", wb_code)
        return []

    return data[1]


def run_pipeline(db_url: str) -> dict:
    """Run the full World Bank pipeline synchronously.

    Steps:
    1. Ensure the 'world-bank' source exists (seeded by schema.sql)
    2. Create a source_document record for this API fetch
    3. Create a dataset for World Bank indicators
    4. Create indicator records
    5. Fetch observations from the API
    6. Insert observation records with provenance
    7. Record the pipeline run
    """
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    started_at = datetime.now(tz=None)
    total_inserted = 0
    total_processed = 0

    try:
        # 1. Get the world-bank source ID (already seeded)
        cur.execute("SELECT id FROM sources WHERE slug = 'world-bank'")
        row = cur.fetchone()
        if not row:
            raise RuntimeError("Source 'world-bank' not found — run schema.sql seed data first")
        source_id = row[0]

        # 2. Create a source_document for this API fetch
        cur.execute(
            """INSERT INTO source_documents
               (source_id, title_en, title_ar, document_url, file_type, access_date, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (
                source_id,
                "World Bank Open Data API — Palestine (PSE)",
                "واجهة برمجة تطبيقات البنك الدولي للبيانات المفتوحة — فلسطين",
                "https://api.worldbank.org/v2/country/PSE",
                "api",
                date.today(),
                '{"api_version": "v2", "country_code": "PSE", "date_range": "1990:2025"}',
            ),
        )
        source_document_id = cur.fetchone()[0]

        # 3. Create the dataset (upsert by slug)
        cur.execute("SELECT id FROM categories WHERE slug = 'economy'")
        economy_cat_id = cur.fetchone()[0]

        cur.execute(
            """INSERT INTO datasets
               (slug, name_en, name_ar, description_en, description_ar,
                category_id, primary_source_id, status, update_frequency,
                methodology_en, methodology_ar, license, featured)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (slug) DO UPDATE SET updated_at = NOW()
               RETURNING id""",
            (
                "world-bank-development-indicators",
                "World Bank Development Indicators — Palestine",
                "مؤشرات التنمية للبنك الدولي — فلسطين",
                "Key development indicators for the West Bank and Gaza from the World Bank Open Data platform. "
                "Includes GDP, population, unemployment, life expectancy, and other socioeconomic metrics.",
                "مؤشرات التنمية الرئيسية للضفة الغربية وقطاع غزة من منصة البنك الدولي للبيانات المفتوحة. "
                "تشمل الناتج المحلي الإجمالي والسكان والبطالة ومتوسط العمر المتوقع ومقاييس اجتماعية اقتصادية أخرى.",
                economy_cat_id,
                source_id,
                "published",
                "annual",
                "Data sourced from the World Bank Open Data API (api.worldbank.org/v2). "
                "Country code PSE (West Bank and Gaza). Values are as reported by the World Bank "
                "with no transformation applied.",
                "البيانات مصدرها واجهة برمجة تطبيقات البنك الدولي للبيانات المفتوحة. "
                "رمز الدولة PSE (الضفة الغربية وقطاع غزة). القيم كما وردت من البنك الدولي "
                "دون أي تحويل.",
                "CC-BY-4.0",
                True,
            ),
        )
        dataset_id = cur.fetchone()[0]

        # Also link dataset to source
        cur.execute(
            """INSERT INTO dataset_sources (dataset_id, source_id, is_primary)
               VALUES (%s, %s, TRUE)
               ON CONFLICT DO NOTHING""",
            (dataset_id, source_id),
        )

        # 4-6. For each indicator: create indicator record, fetch data, insert observations
        observations_to_insert = []

        for ind_config in INDICATORS:
            # Create indicator record
            cur.execute(
                """INSERT INTO indicators
                   (dataset_id, code, name_en, name_ar, description_en, description_ar,
                    unit_en, unit_ar, unit_symbol, decimals, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (dataset_id, code) DO UPDATE SET updated_at = NOW()
                   RETURNING id""",
                (
                    dataset_id,
                    ind_config["code"],
                    ind_config["name_en"],
                    ind_config["name_ar"],
                    ind_config["name_en"],
                    ind_config["name_ar"],
                    ind_config["unit_en"],
                    ind_config["unit_ar"],
                    ind_config["unit_symbol"],
                    ind_config["decimals"],
                    f'{{"wb_code": "{ind_config["wb_code"]}"}}',
                ),
            )
            indicator_id = cur.fetchone()[0]

            # Fetch data from World Bank API
            logger.info("Fetching %s (%s)...", ind_config["code"], ind_config["wb_code"])
            wb_data = asyncio.run(
                _fetch_single_indicator(ind_config["wb_code"])
            )

            for obs in wb_data:
                year = obs.get("date")
                value = obs.get("value")
                if value is None or year is None:
                    continue
                try:
                    year_int = int(year)
                    value_float = float(value)
                except (ValueError, TypeError):
                    continue

                total_processed += 1
                observations_to_insert.append((
                    indicator_id,
                    "PS",  # National level
                    date(year_int, 1, 1),  # Normalize to Jan 1
                    "annual",
                    value_float,
                    "final",
                    source_document_id,
                    1,   # data_version
                    True,  # is_latest
                ))

            logger.info(
                "  %s: %d observations fetched",
                ind_config["code"],
                len([o for o in observations_to_insert if o[0] == indicator_id]),
            )

        # Bulk insert observations
        if observations_to_insert:
            execute_values(
                cur,
                """INSERT INTO observations
                   (indicator_id, geography_code, time_period, time_precision,
                    value, status, source_document_id, data_version, is_latest)
                   VALUES %s
                   ON CONFLICT DO NOTHING""",
                observations_to_insert,
            )
            total_inserted = len(observations_to_insert)

        # Update dataset temporal coverage
        cur.execute(
            """UPDATE datasets SET
                temporal_coverage_start = (
                    SELECT MIN(o.time_period) FROM observations o
                    JOIN indicators i ON o.indicator_id = i.id
                    WHERE i.dataset_id = %s
                ),
                temporal_coverage_end = (
                    SELECT MAX(o.time_period) FROM observations o
                    JOIN indicators i ON o.indicator_id = i.id
                    WHERE i.dataset_id = %s
                ),
                published_at = NOW(),
                updated_at = NOW()
               WHERE id = %s""",
            (dataset_id, dataset_id, dataset_id),
        )

        # 7. Record the pipeline run
        completed_at = datetime.now(tz=None)
        cur.execute(
            """INSERT INTO pipeline_runs
               (pipeline_name, started_at, completed_at, status,
                records_processed, records_inserted, records_updated, records_skipped)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                "worldbank",
                started_at,
                completed_at,
                "success",
                total_processed,
                total_inserted,
                0,
                total_processed - total_inserted,
            ),
        )

        conn.commit()

        result = {
            "status": "success",
            "dataset_id": dataset_id,
            "source_document_id": source_document_id,
            "indicators_created": len(INDICATORS),
            "observations_processed": total_processed,
            "observations_inserted": total_inserted,
            "duration_seconds": (completed_at - started_at).total_seconds(),
        }
        logger.info("Pipeline complete: %s", result)
        return result

    except Exception as e:
        conn.rollback()
        logger.error("Pipeline failed: %s", e)

        # Record failed run
        try:
            cur.execute(
                """INSERT INTO pipeline_runs
                   (pipeline_name, started_at, completed_at, status, error_message)
                   VALUES (%s, %s, %s, %s, %s)""",
                ("worldbank", started_at, datetime.now(tz=None), "failed", str(e)),
            )
            conn.commit()
        except Exception:
            pass

        raise

    finally:
        cur.close()
        conn.close()


async def _fetch_single_indicator(wb_code: str) -> list[dict]:
    """Async helper to fetch a single indicator."""
    async with httpx.AsyncClient(timeout=30) as client:
        return await fetch_indicator(client, wb_code)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    db_url = sys.argv[1] if len(sys.argv) > 1 else (
        "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine"
    )

    result = run_pipeline(db_url)
    print(f"\nDone! {result['observations_inserted']} observations inserted "
          f"across {result['indicators_created']} indicators.")
