"""Pipeline for B'Tselem casualty statistics."""

import pandas as pd

from pipeline.base import BasePipeline
from pipeline.models import LoadResult, RawFile


class BtselemCasualtiesPipeline(BasePipeline):
    """Pipeline for B'Tselem casualty data.

    Note: Handle with extreme care — these represent human lives.
    """

    @property
    def name(self) -> str:
        return "btselem_casualties"

    @property
    def source_url(self) -> str:
        return "https://statistics.btselem.org"

    async def collect(self) -> list[RawFile]:
        raise NotImplementedError

    async def extract(self, raw_files: list[RawFile]) -> pd.DataFrame:
        raise NotImplementedError

    async def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError

    async def load(self, df: pd.DataFrame) -> LoadResult:
        raise NotImplementedError
