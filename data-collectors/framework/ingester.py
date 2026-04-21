"""Persistence layer: turns `RawSQLQuery` records into Postgres upserts.

The ingester is framework-owned and contributor-agnostic: it does not
know anything about any specific API or table. It only knows how to
group records by ``dedup_key``, apply per-column merge rules, and write
the resolved row.

This module ships a single concrete class, :class:`SqlIngester`. It is
named with the ``Sql`` prefix (rather than a bare ``Ingester``) because
we expect to add siblings later — e.g. a dry-run logger, or a
JSON-to-disk ingester for local development. Keeping the name specific
today avoids a rename when those arrive.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any, Callable

from .base import RawSQLQuery

logger = logging.getLogger(__name__)


# A merge strategy takes (existing_value, incoming_value) and returns
# the winner. The ingester calls one of these for every column when
# two records share a dedup_key.
MergeStrategy = Callable[[Any, Any], Any]


def newest_wins(existing: Any, incoming: Any) -> Any:
    """Incoming value always overwrites the existing one.

    Appropriate as the default because we feed pages in fetch order and
    later batches reflect fresher data.
    """
    return incoming


def non_null_wins(existing: Any, incoming: Any) -> Any:
    """Prefer whichever value is non-null; fall back to the incoming."""
    if incoming is None:
        return existing
    return incoming


class SqlIngester:
    """Persist `RawSQLQuery` records to a SQL database via upsert.

    Parameters
    ----------
    connection :
        A DB-API 2.0 compatible connection (e.g. ``psycopg.connect(...)``).
        Each call to :meth:`write` opens a single transaction that commits
        on success and rolls back on exception.
    merge_rules :
        Optional mapping from column name to a :data:`MergeStrategy`.
        Columns not listed fall back to ``default_merge``.
    default_merge :
        Strategy used for any column not in ``merge_rules``. Defaults to
        :func:`newest_wins`.
    """

    def __init__(
        self,
        connection: Any,
        *,
        merge_rules: dict[str, MergeStrategy] | None = None,
        default_merge: MergeStrategy = newest_wins,
    ) -> None:
        self.connection = connection
        self.merge_rules = merge_rules or {}
        self.default_merge = default_merge

    def write(self, records: Iterable[RawSQLQuery]) -> int:
        """Upsert one page of records in a single transaction.

        Records that share a ``(table, dedup_key)`` within this batch
        are merged column-by-column before we hit the database, so we
        issue one row per logical entity per page.

        Returns the number of rows upserted.
        """
        records = list(records)
        if not records:
            return 0

        merged: dict[tuple[str, tuple[Any, ...]], RawSQLQuery] = {}
        for record in records:
            key = (record.table, self._dedup_values(record))
            if key in merged:
                merged[key] = self._merge(merged[key], record)
            else:
                merged[key] = record

        # DB-API: using the connection as a context manager starts a
        # transaction that commits on success and rolls back on error.
        with self.connection:
            cursor = self.connection.cursor()
            for record in merged.values():
                self._upsert(cursor, record)

        logger.info("SqlIngester wrote %d rows", len(merged))
        return len(merged)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _merge(
        self, existing: RawSQLQuery, incoming: RawSQLQuery
    ) -> RawSQLQuery:
        """Reduce two records that share a dedup_key to a single record."""
        resolved: dict[str, Any] = {}
        all_columns = set(existing.values) | set(incoming.values)
        for column in all_columns:
            strategy = self.merge_rules.get(column, self.default_merge)
            resolved[column] = strategy(
                existing.values.get(column), incoming.values.get(column)
            )
        newer = (
            incoming
            if incoming.fetched_at >= existing.fetched_at
            else existing
        )
        return RawSQLQuery(
            table=newer.table,
            values=resolved,
            dedup_key=newer.dedup_key,
            source=newer.source,
            fetched_at=newer.fetched_at,
        )

    def _upsert(self, cursor: Any, record: RawSQLQuery) -> None:
        """Execute a single ``INSERT ... ON CONFLICT DO UPDATE``."""
        columns = list(record.values.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        column_list = ", ".join(columns)
        # EXCLUDED is Postgres's pseudo-table for the incoming values in
        # an ON CONFLICT clause; we use it to promote the upserted row.
        update_clause = ", ".join(
            f"{col} = EXCLUDED.{col}" for col in columns
        )
        sql = (
            f"INSERT INTO {record.table} ({column_list}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT ({', '.join(record.dedup_key)}) "
            f"DO UPDATE SET {update_clause}"
        )
        cursor.execute(sql, [record.values[col] for col in columns])

    @staticmethod
    def _dedup_values(record: RawSQLQuery) -> tuple[Any, ...]:
        """Extract the dedup_key values from the record's column map."""
        return tuple(record.values.get(col) for col in record.dedup_key)
