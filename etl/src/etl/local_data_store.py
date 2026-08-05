from etl.base.data_store import BaseDataStore
from etl.dtos import DataSource, NormalizedLocation
from pathlib import Path
import json

src_key = 'source'
loc_key = 'locations'
data_dir = Path(__file__).parent / "data"

# Reads and writes normalized locations to a local file.
class LocalDataStore(BaseDataStore):

    def write_source_snapshot(
        self,
        source: DataSource,
        normalized_locations: list[NormalizedLocation],
    ) -> None:
        file_path = self._get_file_path(source)
        locations_serialized = [location.model_dump(mode="json") for location in normalized_locations]
        snapshot = json.dumps({ src_key: source.value, loc_key: locations_serialized }, indent=2)
        with open(file_path, "w") as file:
            file.write(snapshot)

    def read_source_snapshot(
        self,
        source: DataSource,
    ) -> list[NormalizedLocation]:
        file_path = self._get_file_path(source)
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        with open(file_path, "r") as file:
            snapshot_serialized = json.load(file)

        snapshot_source = snapshot_serialized[src_key]
        if snapshot_source != source.value:
            raise ValueError(f"Provided source '{source.value}' does not match file source '{snapshot_source}'")

        return [NormalizedLocation.model_validate(location) for location in snapshot_serialized[loc_key]]

    def write_output_locations(
        self,
        output_locations: list[NormalizedLocation],
    ) -> None:
        pass

    def _get_file_path(self, source: DataSource) -> Path:
        data_dir.mkdir(exist_ok=True)
        return data_dir / f"{source.value}_snapshot.json"