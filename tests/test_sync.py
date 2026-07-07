import pytest
from pathlib import Path
from rosetta_core.fields import FieldsStore
from rosetta_core.sync import sync, SyncConflict

FIELDS = {"TASK": "ENTITY_RESOLUTION", "ID_THRESHOLD": 0.92}
DESCRIPTIONS = {"TASK": "Task", "ID_THRESHOLD": "Identity match threshold"}


def _write_fields(directory: Path, name: str, fields: dict):
    FieldsStore(schema_ver="1.0", fields=fields).save(directory / f"{name}.fields.json")


def test_bootstrap_creates_both_views_from_fields(tmp_path: Path):
    _write_fields(tmp_path, "entity_resolution", FIELDS)
    result = sync("entity_resolution", tmp_path, "Entity Resolution Policy", DESCRIPTIONS)
    assert result == "bootstrap"
    assert (tmp_path / "entity_resolution.cpn").exists()
    assert (tmp_path / "entity_resolution.md").exists()
    assert (tmp_path / "entity_resolution.rosetta.lock").exists()


def test_second_sync_with_no_changes_is_noop(tmp_path: Path):
    _write_fields(tmp_path, "entity_resolution", FIELDS)
    sync("entity_resolution", tmp_path, "Entity Resolution Policy", DESCRIPTIONS)
    result = sync("entity_resolution", tmp_path, "Entity Resolution Policy", DESCRIPTIONS)
    assert result == "no-op"


def test_editing_machine_packet_propagates_to_human_doc(tmp_path: Path):
    _write_fields(tmp_path, "entity_resolution", FIELDS)
    sync("entity_resolution", tmp_path, "Entity Resolution Policy", DESCRIPTIONS)
    cpn_path = tmp_path / "entity_resolution.cpn"
    cpn_path.write_text(cpn_path.read_text(encoding="utf-8").replace("0.92", "0.95"), encoding="utf-8")

    result = sync("entity_resolution", tmp_path, "Entity Resolution Policy", DESCRIPTIONS)

    assert result == "machine-to-human"
    md_text = (tmp_path / "entity_resolution.md").read_text(encoding="utf-8")
    assert "0.95" in md_text


def test_editing_human_doc_fields_comment_propagates_to_machine_packet(tmp_path: Path):
    _write_fields(tmp_path, "entity_resolution", FIELDS)
    sync("entity_resolution", tmp_path, "Entity Resolution Policy", DESCRIPTIONS)
    md_path = tmp_path / "entity_resolution.md"
    md_path.write_text(md_path.read_text(encoding="utf-8").replace("0.92", "0.97"), encoding="utf-8")

    result = sync("entity_resolution", tmp_path, "Entity Resolution Policy", DESCRIPTIONS)

    assert result == "human-to-machine"
    cpn_text = (tmp_path / "entity_resolution.cpn").read_text(encoding="utf-8")
    assert "0.97" in cpn_text


def test_editing_notes_region_resyncs_but_preserves_fields(tmp_path: Path):
    """Notes-only edits still change the .md file's whole-content hash, so sync
    runs the human-to-machine path — but the FIELDS comment is untouched, so
    fields (and therefore the recompiled .cpn) come out identical."""
    _write_fields(tmp_path, "entity_resolution", FIELDS)
    sync("entity_resolution", tmp_path, "Entity Resolution Policy", DESCRIPTIONS)
    md_path = tmp_path / "entity_resolution.md"
    text = md_path.read_text(encoding="utf-8")
    start = text.index("<!-- ROSETTA:NOTES")
    end = text.index("<!-- /ROSETTA:NOTES -->") + len("<!-- /ROSETTA:NOTES -->")
    notes_block = text[start:end]
    new_notes_block = notes_block.split("-->", 1)[0] + "-->\nnew note\n<!-- /ROSETTA:NOTES -->"
    text = text[:start] + new_notes_block + text[end:]
    md_path.write_text(text, encoding="utf-8")
    cpn_before = (tmp_path / "entity_resolution.cpn").read_text(encoding="utf-8")

    result = sync("entity_resolution", tmp_path, "Entity Resolution Policy", DESCRIPTIONS)

    assert result == "human-to-machine"
    assert "new note" in md_path.read_text(encoding="utf-8")
    assert (tmp_path / "entity_resolution.cpn").read_text(encoding="utf-8") == cpn_before


def test_both_sides_changed_raises_conflict(tmp_path: Path):
    _write_fields(tmp_path, "entity_resolution", FIELDS)
    sync("entity_resolution", tmp_path, "Entity Resolution Policy", DESCRIPTIONS)
    cpn_path = tmp_path / "entity_resolution.cpn"
    md_path = tmp_path / "entity_resolution.md"
    cpn_path.write_text(cpn_path.read_text(encoding="utf-8").replace("0.92", "0.95"), encoding="utf-8")
    md_path.write_text(md_path.read_text(encoding="utf-8").replace("0.92", "0.97"), encoding="utf-8")

    with pytest.raises(SyncConflict) as exc_info:
        sync("entity_resolution", tmp_path, "Entity Resolution Policy", DESCRIPTIONS)

    assert "ID_THRESHOLD" in exc_info.value.differing_keys
