"""Abstract base class for all data ingestion pipelines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from pipeline.models import LoadResult, PipelineRunResult, RawFile


class BasePipeline(ABC):
    """Base class for all data ingestion pipelines.

    Each pipeline implements four stages:
    1. collect — Download raw files from source
    2. extract — Parse tables from raw files into DataFrames
    3. transform — Normalize schema, clean values, validate
    4. load — Insert into database with provenance tracking
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Pipeline identifier (e.g., 'pcbs_population')."""
        ...

    @property
    @abstractmethod
    def source_url(self) -> str:
        """Primary URL for the data source."""
        ...

    @abstractmethod
    async def collect(self) -> list[RawFile]:
        """Download raw files from the data source."""
        ...

    @abstractmethod
    async def extract(self, raw_files: list[RawFile]) -> pd.DataFrame:
        """Parse tables from raw files into structured DataFrames."""
        ...

    @abstractmethod
    async def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize schema, clean values, validate."""
        ...

    @abstractmethod
    async def load(self, df: pd.DataFrame) -> LoadResult:
        """Insert into database with full provenance tracking."""
        ...

    async def run(self) -> PipelineRunResult:
        """Execute full pipeline: collect -> extract -> transform -> load."""
        started_at = datetime.now()
        try:
            raw_files = await self.collect()
            df = await self.extract(raw_files)
            df = await self.transform(df)
            result = await self.load(df)
            return PipelineRunResult(
                pipeline_name=self.name,
                status="success",
                started_at=started_at,
                completed_at=datetime.now(),
                records_processed=result.records_processed,
                records_inserted=result.records_inserted,
                records_updated=result.records_updated,
                records_skipped=result.records_skipped,
            )
        except Exception as e:
            return PipelineRunResult(
                pipeline_name=self.name,
                status="failed",
                started_at=started_at,
                completed_at=datetime.now(),
                error_message=str(e),
            )
