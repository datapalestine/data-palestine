"""Shared Pydantic models for pipeline I/O."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class RawFile:
    """A raw file downloaded from a data source."""

    path: Path
    source_url: str
    file_type: str  # 'pdf', 'excel', 'csv', 'html'
    title: str | None = None
    publication_date: datetime | None = None
    checksum: str | None = None


@dataclass
class LoadResult:
    """Result of loading data into the database."""

    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineRunResult:
    """Result of a full pipeline execution."""

    pipeline_name: str
    status: str  # 'success', 'failed', 'partial'
    started_at: datetime | None = None
    completed_at: datetime | None = None
    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    error_message: str | None = None
