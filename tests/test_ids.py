import pytest

from ha_catalogue.ids import (
    find_catalogue_references,
    parse_catalogue_id,
    parse_plain_number,
    parse_reserved_range,
)


@pytest.mark.parametrize(
    ("raw", "catalogue", "number", "leftover"),
    [
        ("189.13 (527)       ", "189.13", "527", ""),
        ("189.0 (10)    ", "189.0", "10", ""),
        ("189.1.(29A)", "189.1", "29a", ""),
        ("189.9a (146)", "189.9a", "146", ""),
        ("189.22 (96)\xa0\xa0\xa0\xa0 e", "189.22", "96", "e"),
    ],
)
def test_parse_catalogue_id(raw, catalogue, number, leftover):
    parsed = parse_catalogue_id(raw)
    assert parsed is not None
    assert (parsed.catalogue, parsed.number, parsed.leftover) == (catalogue, number, leftover)


def test_parse_catalogue_id_rejects_garbage():
    assert parse_catalogue_id("Local History") is None


def test_parse_plain_number():
    assert parse_plain_number(" 12 ") == "12"
    assert parse_plain_number("") is None
    assert parse_plain_number("3476-3500 duvKv") is None


def test_parse_reserved_range():
    assert parse_reserved_range("3476-3500 duvKv  ") == (3476, 3500)
    assert parse_reserved_range("12") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("(See Indigenous Communities 155/155a)", ("155", "155a")),
        ("(See Family Planning 104)", ("104",)),
        ("36NAZ (also 400.3.10)", ("36naz", "400.3.10")),
        ("(see Census 55) also 55", ("55",)),
        ("(See ........ )", ()),
    ],
)
def test_find_catalogue_references(text, expected):
    assert find_catalogue_references(text) == expected
