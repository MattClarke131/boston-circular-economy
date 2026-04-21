"""Abstract base classes and DTOs for the data-collector framework.

A data source is implemented as a Querier + Normalizer pair:

  - The Querier knows how to talk to an external API: authentication,
    pagination, rate limiting, retries.
  - The Normalizer knows how to map the API's response shape onto our
    database records.

These two classes are deliberately kept separate. Splitting them lets us
swap one without touching the other (e.g. reuse a single Querier with
multiple Normalizers when one API feeds multiple tables), and it keeps
each subclass focused on one concern.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------


@dataclass
class RawQueryResponse:
    """One page of results as returned by a Querier.

    The Querier fills this envelope; the Normalizer consumes it. The
    `payload` is the raw API response (typically parsed JSON) and its
    shape is source-specific.
    """

    source: str
    """Stable identifier for the data source (e.g. 'osm_repair')."""

    page: int
    """Zero-indexed page number this envelope represents."""

    payload: Any
    """The raw API response body. Shape is source-specific."""

    fetched_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    """UTC timestamp the response was received at."""


@dataclass
class RawSQLQuery:
    """A database-ready record produced by a Normalizer.

    `SqlIngester` consumes these and turns them into upserts. Keeping
    this DTO free of anything source-specific is what lets a single
    ingester serve every data source.
    """

    table: str
    """Name of the target database table."""

    values: dict[str, Any]
    """Column -> value map to upsert."""

    dedup_key: tuple[str, ...]
    """Names of the columns (subset of `values`) that uniquely identify
    this record across sources and repeated fetches. The ingester
    resolves conflicts between rows that share the same dedup_key
    values."""

    source: str
    """Source identifier, propagated from RawQueryResponse.source.
    Used by source-priority merge strategies."""

    fetched_at: datetime
    """Propagated from the RawQueryResponse so the ingester can apply
    newest-wins merge rules without reaching back to the envelope."""


# ---------------------------------------------------------------------------
# Abstract base classes
# ---------------------------------------------------------------------------


class BaseQuerier(ABC):
    """Abstract base for source-specific queriers.

    Subclasses implement :meth:`get_page` to fetch a single page from
    the target API. The framework provides :meth:`fetch`, a generator
    that pages through the API and yields one `RawQueryResponse` at a
    time, sleeping for `page_delay_seconds` between pages.

    Subclasses set:
      - ``source``: stable identifier, stamped onto each envelope.
      - ``page_delay_seconds`` (optional): seconds to sleep between
        pages. Defaults to 0 (no throttling). Set this to respect the
        API's rate limit.
    """

    source: str
    page_delay_seconds: float = 0.0

    @abstractmethod
    def get_page(self, page: int) -> RawQueryResponse | None:
        """Fetch a single page.

        Return ``None`` to signal that there are no more pages. Page
        numbers start at 0. APIs that don't paginate should return the
        full response for page 0 and ``None`` for page 1.
        """

    def fetch(self) -> Iterator[RawQueryResponse]:
        """Yield one `RawQueryResponse` per page until exhausted."""
        page = 0
        while True:
            response = self.get_page(page)
            if response is None:
                return
            yield response
            page += 1
            if self.page_delay_seconds:
                time.sleep(self.page_delay_seconds)


class BaseNormalizer(ABC):
    """Abstract base for source-specific normalizers.

    A Normalizer takes one `RawQueryResponse` and returns the list of
    `RawSQLQuery` records it represents. Normalizers own the source's
    data domain: which fields map to which columns, what constitutes a
    duplicate (`dedup_key`), and any per-source validation.
    """

    @abstractmethod
    def normalize(self, response: RawQueryResponse) -> list[RawSQLQuery]:
        """Map one API response page to a list of database-ready records."""
