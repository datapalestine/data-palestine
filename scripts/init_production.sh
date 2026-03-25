#!/bin/bash
set -e

echo "============================================"
echo "Data Palestine - Production Database Init"
echo "============================================"

# Use the sync database URL for psycopg2-based scripts
export DATABASE_URL="${DATABASE_URL_SYNC:-postgresql://datapalestine:${POSTGRES_PASSWORD}@db:5432/datapalestine}"
DB_HOST="${DB_HOST:-db}"
DB_USER="${DB_USER:-datapalestine}"
DB_NAME="${DB_NAME:-datapalestine}"
# Extract password from DATABASE_URL for psql commands
DB_PASS=$(echo "$DATABASE_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')

# Step 0: Check data directories exist
echo ""
echo "[0/8] Checking data directories..."
DATA_DIR="/data"
MISSING=0
for dir in "$DATA_DIR/raw/pcbs_csv"; do
    if [ ! -d "$dir" ]; then
        echo "  WARNING: $dir not found"
        MISSING=1
    else
        count=$(ls "$dir"/*.csv 2>/dev/null | wc -l)
        echo "  OK: $dir ($count files)"
    fi
done
if [ -d "$DATA_DIR/raw/pcbs_xlsx" ]; then
    count=$(ls "$DATA_DIR/raw/pcbs_xlsx"/*.xlsx 2>/dev/null | wc -l)
    echo "  OK: $DATA_DIR/raw/pcbs_xlsx ($count files)"
fi

# Step 1: Wait for PostgreSQL
echo ""
echo "[1/8] Waiting for PostgreSQL..."
for i in $(seq 1 30); do
    if pg_isready -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -q 2>/dev/null; then
        echo "  PostgreSQL is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  ERROR: PostgreSQL not ready after 30 seconds"
        exit 1
    fi
    sleep 1
done

# Step 2: Check if data already exists
echo ""
echo "[2/8] Checking existing data..."
EXISTING=$(PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM observations;" 2>/dev/null || echo "0")
EXISTING=$(echo "$EXISTING" | tr -d ' ')

if [ "$EXISTING" -gt 1000 ]; then
    echo "  Database already has $EXISTING observations. Skipping ingestion."
    echo "  To re-initialize, drop and recreate the database first."

    # Print final counts
    echo ""
    echo "============================================"
    echo "Current Database State"
    echo "============================================"
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c \
        "SELECT 'Datasets' as entity, COUNT(*) FROM datasets
         UNION ALL SELECT 'Indicators', COUNT(*) FROM indicators
         UNION ALL SELECT 'Observations', COUNT(*) FROM observations
         ORDER BY entity;"
    exit 0
fi

# Step 3: World Bank pipeline (needs internet)
echo ""
echo "[3/8] Running World Bank pipeline..."
cd /app
python -c "
from pipeline.sources.worldbank import run_pipeline
import os
db_url = os.environ.get('DATABASE_URL', 'postgresql://datapalestine:password@db:5432/datapalestine')
result = run_pipeline(db_url)
print(f'  World Bank: {result[\"observations_inserted\"]} observations, {result[\"indicators_created\"]} indicators')
" 2>&1 | tail -10 || echo "  World Bank pipeline failed (non-fatal)"

# Step 4: PCBS CSV ingestion (uses raw CSV files, not discovery JSON)
echo ""
echo "[4/8] Running PCBS CSV ingestion..."
if [ -d "$DATA_DIR/raw/pcbs_csv" ]; then
    CSV_COUNT=$(ls "$DATA_DIR/raw/pcbs_csv"/*.csv 2>/dev/null | wc -l)
    echo "  Found $CSV_COUNT CSV files"
    python -c "
import os, glob, json, psycopg2
from pipeline.sources.pcbs_csv_ingest import ingest_table, clean_title, slugify, load_geography_names
from pipeline.sources.pcbs_csv_ingest import parse_csv_content
import hashlib

db_url = os.environ.get('DATABASE_URL')
conn = psycopg2.connect(db_url)
conn.autocommit = False
cur = conn.cursor()

# Get PCBS source ID
cur.execute(\"SELECT id FROM sources WHERE slug = 'pcbs'\")
row = cur.fetchone()
if not row:
    print('  ERROR: PCBS source not found in database. Run schema seed first.')
    exit(1)
source_id = row[0]

# Get category map
cur.execute('SELECT slug, id FROM categories')
pcbs_category_map = dict(cur.fetchall())
geo_name_map = load_geography_names(cur)

files = sorted(glob.glob('$DATA_DIR/raw/pcbs_csv/table_*.csv'))
total_obs = 0
total_ds = 0
errors = 0

for i, f in enumerate(files):
    try:
        with open(f, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()
        csv_hash = hashlib.sha256(content.encode()).hexdigest()
        fname = os.path.basename(f)
        # Extract table_id from filename (table_1234_...)
        parts = fname.replace('.csv', '').split('_')
        table_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else i
        title = ' '.join(parts[2:]).replace('-', ' ').strip() if len(parts) > 2 else fname

        table_info = {'table_id': table_id, 'title': title, 'csv_url': f}
        result = ingest_table(conn, table_info, content, csv_hash, source_id, pcbs_category_map, geo_name_map)
        if result['status'] == 'ingested':
            total_obs += result['observations']
            total_ds += 1
    except Exception as e:
        errors += 1
    if (i+1) % 200 == 0:
        print(f'  Processed {i+1}/{len(files)} files... ({total_ds} datasets, {total_obs} obs)')
        conn.commit()

conn.commit()
conn.close()
print(f'  Total: {total_obs} observations from {total_ds} datasets ({errors} errors)')
" 2>&1 | grep -E "Total|Processed|ERROR"
else
    echo "  No CSV directory found, skipping."
fi

# Step 5: Tech for Palestine pipeline
echo ""
echo "[5/8] Running Tech for Palestine pipeline..."
python -c "
from pipeline.sources.techforpalestine import run
run()
" 2>&1 | tail -5

# Step 6: XLSX ingestion
echo ""
echo "[6/8] Running XLSX ingestion..."
if [ -d "$DATA_DIR/raw/pcbs_xlsx" ]; then
    python -c "
import glob
from packages.pipeline.pcbs.xlsx_ingest import ingest_xlsx
files = glob.glob('$DATA_DIR/raw/pcbs_xlsx/*.xlsx')
for f in sorted(files)[:10]:
    try:
        ingest_xlsx(f)
    except Exception as e:
        print(f'  Skipped: {e}')
" 2>&1 | tail -10
else
    echo "  No XLSX directory found, skipping."
fi

# Step 7: Cleanup scripts
echo ""
echo "[7/8] Running cleanup scripts..."
cd /app

# Geography reprocessing
python scripts/archive/decompose_indicators.py 2>&1 | tail -3 || echo "  decompose skipped"

# Dataset consolidation
python scripts/archive/consolidate_datasets.py 2>&1 | tail -3 || echo "  consolidation skipped"

# Final cleanup
python scripts/archive/final_cleanup.py 2>&1 | tail -3 || echo "  final cleanup skipped"

# Step 8: Final report
echo ""
echo "[8/8] Final database state:"
echo "============================================"
PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c \
    "SELECT 'Datasets' as entity, COUNT(*) FROM datasets
     UNION ALL SELECT 'Indicators', COUNT(*) FROM indicators
     UNION ALL SELECT 'Observations', COUNT(*) FROM observations
     ORDER BY entity;"

echo ""
echo "Production initialization complete."
