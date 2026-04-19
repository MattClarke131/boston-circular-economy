from abc import ABC, abstractmethod

from data_transfer_objects import FetchResponse, SQLQuery


class BaseJob(ABC):

    # Fetch all raw data from the source. Make as many requests as needed.
    # Return one FetchResponse per request made.
    @abstractmethod
    def fetch(self) -> list[FetchResponse]:
        pass

    # Transform raw responses into SQL-ready records.
    @abstractmethod
    def normalize(self, responses: list[FetchResponse]) -> list[SQLQuery]:
        pass
