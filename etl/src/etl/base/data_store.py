from abc import ABC, abstractmethod

from etl.dtos import NormalizedLocation


class BaseDataStore(ABC):
    """
    Subclass this to implement a new storage backend.
    """

    @abstractmethod
    def write_source_snapshot(
        self,
        source: str,
        normalized_locations: list[NormalizedLocation],
    ) -> None:
        pass

    @abstractmethod
    def read_source_snapshot(
        self,
        source: str,
    ) -> list[NormalizedLocation]:
        pass

    @abstractmethod
    def write_output_locations(
        self,
        output_locations: list[NormalizedLocation],
    ) -> None:
        pass
