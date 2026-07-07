import json
from pathlib import Path
from rosetta_core.fields import FieldsStore


def test_load_reads_schema_ver_and_fields(tmp_path: Path):
    p = tmp_path / "entity_resolution.fields.json"
    p.write_text(
        json.dumps({"schema_ver": "1.0", "fields": {"TASK": "ENTITY_RESOLUTION", "ID_THRESHOLD": 0.92}}),
        encoding="utf-8",
    )
    store = FieldsStore.load(p)
    assert store.schema_ver == "1.0"
    assert store.fields == {"TASK": "ENTITY_RESOLUTION", "ID_THRESHOLD": 0.92}


def test_save_then_load_round_trips(tmp_path: Path):
    p = tmp_path / "roundtrip.fields.json"
    store = FieldsStore(schema_ver="1.0", fields={"TASK": "VERIFICATION"})
    store.save(p)
    loaded = FieldsStore.load(p)
    assert loaded.schema_ver == store.schema_ver
    assert loaded.fields == store.fields


def test_fields_with_schema_ver_merges():
    store = FieldsStore(schema_ver="1.0", fields={"TASK": "VERIFICATION"})
    merged = store.fields_with_schema_ver()
    assert merged == {"TASK": "VERIFICATION", "SCHEMA_VER": "1.0"}
    # original fields dict must be untouched
    assert store.fields == {"TASK": "VERIFICATION"}
