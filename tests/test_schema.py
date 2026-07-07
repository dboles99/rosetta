import pytest
from rosetta_core.schema import validate_fields, SchemaValidationError

SCHEMA = {
    "type": "object",
    "required": ["TASK", "SCHEMA_VER"],
    "properties": {
        "TASK": {"type": "string", "enum": ["ENTITY_RESOLUTION", "VERIFICATION"]},
        "ID_THRESHOLD": {"type": "number", "minimum": 0, "maximum": 1},
        "SCHEMA_VER": {"type": "string", "pattern": r"^\d+\.\d+$"},
    },
}


def test_valid_fields_pass():
    validate_fields({"TASK": "ENTITY_RESOLUTION", "SCHEMA_VER": "1.0"}, SCHEMA)


def test_missing_required_field_raises():
    with pytest.raises(SchemaValidationError) as exc_info:
        validate_fields({"TASK": "ENTITY_RESOLUTION"}, SCHEMA)
    assert any("SCHEMA_VER" in msg for msg in exc_info.value.errors)


def test_bad_enum_value_raises():
    with pytest.raises(SchemaValidationError) as exc_info:
        validate_fields({"TASK": "NOT_A_TASK", "SCHEMA_VER": "1.0"}, SCHEMA)
    assert len(exc_info.value.errors) == 1


def test_stringly_typed_number_from_cpn_coerces_and_passes():
    fields = {"TASK": "ENTITY_RESOLUTION", "SCHEMA_VER": "1.0", "ID_THRESHOLD": "0.92"}
    validate_fields(fields, SCHEMA)


def test_stringly_typed_integer_coerces_and_passes():
    schema = {
        "type": "object",
        "properties": {"COUNT": {"type": "integer"}},
    }
    validate_fields({"COUNT": "3"}, schema)


def test_genuinely_invalid_number_string_still_raises():
    fields = {"TASK": "ENTITY_RESOLUTION", "SCHEMA_VER": "1.0", "ID_THRESHOLD": "not_a_number"}
    with pytest.raises(SchemaValidationError) as exc_info:
        validate_fields(fields, SCHEMA)
    assert any("ID_THRESHOLD" in msg for msg in exc_info.value.errors)


def test_native_typed_value_unaffected_by_coercion():
    fields = {"TASK": "ENTITY_RESOLUTION", "SCHEMA_VER": "1.0", "ID_THRESHOLD": 0.5}
    validate_fields(fields, SCHEMA)


def test_coercion_does_not_mutate_caller_fields_dict():
    fields = {"TASK": "ENTITY_RESOLUTION", "SCHEMA_VER": "1.0", "ID_THRESHOLD": "0.92"}
    original = dict(fields)
    validate_fields(fields, SCHEMA)
    assert fields == original
