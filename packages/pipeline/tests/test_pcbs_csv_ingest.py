"""Tests for PCBS CSV ingestion pipeline run-status guard."""

from pipeline.sources.pcbs_csv_ingest import determine_run_status


def test_status_success_when_all_tables_ingested():
    assert determine_run_status(tables_processed=10, tables_ingested=10) == "success"


def test_status_success_when_no_tables_to_process():
    assert determine_run_status(tables_processed=0, tables_ingested=0) == "success"


def test_status_partial_when_all_tables_silently_skipped():
    assert determine_run_status(tables_processed=200, tables_ingested=0) == "partial"


def test_status_partial_when_majority_of_tables_skipped():
    assert determine_run_status(tables_processed=10, tables_ingested=4) == "partial"


def test_status_success_at_half_threshold():
    assert determine_run_status(tables_processed=10, tables_ingested=5) == "success"
