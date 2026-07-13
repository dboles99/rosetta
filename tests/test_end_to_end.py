from pathlib import Path
from rosetta_core.fields import FieldsStore
from rosetta_core.loader import load_prompt
from rosetta_core.sync import sync

SCHEMA = {
    "type": "object",
    "required": ["TASK", "SCOPE", "SCHEMA_VER"],
    "properties": {
        "TASK": {"type": "string", "enum": ["ENTITY_RESOLUTION"]},
        "SCOPE": {"type": "string"},
        "ID_THRESHOLD": {"type": "number", "minimum": 0, "maximum": 1},
        "SCHEMA_VER": {"type": "string", "pattern": r"^\d+\.\d+$"},
    },
}
DESCRIPTIONS = {"TASK": "Task", "SCOPE": "Scope", "ID_THRESHOLD": "Identity match threshold"}


def test_full_lifecycle_bootstrap_edit_and_runtime_fallback(tmp_path: Path):
    name = "entity_resolution"
    FieldsStore(
        schema_ver="1.0",
        fields={"TASK": "ENTITY_RESOLUTION", "SCOPE": "PUBLIC_ONLY", "ID_THRESHOLD": 0.92},
    ).save(tmp_path / f"{name}.fields.json")

    assert sync(name, tmp_path, "Entity Resolution Policy", DESCRIPTIONS) == "bootstrap"

    # Normal runtime path: only the compact packet is loaded.
    prompt = load_prompt(name, tmp_path, SCHEMA)
    assert prompt == (tmp_path / f"{name}.cpn").read_text(encoding="utf-8")
    assert "ID_THRESHOLD=0.92" in prompt

    # Corrupt the packet directly, simulating a runtime hotfix gone wrong.
    # Only the TASK value is invalidated; SCOPE and ID_THRESHOLD keep their
    # original valid values so this isolates the enum-validation failure
    # rather than also tripping the required-field check.
    cpn_path = tmp_path / f"{name}.cpn"
    corrupted = cpn_path.read_text(encoding="utf-8").replace(
        "TASK=ENTITY_RESOLUTION", "TASK=NOT_A_REAL_TASK"
    )
    cpn_path.write_text(corrupted, encoding="utf-8")

    # Loader falls back to the human doc rather than serving an invalid packet.
    fallback_prompt = load_prompt(name, tmp_path, SCHEMA)
    assert fallback_prompt == (tmp_path / f"{name}.md").read_text(encoding="utf-8")
    assert "Entity Resolution Policy" in fallback_prompt
