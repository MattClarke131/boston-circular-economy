from datetime import datetime, timezone

from base_job import BaseJob
from data_transfer_objects import FetchResponse, SQLQuery


class ExampleJob(BaseJob):

    def fetch(self) -> list[FetchResponse]:
        return [
            FetchResponse(
                source="example",
                fetched_at=datetime.now(timezone.utc),
                payload={},
            )
        ]

    def normalize(self, responses: list[FetchResponse]) -> list[SQLQuery]:
        return []
