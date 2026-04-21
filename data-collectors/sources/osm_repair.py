"""Example data-collector: repair shops from OpenStreetMap via Overpass.

Overpass returns everything in one response (no pagination), so the
Querier yields a single page and stops. The Normalizer maps each
element to a ``service_providers`` row, using
``(source, source_id)`` as the dedup key.

Contributors adding a new source should use this file as a template:
one Querier subclass, one Normalizer subclass, no extra plumbing.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from framework import (
    BaseNormalizer,
    BaseQuerier,
    RawQueryResponse,
    RawSQLQuery,
)

OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"

# Greater Boston bounding box: (south, west, north, east).
GREATER_BOSTON_BBOX = (42.2, -71.2, 42.5, -70.9)

OVERPASS_QUERY_TEMPLATE = """
[out:json][timeout:25];
nwr["repair"]({bbox});
out center;
""".strip()


class OsmRepairQuerier(BaseQuerier):
    """Fetches repair-tagged OSM elements within a bounding box.

    Overpass does not paginate, so ``get_page`` returns the full payload
    on page 0 and ``None`` thereafter.
    """

    source = "osm_repair"
    page_delay_seconds = 1.0  # Be polite to the public Overpass instance.

    def __init__(
        self,
        bbox: tuple[float, float, float, float] = GREATER_BOSTON_BBOX,
    ) -> None:
        self.bbox = bbox

    def get_page(self, page: int) -> RawQueryResponse | None:
        if page > 0:
            return None

        query = OVERPASS_QUERY_TEMPLATE.format(
            bbox=",".join(str(x) for x in self.bbox)
        )
        body = urllib.parse.urlencode({"data": query}).encode("utf-8")
        request = urllib.request.Request(
            OVERPASS_ENDPOINT, data=body, method="POST"
        )
        with urllib.request.urlopen(request) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return RawQueryResponse(
            source=self.source, page=page, payload=payload
        )


class OsmRepairNormalizer(BaseNormalizer):
    """Maps Overpass elements to ``service_providers`` rows."""

    TABLE = "service_providers"

    def normalize(self, response: RawQueryResponse) -> list[RawSQLQuery]:
        records: list[RawSQLQuery] = []
        for element in response.payload.get("elements", []):
            record = self._normalize_element(element, response)
            if record is not None:
                records.append(record)
        return records

    def _normalize_element(
        self,
        element: dict[str, Any],
        response: RawQueryResponse,
    ) -> RawSQLQuery | None:
        tags = element.get("tags", {})
        name = tags.get("name")
        if not name:
            # OSM has plenty of untagged / unnamed nodes; skip them
            # rather than persist rows that won't render in the UI.
            return None

        # `way` and `relation` elements carry coordinates under `center`;
        # plain `node` elements have lat/lon at the top level.
        lat = element.get("lat") or element.get("center", {}).get("lat")
        lon = element.get("lon") or element.get("center", {}).get("lon")

        values = {
            "source": response.source,
            "source_id": f"{element['type']}/{element['id']}",
            "name": name,
            "latitude": lat,
            "longitude": lon,
            "street_address": self._street_address(tags),
            "phone": tags.get("phone") or tags.get("contact:phone"),
            "website": tags.get("website") or tags.get("contact:website"),
            "raw_tags": json.dumps(tags),
            "fetched_at": response.fetched_at,
        }

        return RawSQLQuery(
            table=self.TABLE,
            values=values,
            dedup_key=("source", "source_id"),
            source=response.source,
            fetched_at=response.fetched_at,
        )

    @staticmethod
    def _street_address(tags: dict[str, Any]) -> str | None:
        number = tags.get("addr:housenumber")
        street = tags.get("addr:street")
        if number and street:
            return f"{number} {street}"
        return street
