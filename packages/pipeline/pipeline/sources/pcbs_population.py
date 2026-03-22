"""Pipeline for PCBS population statistics."""

import pandas as pd

from pipeline.base import BasePipeline
from pipeline.models import LoadResult, RawFile


class PCBSPopulationPipeline(BasePipeline):
    """Pipeline for PCBS population statistics.

    Source: Palestinian Central Bureau of Statistics
    Data: Population by territory, governorate, gender, age group
    """

    @property
    def name(self) -> str:
        return "pcbs_population"

    @property
    def source_url(self) -> str:
        return "https://www.pcbs.gov.ps/site/lang__en/507/default.aspx"

    DATASET_SLUG = "pcbs-population"

    async def collect(self) -> list[RawFile]:
        """Download raw files from PCBS website."""
        # Will be implemented in Step 5
        raise NotImplementedError

    async def extract(self, raw_files: list[RawFile]) -> pd.DataFrame:
        """Parse tables from HTML/PDF/Excel into structured DataFrames."""
        raise NotImplementedError

    async def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize schema, clean values, validate."""
        raise NotImplementedError

    async def load(self, df: pd.DataFrame) -> LoadResult:
        """Insert into database with full provenance tracking."""
        raise NotImplementedError
