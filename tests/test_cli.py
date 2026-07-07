import json
from pathlib import Path
from rosetta_core.cli import main
from rosetta_core.fields import FieldsStore

SCHEMA = {
    "type": "object",
    "required": ["TASK", "SCHEMA_VER"],
    "properties": {"TASK": {"type": "string", "enum": ["ENTITY_RESOLUTION"]}},
}


def _setup(tmp_path: Path):
    FieldsStore(schema_ver="1.0", fields={"TASK": "ENTITY_RESOLUTION"}).save(tmp_path / "policy.fields.json")
    (tmp_path / "policy.schema.json").write_text(json.dumps(SCHEMA), encoding="utf-8")


def test_sync_command_bootstraps(tmp_path: Path, capsys):
    _setup(tmp_path)
    code = main(["sync", "policy", "--dir", str(tmp_path)])
    assert code == 0
    assert "bootstrap" in capsys.readouterr().out
    assert (tmp_path / "policy.cpn").exists()


def test_compile_is_an_alias_for_sync(tmp_path: Path, capsys):
    _setup(tmp_path)
    code = main(["compile", "policy", "--dir", str(tmp_path)])
    assert code == 0
    assert (tmp_path / "policy.md").exists()


def test_validate_command_reports_valid(tmp_path: Path, capsys):
    _setup(tmp_path)
    code = main(["validate", "policy", "--dir", str(tmp_path)])
    assert code == 0
    assert "valid" in capsys.readouterr().out


def test_validate_command_reports_invalid(tmp_path: Path, capsys):
    FieldsStore(schema_ver="1.0", fields={"TASK": "WRONG"}).save(tmp_path / "policy.fields.json")
    (tmp_path / "policy.schema.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
    code = main(["validate", "policy", "--dir", str(tmp_path)])
    assert code == 1
    assert "INVALID" in capsys.readouterr().err


def test_expand_command_prints_human_doc_without_writing(tmp_path: Path, capsys):
    _setup(tmp_path)
    code = main(["expand", "policy", "--dir", str(tmp_path)])
    assert code == 0
    assert "TASK" in capsys.readouterr().out or "ENTITY_RESOLUTION" in capsys.readouterr().out
    assert not (tmp_path / "policy.md").exists()
