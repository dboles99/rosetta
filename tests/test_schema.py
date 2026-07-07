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
