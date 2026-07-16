from etl.local_data_store import LocalDataStore
from etl.merge_processor import MergeProcessor


def main() -> None:
    # reads normalized locations from the local store
    # writes merged locations back to the local store
    store = LocalDataStore()
    processor = MergeProcessor(store)
    processor.process()

    print("merge-process-to-local finished")


if __name__ == "__main__":
    main()
