from etl.local_data_store import LocalDataStore
from etl.sources.google_places.normalizer import GooglePlacesNormalizer
from etl.sources.google_places.querier import GooglePlacesQuerier
from etl.sources.openstreetmap.normalizer import OpenStreetMapNormalizer
from etl.sources.openstreetmap.querier import OpenStreetMapQuerier

google_places_query_args: list[dict[str, str]] = []
openstreetmap_query_args: list[dict[str, str]] = []


def main() -> None:
    # reads and writes normalized locations to the local output file
    store = LocalDataStore()

    for args in google_places_query_args:
        # queries the Google Places API
        querier = GooglePlacesQuerier()
        raw_locations = querier.fetch()

        # maps Google Places payloads to the shared schema
        normalizer = GooglePlacesNormalizer()
        normalized_locations = normalizer.normalize(raw_locations)

        # writes the normalized locations to the local output file
        store.write_source_snapshot("google_places", normalized_locations)

    for args in openstreetmap_query_args:
        # queries the OpenStreetMap API
        querier = OpenStreetMapQuerier()
        raw_locations = querier.fetch()

        # maps OpenStreetMap payloads to the shared schema
        normalizer = OpenStreetMapNormalizer()
        normalized_locations = normalizer.normalize(raw_locations)

        # writes the normalized locations to the local output file
        store.write_source_snapshot("openstreetmap", normalized_locations)

    print("scrape-to-local finished")


if __name__ == "__main__":
    main()
