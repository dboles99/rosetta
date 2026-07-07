# tests/test_loader.py
from pathlib import Path

from rosetta_core.loader import load_prompt

SCHEMA = {
    "type": "object",
    "required": ["TASK", "SCHEMA_VER"],
    "properties": {"TASK": {"type": "string", "enum": ["ENTITY_RESOLUTION"]}},
}


def test_loads_valid_packet(tmp_path: Path):
    (tmp_path / "policy.cpn").write_text("SCHEMA_VER=1.0\nTASK=ENTITY_RESOLUTION\n", encoding="utf-8")
    text = load_prompt("policy", tmp_path, SCHEMA)
    assert text == "SCHEMA_VER=1.0\nTASK=ENTITY_RESOLUTION\n"


def test_falls_back_to_human_doc_when_packet_missing(tmp_path: Path):
    (tmp_path / "policy.md").write_text("# Policy\nFallback prose.\n", encoding="utf-8")
    text = load_prompt("policy", tmp_path, SCHEMA)
    assert text == "# Policy\nFallback prose.\n"


def test_falls_back_to_human_doc_when_packet_fails_schema(tmp_path: Path):
    (tmp_path / "policy.cpn").write_text("SCHEMA_VER=1.0\nTASK=NOT_VALID\n", encoding="utf-8")
    (tmp_path / "policy.md").write_text("# Policy\nFallback prose.\n", encoding="utf-8")
    text = load_prompt("policy", tmp_path, SCHEMA)
    assert text == "# Policy\nFallback prose.\n"


def test_raises_when_both_missing(tmp_path: Path):
    import pytest
    from rosetta_core.loader import PacketUnavailable

    with pytest.raises(PacketUnavailable):
        load_prompt("policy", tmp_path, SCHEMA)
