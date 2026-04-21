"""Data-collector framework.

Three classes, wired by :func:`run`:

  - :class:`BaseQuerier`    - fetches pages from the source API (subclass me).
  - :class:`BaseNormalizer` - maps raw responses to DB records (subclass me).
  - :class:`SqlIngester`    - persists records via upsert (use directly).

A data source lives in ``sources/`` as a pair of subclasses (one
Querier, one Normalizer). See ``sources/osm_repair.py`` for an example.
"""

from .base import (
    BaseNormalizer,
    BaseQuerier,
    RawQueryResponse,
    RawSQLQuery,
)
from .ingester import SqlIngester, newest_wins, non_null_wins
from .runner import run

__all__ = [
    "BaseNormalizer",
    "BaseQuerier",
    "RawQueryResponse",
    "RawSQLQuery",
    "SqlIngester",
    "newest_wins",
    "non_null_wins",
    "run",
]
