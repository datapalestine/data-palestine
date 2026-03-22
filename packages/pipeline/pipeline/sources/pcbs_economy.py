"""Pipeline for PCBS economic indicators."""

import pandas as pd

from pipeline.base import BasePipeline
from pipeline.models import LoadResult, RawFile


class PCBSEconomyPipeline(BasePipeline):
    """Pipeline for PCBS economic indicators (GDP, CPI, trade balance)."""

    @property
    def name(self) -> str:
        return "pcbs_economy"

    @property
    def source_url(self) -> str:
        return "https://www.pcbs.gov.ps/site/lang__en/507/default.aspx"

    async def collect(self) -> list[RawFile]:
        raise NotImplementedError

    async def extract(self, raw_files: list[RawFile]) -> pd.DataFrame:
        raise NotImplementedError

    async def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError

    async def load(self, df: pd.DataFrame) -> LoadResult:
        raise NotImplementedError
