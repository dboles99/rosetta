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


def test_save_uses_unix_line_endings(tmp_path: Path):
    """Verify that saved files use Unix \\n line endings, not Windows \\r\\n.

    This test catches defects that would be hidden by read_text()'s universal-newline
    handling. We read in binary mode to verify the actual on-disk bytes.
    """
    p = tmp_path / "unix_endings.fields.json"
    store = FieldsStore(schema_ver="1.0", fields={"TASK": "VERIFICATION", "VALUE": "test"})
    store.save(p)

    # Read file in binary mode to check actual on-disk bytes
    file_bytes = p.read_bytes()

    # Assert no Windows line endings exist in the file
    assert b"\r\n" not in file_bytes, "File contains Windows line endings (\\r\\n) instead of Unix (\\n)"

    # Verify that the file does end with a Unix newline
    assert file_bytes.endswith(b"\n"), "File must end with Unix newline"
