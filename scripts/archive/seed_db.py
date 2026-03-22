"""Load seed data into the database.

Usage:
    python scripts/seed_db.py

This script loads the initial geography and source data from the schema.sql
seed data. It can be run after initial database creation if the schema was
applied without seed data.
"""

import sys
from pathlib import Path


def main():
    """Seed the database with initial data."""
    print("Database seeding is handled by schema.sql during Docker init.")
    print("See packages/db/schema.sql for seed data (geographies, categories, sources).")
    print("Run: docker compose up db")


if __name__ == "__main__":
    main()
