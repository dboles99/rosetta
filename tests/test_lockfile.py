from pathlib import Path
from rosetta_core.lockfile import Lockfile


def test_load_or_default_returns_empty_hashes_when_missing(tmp_path: Path):
    lock = Lockfile.load_or_default(tmp_path / "missing.lock")
    assert lock.human_hash == ""
    assert lock.machine_hash == ""


def test_save_then_load_round_trips(tmp_path: Path):
    p = tmp_path / "name.rosetta.lock"
    Lockfile(human_hash="abc", machine_hash="def").save(p)
    loaded = Lockfile.load_or_default(p)
    assert loaded.human_hash == "abc"
    assert loaded.machine_hash == "def"
