from etl.base.data_store import BaseDataStore
from etl.dtos import NormalizedLocation


# Reads and writes normalized locations to a local file.
class LocalDataStore(BaseDataStore):

    def write_source_snapshot(
        self,
        source: str,
        normalized_locations: list[NormalizedLocation],
    ) -> None:
        pass

    def read_source_snapshot(
        self,
        source: str,
    ) -> list[NormalizedLocation]:
        pass

    def write_output_locations(
        self,
        output_locations: list[NormalizedLocation],
    ) -> None:
        pass
