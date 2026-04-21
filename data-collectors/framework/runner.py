"""End-to-end runner that wires a Querier, Normalizer, and Ingester."""

from __future__ import annotations

import logging

from .base import BaseNormalizer, BaseQuerier
from .ingester import SqlIngester

logger = logging.getLogger(__name__)


def run(
    querier: BaseQuerier,
    normalizer: BaseNormalizer,
    ingester: SqlIngester,
) -> int:
    """Run the fetch -> normalize -> persist pipeline to completion.

    Iterates the Querier's pagination generator, normalizes each page,
    and hands the resulting records to the Ingester. Returns the total
    number of rows written across all pages.

    Memory stays bounded to a single page at a time.
    """
    total = 0
    for response in querier.fetch():
        records = normalizer.normalize(response)
        written = ingester.write(records)
        total += written
        logger.info(
            "source=%s page=%d fetched=%d written=%d",
            response.source,
            response.page,
            len(records),
            written,
        )
    return total
