from etl.base.normalizer import BaseNormalizer
from etl.dtos import RawLocation, NormalizedLocation


class OpenStreetMapNormalizer(BaseNormalizer):

    def normalize(self, raw_locations: list[RawLocation]) -> list[NormalizedLocation]:
        pass
