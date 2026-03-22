"""Pipeline for Tech for Palestine conflict/casualty datasets.

Sources: https://github.com/TechForPalestine/palestine-datasets
Data: Daily casualties (Gaza/West Bank), infrastructure damage.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

import httpx
import psycopg2
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)

BASE_URL = "https://raw.githubusercontent.com/TechForPalestine/palestine-datasets/main"

import os
DB_URL = os.environ.get("DATABASE_URL", "postgresql://datapal:datapal_dev_2026@localhost:5432/datapalestine")

# Category: Conflict & Protection (id=6)
CATEGORY_ID = 6

DATASETS = [
    {
        "slug": "gaza-daily-casualties",
        "name_en": "Daily Casualties in Gaza",
        "name_ar": "الضحايا اليوميون في غزة",
        "desc_en": "Daily reports of deaths and injuries in Gaza since October 7, 2023. Includes breakdowns by children, women, medical personnel, and press.",
        "desc_ar": "تقارير يومية عن القتلى والجرحى في غزة منذ 7 أكتوبر 2023. تشمل تفصيلاً حسب الأطفال والنساء والطواقم الطبية والصحفيين.",
        "url": f"{BASE_URL}/casualties_daily.json",
        "geography": "PS-GZA",
        "indicators": [
            {"code": "gaza_killed_cum", "name_en": "Cumulative deaths", "name_ar": "إجمالي القتلى", "field": "killed_cum", "unit": "persons"},
            {"code": "gaza_killed_children_cum", "name_en": "Children killed (cumulative)", "name_ar": "الأطفال القتلى (تراكمي)", "field": "killed_children_cum", "unit": "persons"},
            {"code": "gaza_killed_women_cum", "name_en": "Women killed (cumulative)", "name_ar": "النساء القتلى (تراكمي)", "field": "killed_women_cum", "unit": "persons"},
            {"code": "gaza_injured_cum", "name_en": "Cumulative injuries", "name_ar": "إجمالي الجرحى", "field": "injured_cum", "unit": "persons"},
            {"code": "gaza_killed_daily", "name_en": "Daily deaths", "name_ar": "القتلى اليوميون", "field": "killed", "unit": "persons"},
            {"code": "gaza_med_killed_cum", "name_en": "Medical personnel killed (cumulative)", "name_ar": "الطواقم الطبية القتلى (تراكمي)", "field": "ext_med_personnel_killed_cum", "unit": "persons"},
            {"code": "gaza_press_killed_cum", "name_en": "Press killed (cumulative)", "name_ar": "الصحفيون القتلى (تراكمي)", "field": "ext_press_killed_cum", "unit": "persons"},
        ],
    },
    {
        "slug": "west-bank-daily-casualties",
        "name_en": "Daily Casualties in the West Bank",
        "name_ar": "الضحايا اليوميون في الضفة الغربية",
        "desc_en": "Daily statistics on fatalities, injuries, and settler attacks in the West Bank since October 7, 2023.",
        "desc_ar": "إحصائيات يومية عن القتلى والجرحى وهجمات المستوطنين في الضفة الغربية منذ 7 أكتوبر 2023.",
        "url": f"{BASE_URL}/west_bank_daily.json",
        "geography": "PS-WBK",
        "indicators": [
            {"code": "wb_killed_cum", "name_en": "Cumulative deaths", "name_ar": "إجمالي القتلى", "field": "killed_cum", "unit": "persons"},
            {"code": "wb_killed_children_cum", "name_en": "Children killed (cumulative)", "name_ar": "الأطفال القتلى (تراكمي)", "field": "killed_children_cum", "unit": "persons"},
            {"code": "wb_injured_cum", "name_en": "Cumulative injuries", "name_ar": "إجمالي الجرحى", "field": "injured_cum", "unit": "persons"},
            {"code": "wb_settler_attacks_cum", "name_en": "Settler attacks (cumulative)", "name_ar": "هجمات المستوطنين (تراكمي)", "field": "settler_attacks_cum", "unit": "incidents"},
        ],
    },
    {
        "slug": "gaza-infrastructure-damage",
        "name_en": "Infrastructure Damage in Gaza",
        "name_ar": "الأضرار في البنية التحتية في غزة",
        "desc_en": "Daily assessments of damage to civilian infrastructure in Gaza including residential, educational, and religious buildings.",
        "desc_ar": "تقييمات يومية للأضرار في البنية التحتية المدنية في غزة بما في ذلك المباني السكنية والتعليمية والدينية.",
        "url": f"{BASE_URL}/infrastructure-damaged.json",
        "geography": "PS-GZA",
        "indicators": [
            {"code": "gaza_residential_destroyed", "name_en": "Residential units destroyed", "name_ar": "وحدات سكنية مدمرة", "field": "residential.destroyed", "unit": "units"},
            {"code": "gaza_edu_destroyed", "name_en": "Educational buildings destroyed", "name_ar": "مبانٍ تعليمية مدمرة", "field": "educational_buildings.ext_destroyed", "unit": "buildings"},
            {"code": "gaza_edu_damaged", "name_en": "Educational buildings damaged", "name_ar": "مبانٍ تعليمية متضررة", "field": "educational_buildings.ext_damaged", "unit": "buildings"},
            {"code": "gaza_mosques_destroyed", "name_en": "Mosques destroyed", "name_ar": "مساجد مدمرة", "field": "places_of_worship.ext_mosques_destroyed", "unit": "buildings"},
            {"code": "gaza_mosques_damaged", "name_en": "Mosques damaged", "name_ar": "مساجد متضررة", "field": "places_of_worship.ext_mosques_damaged", "unit": "buildings"},
        ],
    },
]


def get_nested(obj: dict, path: str):
    """Get a nested field by dot path like 'residential.destroyed'."""
    for key in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return None
    return obj


def run():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Ensure source exists
    cur.execute("""
        INSERT INTO sources (slug, name_en, name_ar, source_type, website_url, reliability)
        VALUES ('tech-for-palestine', 'Tech for Palestine', 'تقنية من أجل فلسطين',
                'ngo', 'https://data.techforpalestine.org', 4)
        ON CONFLICT (slug) DO UPDATE SET name_en = EXCLUDED.name_en
        RETURNING id
    """)
    source_id = cur.fetchone()[0]
    conn.commit()

    total_obs = 0

    for ds_config in DATASETS:
        print(f"\n--- {ds_config['name_en']} ---")

        # Fetch JSON
        print(f"  Fetching {ds_config['url']}...")
        resp = httpx.get(ds_config["url"], timeout=60)
        resp.raise_for_status()
        records = resp.json()
        print(f"  Got {len(records)} records")

        # Create or update dataset
        cur.execute("""
            INSERT INTO datasets (slug, name_en, name_ar, description_en, description_ar,
                                  category_id, primary_source_id, status, update_frequency)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'published', 'daily')
            ON CONFLICT (slug) DO UPDATE SET
                name_en = EXCLUDED.name_en,
                description_en = EXCLUDED.description_en,
                description_ar = EXCLUDED.description_ar
            RETURNING id
        """, (ds_config["slug"], ds_config["name_en"], ds_config["name_ar"],
              ds_config["desc_en"], ds_config["desc_ar"], CATEGORY_ID, source_id))
        dataset_id = cur.fetchone()[0]

        # Link source
        cur.execute("""
            INSERT INTO dataset_sources (dataset_id, source_id, is_primary)
            VALUES (%s, %s, true)
            ON CONFLICT (dataset_id, source_id) DO NOTHING
        """, (dataset_id, source_id))

        # Source document
        cur.execute("""
            INSERT INTO source_documents (source_id, title_en, document_url, file_type, access_date)
            VALUES (%s, %s, %s, 'json', CURRENT_DATE)
            RETURNING id
        """, (source_id, ds_config["name_en"], ds_config["url"]))
        source_doc_id = cur.fetchone()[0]

        # Create indicators
        indicator_ids = {}
        for ind_conf in ds_config["indicators"]:
            cur.execute("""
                INSERT INTO indicators (dataset_id, code, name_en, name_ar, unit_en, unit_ar, decimals)
                VALUES (%s, %s, %s, %s, %s, %s, 0)
                ON CONFLICT ON CONSTRAINT indicators_dataset_id_code_key DO UPDATE SET
                    name_en = EXCLUDED.name_en,
                    name_ar = EXCLUDED.name_ar
                RETURNING id
            """, (dataset_id, ind_conf["code"], ind_conf["name_en"], ind_conf["name_ar"],
                  ind_conf["unit"], ind_conf["unit"], ))
            indicator_ids[ind_conf["code"]] = cur.fetchone()[0]
        conn.commit()

        # Upsert observations (insert new, update existing)
        obs_rows = []
        for record in records:
            report_date = record.get("report_date")
            if not report_date:
                continue
            try:
                tp = date.fromisoformat(report_date)
            except (ValueError, TypeError):
                continue

            for ind_conf in ds_config["indicators"]:
                value = get_nested(record, ind_conf["field"])
                if value is None:
                    continue
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    continue

                obs_rows.append((
                    indicator_ids[ind_conf["code"]],
                    ds_config["geography"],
                    tp,
                    "daily",
                    value,
                    source_doc_id,
                ))

        if obs_rows:
            # Use a temp table for upsert to handle the partitioned observations table
            cur.execute("CREATE TEMP TABLE _obs_staging (LIKE observations INCLUDING DEFAULTS) ON COMMIT DROP")
            execute_values(cur, """
                INSERT INTO _obs_staging (indicator_id, geography_code, time_period,
                                          time_precision, value, source_document_id)
                VALUES %s
            """, obs_rows)
            cur.execute("""
                INSERT INTO observations (indicator_id, geography_code, time_period,
                                          time_precision, value, source_document_id)
                SELECT indicator_id, geography_code, time_period,
                       time_precision, value, source_document_id
                FROM _obs_staging s
                ON CONFLICT (id, time_period) DO UPDATE SET
                    value = EXCLUDED.value,
                    source_document_id = EXCLUDED.source_document_id
            """)
            total_obs += len(obs_rows)
            print(f"  Upserted {len(obs_rows)} observations")

        # Update temporal coverage
        cur.execute("""
            UPDATE datasets SET
                temporal_coverage_start = sub.min_t,
                temporal_coverage_end = sub.max_t
            FROM (
                SELECT MIN(o.time_period) as min_t, MAX(o.time_period) as max_t
                FROM observations o JOIN indicators i ON o.indicator_id = i.id
                WHERE i.dataset_id = %s
            ) sub
            WHERE datasets.id = %s
        """, (dataset_id, dataset_id))

        conn.commit()

    print(f"\n=== Total: {total_obs} observations from Tech for Palestine ===")

    # Final counts
    cur.execute("SELECT COUNT(*) FROM datasets")
    ds = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM indicators")
    inds = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM observations")
    obs = cur.fetchone()[0]
    print(f"Database totals: {ds} datasets, {inds:,} indicators, {obs:,} observations")

    cur.close()
    conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
