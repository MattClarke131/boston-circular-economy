"""
    Maps Overpass elements to NormalizedLocations.

    Each RawLocation payload is one Overpass element. Its fields live in `tags`.
    See https://wiki.openstreetmap.org/wiki/Map_features for tag meanings.
"""
from contracts.domain import Address, Availability, Contact, NormalizedLocation

from etl.base.normalizer import BaseNormalizer
from etl.dtos import RawLocation


# Tags to try, in order, for each field. OSM has both a plain key and a
# `contact:` prefixed key for most contact details, and mappers use either.
NAME_TAGS = ("name", "brand", "operator")
PHONE_TAGS = ("phone", "contact:phone")
EMAIL_TAGS = ("email", "contact:email")
WEBSITE_TAGS = ("website", "contact:website", "url")
SOCIAL_TAGS = ("contact:facebook", "contact:instagram", "facebook", "instagram")
LAST_VERIFIED_TAGS = ("check_date", "survey:date")


class OpenStreetMapNormalizer(BaseNormalizer):

    def normalize(self, raw_locations: list[RawLocation]) -> list[NormalizedLocation]:
        normalized_locations = []
        for raw_location in raw_locations:
            normalized_location = self._normalize_one(raw_location)
            if normalized_location is not None:
                normalized_locations.append(normalized_location)
        return normalized_locations

    def _normalize_one(self, raw_location: RawLocation) -> NormalizedLocation | None:
        """Return None for elements we can't show on a map: no name or no coordinates."""
        element = raw_location.payload
        tags = element.get("tags", {})

        name = first_tag(tags, NAME_TAGS)
        coordinates = element_coordinates(element)
        if name is None or coordinates is None:
            return None
        lat, lon = coordinates

        return NormalizedLocation(
            data_source_id=raw_location.data_source_id,
            data_source=raw_location.data_source,
            name=name,
            lat=lat,
            lon=lon,
            address=build_address(tags),
            contact=Contact(
                phone=first_tag(tags, PHONE_TAGS),
                email=first_tag(tags, EMAIL_TAGS),
                website=first_tag(tags, WEBSITE_TAGS),
                social=first_tag(tags, SOCIAL_TAGS),
            ),
            services=list(self.services),
            availability=Availability(opening_hours=tags.get("opening_hours")),
            last_verified=first_tag(tags, LAST_VERIFIED_TAGS),
        )


def first_tag(tags: dict, keys: tuple[str, ...]) -> str | None:
    """Return the first non-blank value among `keys`, stripped, or None."""
    for key in keys:
        value = tags.get(key, "").strip()
        if value:
            return value
    return None


def element_coordinates(element: dict) -> tuple[float, float] | None:
    """Nodes carry lat/lon directly. Ways and relations carry them under `center`."""
    if "lat" in element and "lon" in element:
        return element["lat"], element["lon"]
    center = element.get("center")
    if center:
        return center["lat"], center["lon"]
    return None


def build_address(tags: dict) -> Address:
    # Join house number and street, e.g. "6" + "Fordham Road" -> "6 Fordham Road".
    street_parts = [tags.get("addr:housenumber"), tags.get("addr:street")]
    street = " ".join(part for part in street_parts if part) or None
    return Address(
        street=street,
        city=tags.get("addr:city"),
        state=tags.get("addr:state"),
        postcode=tags.get("addr:postcode"),
    )
