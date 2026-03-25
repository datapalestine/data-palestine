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
EXISTING=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c \
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
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c \
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
import sys; sys.path.insert(0, '.')
from packages.pipeline.pipeline.sources.worldbank import run
run()
" 2>&1 | tail -5

# Step 4: PCBS CSV ingestion
echo ""
echo "[4/8] Running PCBS CSV ingestion..."
if [ -d "$DATA_DIR/raw/pcbs_csv" ]; then
    CSV_COUNT=$(ls "$DATA_DIR/raw/pcbs_csv"/*.csv 2>/dev/null | wc -l)
    echo "  Found $CSV_COUNT CSV files"
    python -c "
import sys, os, glob; sys.path.insert(0, '.')
from packages.pipeline.pipeline.sources.pcbs_csv_ingest import ingest_csv_file
files = sorted(glob.glob('$DATA_DIR/raw/pcbs_csv/table_*.csv'))
total = 0
for i, f in enumerate(files):
    try:
        n = ingest_csv_file(f)
        total += n
    except Exception as e:
        pass
    if (i+1) % 100 == 0:
        print(f'  Processed {i+1}/{len(files)} files...')
print(f'  Total: {total} observations from {len(files)} CSV files')
" 2>&1 | grep -E "Total|Processed|Error"
else
    echo "  No CSV directory found, skipping."
fi

# Step 5: Tech for Palestine pipeline
echo ""
echo "[5/8] Running Tech for Palestine pipeline..."
python -c "
import sys; sys.path.insert(0, '.')
from packages.pipeline.pipeline.sources.techforpalestine import run
run()
" 2>&1 | tail -5

# Step 6: XLSX ingestion (IPI file)
echo ""
echo "[6/8] Running XLSX ingestion..."
if [ -d "$DATA_DIR/raw/pcbs_xlsx" ]; then
    python -c "
import sys, glob; sys.path.insert(0, '.')
from packages.pipeline.pcbs.xlsx_ingest import ingest_xlsx
files = glob.glob('$DATA_DIR/raw/pcbs_xlsx/*.xlsx') + glob.glob('$DATA_DIR/*.xlsx')
for f in files[:5]:
    try:
        ingest_xlsx(f)
    except Exception as e:
        print(f'  Skipped {f}: {e}')
" 2>&1 | tail -5
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
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c \
    "SELECT 'Datasets' as entity, COUNT(*) FROM datasets
     UNION ALL SELECT 'Indicators', COUNT(*) FROM indicators
     UNION ALL SELECT 'Observations', COUNT(*) FROM observations
     ORDER BY entity;"

echo ""
echo "Production initialization complete."
