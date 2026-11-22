from datetime import datetime, timezone

import pytest
from contracts.domain import Activity, DataSource, ItemCategory, Service

from etl.dtos import RawLocation
from etl.sources.openstreetmap.normalizer import OpenStreetMapNormalizer

CLOTHING_REPAIR = Service(activity=Activity.REPAIR_PAID, item_category=ItemCategory.CLOTHING)

# Based on a real element from data-explorations/openstreetmap/samples/repair-00.json.
FULL_NODE = {
    "type": "node",
    "id": 9659819117,
    "lat": 42.3519623,
    "lon": -71.1276676,
    "tags": {
        "addr:city": "Allston",
        "addr:housenumber": "6",
        "addr:postcode": "02134",
        "addr:state": "MA",
        "addr:street": "Fordham Road",
        "check_date": "2025-02-03",
        "contact:facebook": "https://www.facebook.com/p/The-Computer-Loft-100063792390864/",
        "email": "service@computerloft.com",
        "name": "The Computer Loft",
        "opening_hours": "Mo-Fr 10:00-18:00; Sa,Su off",
        "phone": "+1-617-782-9997",
        "shop": "computer",
        "website": "https://www.computerloft.com/",
    },
}

WAY_WITH_CENTER = {
    "type": "way",
    "id": 674356526,
    "center": {"lat": 42.4626283, "lon": -70.9473823},
    "nodes": [6315476620, 6315476621],
    "tags": {"name": "The Salvation Army", "shop": "charity"},
}


def raw(element: dict) -> RawLocation:
    return RawLocation(
        data_source=DataSource.OPENSTREETMAP,
        data_source_id=f"{element['type']}/{element['id']}",
        fetched_at=datetime.now(timezone.utc),
        payload=element,
    )


def node(**tags) -> dict:
    return {"type": "node", "id": 1, "lat": 42.0, "lon": -71.0, "tags": tags}


@pytest.fixture
def normalizer():
    return OpenStreetMapNormalizer(services=[CLOTHING_REPAIR])


def normalize_one(normalizer, element):
    [location] = normalizer.normalize([raw(element)])
    return location


def test_maps_all_fields_from_full_node(normalizer):
    location = normalize_one(normalizer, FULL_NODE)

    assert location.data_source is DataSource.OPENSTREETMAP
    assert location.data_source_id == "node/9659819117"
    assert location.name == "The Computer Loft"
    assert (location.lat, location.lon) == (42.3519623, -71.1276676)
    assert location.address.street == "6 Fordham Road"
    assert location.address.city == "Allston"
    assert location.address.state == "MA"
    assert location.address.postcode == "02134"
    assert location.contact.phone == "+1-617-782-9997"
    assert location.contact.email == "service@computerloft.com"
    assert location.contact.website == "https://www.computerloft.com/"
    assert location.contact.social == "https://www.facebook.com/p/The-Computer-Loft-100063792390864/"
    assert location.availability.opening_hours == "Mo-Fr 10:00-18:00; Sa,Su off"
    assert location.last_verified == "2025-02-03"


def test_services_come_from_the_query(normalizer):
    location = normalize_one(normalizer, FULL_NODE)

    assert location.services == [CLOTHING_REPAIR]


def test_way_uses_center_coordinates(normalizer):
    location = normalize_one(normalizer, WAY_WITH_CENTER)

    assert (location.lat, location.lon) == (42.4626283, -70.9473823)


def test_element_without_coordinates_is_dropped(normalizer):
    way_without_center = {"type": "way", "id": 2, "tags": {"name": "Somewhere"}}

    assert normalizer.normalize([raw(way_without_center)]) == []


@pytest.mark.parametrize(
    "tags, expected_name",
    [
        ({"name": "Boomerangs", "brand": "B", "operator": "O"}, "Boomerangs"),
        ({"brand": "Goodwill", "operator": "Morgan Memorial"}, "Goodwill"),
        ({"operator": "City of Cambridge"}, "City of Cambridge"),
        ({"name": "  ", "operator": "City of Cambridge"}, "City of Cambridge"),
    ],
)
def test_name_falls_back_to_brand_then_operator(normalizer, tags, expected_name):
    location = normalize_one(normalizer, node(**tags))

    assert location.name == expected_name


def test_element_without_any_name_is_dropped(normalizer):
    unnamed_bin = node(**{"amenity": "recycling", "recycling:clothes": "yes"})

    assert normalizer.normalize([raw(unnamed_bin)]) == []


def test_contact_prefixed_tags_are_used_when_plain_tags_are_missing(normalizer):
    element = node(**{
        "name": "Collins Office Systems",
        "contact:phone": "+1-781-648-1323",
        "contact:email": "info@example.com",
        "contact:website": "http://www.collinsofficesystems.net",
    })

    contact = normalize_one(normalizer, element).contact

    assert contact.phone == "+1-781-648-1323"
    assert contact.email == "info@example.com"
    assert contact.website == "http://www.collinsofficesystems.net"


def test_missing_optional_tags_become_none(normalizer):
    location = normalize_one(normalizer, node(name="Bare"))

    assert location.address.street is None
    assert location.address.city is None
    assert location.contact.phone is None
    assert location.contact.social is None
    assert location.availability.opening_hours is None
    assert location.last_verified is None


def test_street_without_house_number(normalizer):
    location = normalize_one(normalizer, node(name="X", **{"addr:street": "Main Street"}))

    assert location.address.street == "Main Street"


def test_element_without_tags_is_dropped(normalizer):
    assert normalizer.normalize([raw({"type": "node", "id": 3, "lat": 1.0, "lon": 2.0})]) == []


def test_keeps_valid_elements_and_drops_invalid_ones(normalizer):
    unnamed = node(amenity="recycling")

    result = normalizer.normalize([raw(FULL_NODE), raw(unnamed), raw(WAY_WITH_CENTER)])

    assert [r.data_source_id for r in result] == ["node/9659819117", "way/674356526"]


def test_empty_input_returns_empty_list(normalizer):
    assert normalizer.normalize([]) == []
