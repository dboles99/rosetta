# tests/test_cpn.py
from rosetta_core.cpn import serialize_packet, parse_packet


def test_serialize_sorts_keys_and_stamps_schema_ver_first():
    text = serialize_packet("1.0", {"TASK": "ENTITY_RESOLUTION", "GEO": "TH,TW,US"})
    lines = text.splitlines()
    assert lines[0] == "SCHEMA_VER=1.0"
    assert lines[1:] == ["GEO=TH,TW,US", "TASK=ENTITY_RESOLUTION"]


def test_serialize_formats_floats_to_two_decimals():
    text = serialize_packet("1.0", {"ID_THRESHOLD": 0.9})
    assert "ID_THRESHOLD=0.90" in text.splitlines()


def test_serialize_is_deterministic_across_calls():
    fields = {"B": 1, "A": "x", "C": 2.5}
    assert serialize_packet("1.0", fields) == serialize_packet("1.0", dict(reversed(fields.items())))


def test_serialize_ends_with_single_trailing_newline():
    text = serialize_packet("1.0", {"TASK": "VERIFICATION"})
    assert text.endswith("\n")
    assert not text.endswith("\n\n")


def test_parse_recovers_schema_ver_and_fields():
    text = "SCHEMA_VER=1.0\nGEO=TH,TW,US\nTASK=ENTITY_RESOLUTION\n"
    schema_ver, fields = parse_packet(text)
    assert schema_ver == "1.0"
    assert fields == {"GEO": "TH,TW,US", "TASK": "ENTITY_RESOLUTION"}


def test_parse_missing_schema_ver_raises():
    import pytest
    with pytest.raises(ValueError, match="SCHEMA_VER"):
        parse_packet("TASK=VERIFICATION\n")


def test_parse_ignores_blank_lines():
    schema_ver, fields = parse_packet("SCHEMA_VER=1.0\n\nTASK=VERIFICATION\n\n")
    assert fields == {"TASK": "VERIFICATION"}
