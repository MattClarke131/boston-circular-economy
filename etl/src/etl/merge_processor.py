from etl.base.data_store import BaseDataStore
from etl.dtos import MatchGroup, NormalizedLocation


class MergeProcessor:

    def __init__(self, store: BaseDataStore):
        self.store = store

    def process(self) -> None:
        locations_by_source = {
            "google_places": self.store.read_source_snapshot("google_places"),
            "openstreetmap": self.store.read_source_snapshot("openstreetmap"),
        }
        match_groups = self.match(locations_by_source)
        merged_locations = self.prioritize(match_groups)
        self.store.write_output_locations(merged_locations)

    # Match businesses across sources.
    # Assumes each source's list has no duplicate entries for the same business.
    def match(
        self,
        locations_by_source: dict[str, list[NormalizedLocation]],
    ) -> list[MatchGroup]:
        pass

    # Decide which source wins when merged fields conflict.
    def prioritize(
        self,
        match_groups: list[MatchGroup],
    ) -> list[NormalizedLocation]:
        pass
