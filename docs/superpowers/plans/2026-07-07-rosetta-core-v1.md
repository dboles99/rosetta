# Rosetta Core (V1, PacketSpec) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `rosetta-core`, a Python package implementing the PacketSpec artifact kind from the design spec: a canonical fields store with two generated views (a compact `.cpn` machine packet and a human `.md` doc), bidirectional sync with explicit conflict detection, and a runtime loader that falls back from machine to human form on failure.

**Architecture:** Each Rosetta artifact is four files sharing a `<name>` stem in one directory: `<name>.fields.json` (canonical), `<name>.cpn` (machine view), `<name>.md` (human view), `<name>.rosetta.lock` (sync bookkeeping), plus a `<name>.schema.json` (JSON Schema for validation). A pure-function core (hashing, CPN serialization, human-doc rendering, schema validation) is orchestrated by a `sync()` function that compares hashes against the lockfile to decide which view regenerates the other, or raises a conflict. A thin CLI and a runtime loader sit on top.

**Tech Stack:** Python 3.11+, stdlib `argparse`/`json`/`hashlib`, `jsonschema` (schema validation), `pytest` (tests).

## Global Constraints

- Python 3.11+ only; no other runtime dependency besides `jsonschema` and `pytest`.
- All file I/O uses `encoding="utf-8"` explicitly — never rely on platform default encoding.
- All generated files (`.cpn`, `.md`, `.fields.json`, `.rosetta.lock`) use `\n` line endings, enforced in code (`.splitlines()` + explicit `"\n".join(...)`), independent of git's checkout line-ending behavior.
- Repo enforces LF on checkout via `.gitattributes` (Task 1) so the canonical serialization the design relies on for provider prompt-cache stability isn't silently rewritten to CRLF by Windows git checkout.
- V1 field values are restricted to `str`, `int`, `float` — no lists/bools/nested dicts (matches spec's "Open questions": nested dict-literal fields are deferred to a formal grammar later).
- No network calls anywhere in `rosetta-core` or its tests.

---

## File Structure

```
rosetta/
  .gitattributes                        # Task 1
  pyproject.toml                        # Task 1
  src/rosetta_core/
    __init__.py                         # Task 1
    hashing.py                          # Task 2
    schema.py                           # Task 3
    fields.py                           # Task 4
    cpn.py                              # Task 5
    human_doc.py                        # Task 6
    lockfile.py                         # Task 7
    sync.py                             # Task 8
    loader.py                           # Task 9
    cli.py                              # Task 10
  tests/
    test_hashing.py                     # Task 2
    test_schema.py                      # Task 3
    test_fields.py                      # Task 4
    test_cpn.py                         # Task 5
    test_human_doc.py                   # Task 6
    test_lockfile.py                    # Task 7
    test_sync.py                        # Task 8
    test_loader.py                      # Task 9
    test_cli.py                         # Task 10
    test_end_to_end.py                  # Task 12
  docs/decisions/
    rosetta_build.fields.json           # Task 11
    rosetta_build.schema.json           # Task 11
    rosetta_build.md                    # Task 11 (generated)
    rosetta_build.cpn                   # Task 11 (generated)
    rosetta_build.rosetta.lock          # Task 11 (generated)
```

---

### Task 1: Project scaffold

**Suggested tool:** Cline (fast, low-risk project scaffolding in an IDE).

**Files:**
- Create: `pyproject.toml`
- Create: `.gitattributes`
- Create: `src/rosetta_core/__init__.py`

**Interfaces:**
- Produces: an installable package `rosetta_core` importable from `tests/`, and a `pytest` command that runs cleanly with zero tests collected.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "rosetta-core"
version = "0.1.0"
description = "Dual-representation (human + machine) prompts and metadata"
requires-python = ">=3.11"
dependencies = [
    "jsonschema>=4.21",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
rosetta = "rosetta_core.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `.gitattributes` to force LF on all text artifacts**

```
* text=auto eol=lf
*.cpn text eol=lf
*.md text eol=lf
*.json text eol=lf
```

- [ ] **Step 3: Create the empty package `src/rosetta_core/__init__.py`**

```python
"""Rosetta core: dual-representation (human + machine) prompts and metadata."""
```

- [ ] **Step 4: Install in editable/dev mode and verify pytest collects zero tests without error**

Run: `pip install -e ".[dev]"`
Then run: `pytest -q`
Expected: `no tests ran` (exit code 5) or `0 items` — no import errors.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitattributes src/rosetta_core/__init__.py
git commit -m "Scaffold rosetta-core package"
```

---

### Task 2: Hashing helper

**Suggested tool:** Codex (small, pure, self-contained function).

**Files:**
- Create: `src/rosetta_core/hashing.py`
- Test: `tests/test_hashing.py`

**Interfaces:**
- Produces: `sha256_text(text: str) -> str`, used by every later task that needs staleness/conflict hashes.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hashing.py
from rosetta_core.hashing import sha256_text


def test_same_text_same_hash():
    assert sha256_text("abc") == sha256_text("abc")


def test_different_text_different_hash():
    assert sha256_text("abc") != sha256_text("abd")


def test_known_sha256_of_empty_string():
    assert sha256_text("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"[:64]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_hashing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_core.hashing'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/rosetta_core/hashing.py
import hashlib


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_hashing.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/rosetta_core/hashing.py tests/test_hashing.py
git commit -m "Add sha256_text hashing helper"
```

---

### Task 3: Schema validation wrapper

**Suggested tool:** Codex (thin wrapper around a well-known library, clear contract).

**Files:**
- Create: `src/rosetta_core/schema.py`
- Test: `tests/test_schema.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `SchemaValidationError(errors: list[str])` and `validate_fields(fields: dict, schema: dict) -> None` (raises `SchemaValidationError` on failure), used by `loader.py` (Task 9) and `cli.py` (Task 10).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schema.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_core.schema'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/rosetta_core/schema.py
import jsonschema


class SchemaValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_fields(fields: dict, schema: dict) -> None:
    validator = jsonschema.Draft7Validator(schema)
    found = sorted(validator.iter_errors(fields), key=lambda e: list(e.path))
    if found:
        messages = [
            f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
            for e in found
        ]
        raise SchemaValidationError(messages)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_schema.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/rosetta_core/schema.py tests/test_schema.py
git commit -m "Add JSON Schema validation wrapper"
```

---

### Task 4: Canonical fields store

**Suggested tool:** Codex (straightforward load/save logic).

**Files:**
- Create: `src/rosetta_core/fields.py`
- Test: `tests/test_fields.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `FieldsStore(schema_ver: str, fields: dict)` with `.load(path: Path) -> FieldsStore` (classmethod), `.save(path: Path) -> None`, and `.fields_with_schema_ver() -> dict` (merges `SCHEMA_VER` into a copy of `fields`). Used by `sync.py` (Task 8), `loader.py` (Task 9), `cli.py` (Task 10).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fields.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fields.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_core.fields'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/rosetta_core/fields.py
import json
from pathlib import Path


class FieldsStore:
    def __init__(self, schema_ver: str, fields: dict):
        self.schema_ver = schema_ver
        self.fields = fields

    @classmethod
    def load(cls, path: Path) -> "FieldsStore":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(schema_ver=data["schema_ver"], fields=data["fields"])

    def save(self, path: Path) -> None:
        data = {"schema_ver": self.schema_ver, "fields": self.fields}
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def fields_with_schema_ver(self) -> dict:
        return {**self.fields, "SCHEMA_VER": self.schema_ver}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fields.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/rosetta_core/fields.py tests/test_fields.py
git commit -m "Add FieldsStore canonical load/save"
```

---

### Task 5: CPN serializer/parser

**Suggested tool:** Claude Code subagent (correctness-critical: canonicalization underpins the design's prompt-cache-stability guarantee).

**Files:**
- Create: `src/rosetta_core/cpn.py`
- Test: `tests/test_cpn.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure functions over `dict`/`str`).
- Produces: `serialize_packet(schema_ver: str, fields: dict) -> str` and `parse_packet(text: str) -> tuple[str, dict]` (returns `(schema_ver, fields)`, all field values as `str`). Used by `sync.py` (Task 8), `loader.py` (Task 9).

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cpn.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_core.cpn'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/rosetta_core/cpn.py

def _canonicalize_value(value) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def serialize_packet(schema_ver: str, fields: dict) -> str:
    lines = [f"SCHEMA_VER={schema_ver}"]
    for key in sorted(fields.keys()):
        lines.append(f"{key}={_canonicalize_value(fields[key])}")
    return "\n".join(lines) + "\n"


def parse_packet(text: str) -> tuple[str, dict]:
    schema_ver = None
    fields: dict = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        key, sep, value = line.partition("=")
        if sep != "=":
            continue
        if key == "SCHEMA_VER":
            schema_ver = value
        else:
            fields[key] = value
    if schema_ver is None:
        raise ValueError("packet missing SCHEMA_VER")
    return schema_ver, fields
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cpn.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/rosetta_core/cpn.py tests/test_cpn.py
git commit -m "Add CPN canonical serializer/parser"
```

---

### Task 6: Human document renderer/parser

**Suggested tool:** Claude Code subagent (encodes the spec's marker-region + lossless-round-trip design decision — needs to match spec intent precisely).

**Design decision for this task:** re-deriving typed field values from free-form prose bullets (e.g. parsing "- Identity match threshold: 0.92" back into `{"ID_THRESHOLD": 0.92}`) is fragile. Instead, the auto-generated section embeds an HTML comment containing the canonical fields as JSON (invisible in rendered Markdown), followed by human-friendly bullets generated from the same data. Extraction reads the JSON comment, not the bullets. This keeps the round-trip exact while keeping the visible doc genuinely readable.

**Files:**
- Create: `src/rosetta_core/human_doc.py`
- Test: `tests/test_human_doc.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `render_human_doc(title: str, schema_ver: str, fields: dict, field_descriptions: dict, notes: str) -> str`, `extract_fields_comment(doc_text: str) -> dict` (returns raw fields only, no `SCHEMA_VER`), `extract_schema_ver_comment(doc_text: str) -> str`, `extract_notes(doc_text: str) -> str`. Used by `sync.py` (Task 8), `cli.py` (Task 10).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_human_doc.py
from rosetta_core.human_doc import (
    render_human_doc,
    extract_fields_comment,
    extract_schema_ver_comment,
    extract_notes,
)

FIELDS = {"TASK": "ENTITY_RESOLUTION", "ID_THRESHOLD": 0.92}
DESCRIPTIONS = {"TASK": "Task", "ID_THRESHOLD": "Identity match threshold"}


def test_render_includes_markers_and_bullets():
    doc = render_human_doc("Entity Resolution Policy", "1.0", FIELDS, DESCRIPTIONS, notes="Escalate ambiguous cases.")
    assert "<!-- ROSETTA:AUTO-GENERATED" in doc
    assert "<!-- /ROSETTA:AUTO-GENERATED -->" in doc
    assert "<!-- ROSETTA:NOTES" in doc
    assert "- Identity match threshold: 0.92" in doc
    assert "Escalate ambiguous cases." in doc


def test_extract_fields_comment_round_trips():
    doc = render_human_doc("Entity Resolution Policy", "1.0", FIELDS, DESCRIPTIONS, notes="")
    assert extract_fields_comment(doc) == FIELDS


def test_extract_schema_ver_comment_round_trips():
    doc = render_human_doc("Entity Resolution Policy", "1.0", FIELDS, DESCRIPTIONS, notes="")
    assert extract_schema_ver_comment(doc) == "1.0"


def test_extract_notes_round_trips():
    doc = render_human_doc("Entity Resolution Policy", "1.0", FIELDS, DESCRIPTIONS, notes="Escalate ambiguous cases.")
    assert extract_notes(doc) == "Escalate ambiguous cases."


def test_notes_region_is_editable_independent_of_fields():
    doc = render_human_doc("Entity Resolution Policy", "1.0", FIELDS, DESCRIPTIONS, notes="original")
    hand_edited = doc.replace("original", "analyst added a caveat here")
    assert extract_notes(hand_edited) == "analyst added a caveat here"
    assert extract_fields_comment(hand_edited) == FIELDS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_human_doc.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_core.human_doc'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/rosetta_core/human_doc.py
import json

AUTO_START = "<!-- ROSETTA:AUTO-GENERATED — do not edit below this marker, edits will be overwritten by `rosetta sync` -->"
AUTO_END = "<!-- /ROSETTA:AUTO-GENERATED -->"
FIELDS_COMMENT_PREFIX = "<!-- ROSETTA:FIELDS "
SCHEMA_VER_COMMENT_PREFIX = "<!-- ROSETTA:SCHEMA_VER "
COMMENT_SUFFIX = " -->"
NOTES_START = "<!-- ROSETTA:NOTES — hand-written, sync never touches this region -->"
NOTES_END = "<!-- /ROSETTA:NOTES -->"


def render_human_doc(title: str, schema_ver: str, fields: dict, field_descriptions: dict, notes: str) -> str:
    lines = [
        AUTO_START,
        f"{FIELDS_COMMENT_PREFIX}{json.dumps(fields, sort_keys=True)}{COMMENT_SUFFIX}",
        f"{SCHEMA_VER_COMMENT_PREFIX}{schema_ver}{COMMENT_SUFFIX}",
        f"# {title}",
    ]
    for key in sorted(fields.keys()):
        description = field_descriptions.get(key, key)
        lines.append(f"- {description}: {fields[key]}")
    lines.append(AUTO_END)
    lines.append("")
    lines.append(NOTES_START)
    lines.append(notes.strip())
    lines.append(NOTES_END)
    return "\n".join(lines) + "\n"


def extract_fields_comment(doc_text: str) -> dict:
    start = doc_text.index(FIELDS_COMMENT_PREFIX) + len(FIELDS_COMMENT_PREFIX)
    end = doc_text.index(COMMENT_SUFFIX, start)
    return json.loads(doc_text[start:end])


def extract_schema_ver_comment(doc_text: str) -> str:
    start = doc_text.index(SCHEMA_VER_COMMENT_PREFIX) + len(SCHEMA_VER_COMMENT_PREFIX)
    end = doc_text.index(COMMENT_SUFFIX, start)
    return doc_text[start:end]


def extract_notes(doc_text: str) -> str:
    start = doc_text.index(NOTES_START) + len(NOTES_START)
    end = doc_text.index(NOTES_END)
    return doc_text[start:end].strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_human_doc.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/rosetta_core/human_doc.py tests/test_human_doc.py
git commit -m "Add human doc renderer/parser with lossless field round-trip"
```

---

### Task 7: Lockfile

**Suggested tool:** Codex (small, simple, self-contained).

**Files:**
- Create: `src/rosetta_core/lockfile.py`
- Test: `tests/test_lockfile.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `Lockfile(human_hash: str, machine_hash: str)` with `.load_or_default(path: Path) -> Lockfile` (classmethod, returns `Lockfile("", "")` if the file doesn't exist) and `.save(path: Path) -> None`. Used by `sync.py` (Task 8).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lockfile.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_lockfile.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_core.lockfile'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/rosetta_core/lockfile.py
import json
from pathlib import Path


class Lockfile:
    def __init__(self, human_hash: str, machine_hash: str):
        self.human_hash = human_hash
        self.machine_hash = machine_hash

    @classmethod
    def load_or_default(cls, path: Path) -> "Lockfile":
        if not path.exists():
            return cls(human_hash="", machine_hash="")
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(human_hash=data["human_hash"], machine_hash=data["machine_hash"])

    def save(self, path: Path) -> None:
        data = {"human_hash": self.human_hash, "machine_hash": self.machine_hash}
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_lockfile.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/rosetta_core/lockfile.py tests/test_lockfile.py
git commit -m "Add sync lockfile"
```

---

### Task 8: Sync engine (bootstrap, propagation, conflict detection)

**Suggested tool:** Claude Code subagent (the crux of the whole system's correctness guarantee — highest-risk task, needs full design context).

**Files:**
- Create: `src/rosetta_core/sync.py`
- Test: `tests/test_sync.py`

**Interfaces:**
- Consumes: `FieldsStore` (Task 4: `.load`, `.save`, `.schema_ver`, `.fields`), `serialize_packet`/`parse_packet` (Task 5), `render_human_doc`/`extract_fields_comment`/`extract_schema_ver_comment`/`extract_notes` (Task 6), `Lockfile` (Task 7: `.load_or_default`, `.save`, `.human_hash`, `.machine_hash`), `sha256_text` (Task 2).
- Produces: `SyncConflict(differing_keys: list[str])` (exception) and `sync(name: str, directory: Path, title: str, field_descriptions: dict) -> str` (returns one of `"bootstrap"`, `"human-to-machine"`, `"machine-to-human"`, `"no-op"`). Used by `cli.py` (Task 10).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sync.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sync.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_core.sync'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/rosetta_core/sync.py
from pathlib import Path

from .cpn import parse_packet, serialize_packet
from .fields import FieldsStore
from .hashing import sha256_text
from .human_doc import (
    extract_fields_comment,
    extract_notes,
    extract_schema_ver_comment,
    render_human_doc,
)
from .lockfile import Lockfile


class SyncConflict(Exception):
    def __init__(self, differing_keys: list[str]):
        self.differing_keys = differing_keys
        super().__init__(f"conflicting fields: {', '.join(differing_keys)}")


def _differing_keys(human_fields: dict, machine_fields: dict) -> list[str]:
    all_keys = set(human_fields) | set(machine_fields)
    return sorted(
        key for key in all_keys
        if str(human_fields.get(key)) != str(machine_fields.get(key))
    )


def sync(name: str, directory: Path, title: str, field_descriptions: dict) -> str:
    fields_path = directory / f"{name}.fields.json"
    md_path = directory / f"{name}.md"
    cpn_path = directory / f"{name}.cpn"
    lock_path = directory / f"{name}.rosetta.lock"

    store = FieldsStore.load(fields_path)
    lock = Lockfile.load_or_default(lock_path)

    human_text = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    machine_text = cpn_path.read_text(encoding="utf-8") if cpn_path.exists() else ""

    never_synced = lock.human_hash == "" and lock.machine_hash == ""
    if never_synced:
        new_machine = serialize_packet(store.schema_ver, store.fields)
        new_human = render_human_doc(title, store.schema_ver, store.fields, field_descriptions, notes="")
        cpn_path.write_text(new_machine, encoding="utf-8")
        md_path.write_text(new_human, encoding="utf-8")
        Lockfile(human_hash=sha256_text(new_human), machine_hash=sha256_text(new_machine)).save(lock_path)
        return "bootstrap"

    human_changed = sha256_text(human_text) != lock.human_hash
    machine_changed = sha256_text(machine_text) != lock.machine_hash

    if human_changed and machine_changed:
        human_fields = extract_fields_comment(human_text)
        _, machine_fields = parse_packet(machine_text)
        raise SyncConflict(_differing_keys(human_fields, machine_fields))

    if machine_changed:
        schema_ver, fields = parse_packet(machine_text)
        store.schema_ver = schema_ver
        store.fields = fields
        store.save(fields_path)
        notes = extract_notes(human_text)
        new_human = render_human_doc(title, store.schema_ver, store.fields, field_descriptions, notes)
        md_path.write_text(new_human, encoding="utf-8")
        Lockfile(human_hash=sha256_text(new_human), machine_hash=sha256_text(machine_text)).save(lock_path)
        return "machine-to-human"

    if human_changed:
        store.fields = extract_fields_comment(human_text)
        store.schema_ver = extract_schema_ver_comment(human_text)
        store.save(fields_path)
        new_machine = serialize_packet(store.schema_ver, store.fields)
        cpn_path.write_text(new_machine, encoding="utf-8")
        Lockfile(human_hash=sha256_text(human_text), machine_hash=sha256_text(new_machine)).save(lock_path)
        return "human-to-machine"

    return "no-op"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sync.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/rosetta_core/sync.py tests/test_sync.py
git commit -m "Add bidirectional sync engine with conflict detection"
```

---

### Task 9: Runtime loader with fallback

**Suggested tool:** Cline (interactive iteration on the error-handling path).

**Files:**
- Create: `src/rosetta_core/loader.py`
- Test: `tests/test_loader.py`

**Interfaces:**
- Consumes: `parse_packet` (Task 5), `validate_fields`/`SchemaValidationError` (Task 3).
- Produces: `PacketUnavailable(Exception)` and `load_prompt(name: str, directory: Path, schema: dict) -> str`. This is the function OSTINT/Thesis-tool integrations (future plans) will call at runtime.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_core.loader'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/rosetta_core/loader.py
from pathlib import Path

from .cpn import parse_packet
from .schema import SchemaValidationError, validate_fields


class PacketUnavailable(Exception):
    pass


def load_prompt(name: str, directory: Path, schema: dict) -> str:
    cpn_path = directory / f"{name}.cpn"
    md_path = directory / f"{name}.md"

    if cpn_path.exists():
        text = cpn_path.read_text(encoding="utf-8")
        try:
            schema_ver, fields = parse_packet(text)
            validate_fields({**fields, "SCHEMA_VER": schema_ver}, schema)
            return text
        except (ValueError, SchemaValidationError):
            pass

    if md_path.exists():
        return md_path.read_text(encoding="utf-8")

    raise PacketUnavailable(f"neither {cpn_path} nor {md_path} exists or is valid")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_loader.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/rosetta_core/loader.py tests/test_loader.py
git commit -m "Add runtime loader with machine-to-human fallback"
```

---

### Task 10: CLI

**Suggested tool:** Cline (CLI UX benefits from interactively running commands while iterating).

**Files:**
- Create: `src/rosetta_core/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `sync`/`SyncConflict` (Task 8), `FieldsStore` (Task 4), `validate_fields`/`SchemaValidationError` (Task 3), `render_human_doc`/`extract_notes` (Task 6).
- Produces: `main(argv: list[str] | None = None) -> int`, wired as the `rosetta` console script via `pyproject.toml` (Task 1). Subcommands: `sync`, `validate`, `compile` (alias for `sync`, documented as the friendlier name for first-time creation), `expand` (prints the current human-doc rendering without writing files or touching the lock).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_core.cli'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/rosetta_core/cli.py
import argparse
import json
import sys
from pathlib import Path

from .fields import FieldsStore
from .human_doc import extract_notes, render_human_doc
from .schema import SchemaValidationError, validate_fields
from .sync import SyncConflict, sync


def _default_title(name: str) -> str:
    return name.replace("_", " ").title()


def _run_sync(name: str, directory: Path) -> int:
    try:
        result = sync(name, directory, _default_title(name), field_descriptions={})
    except SyncConflict as exc:
        print(f"CONFLICT: {exc}", file=sys.stderr)
        return 1
    print(f"sync: {result}")
    return 0


def _run_validate(name: str, directory: Path) -> int:
    store = FieldsStore.load(directory / f"{name}.fields.json")
    schema = json.loads((directory / f"{name}.schema.json").read_text(encoding="utf-8"))
    try:
        validate_fields(store.fields_with_schema_ver(), schema)
    except SchemaValidationError as exc:
        for message in exc.errors:
            print(f"INVALID: {message}", file=sys.stderr)
        return 1
    print("valid")
    return 0


def _run_expand(name: str, directory: Path) -> int:
    store = FieldsStore.load(directory / f"{name}.fields.json")
    md_path = directory / f"{name}.md"
    notes = extract_notes(md_path.read_text(encoding="utf-8")) if md_path.exists() else ""
    print(render_human_doc(_default_title(name), store.schema_ver, store.fields, field_descriptions={}, notes=notes))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rosetta")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command_name in ("sync", "compile", "validate", "expand"):
        sub = subparsers.add_parser(command_name)
        sub.add_argument("name")
        sub.add_argument("--dir", default=".")

    args = parser.parse_args(argv)
    directory = Path(args.dir)

    if args.command in ("sync", "compile"):
        return _run_sync(args.name, directory)
    if args.command == "validate":
        return _run_validate(args.name, directory)
    if args.command == "expand":
        return _run_expand(args.name, directory)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/rosetta_core/cli.py tests/test_cli.py
git commit -m "Add rosetta CLI: sync, compile, validate, expand"
```

---

### Task 11: Dogfooding — Rosetta's own build decision log as a PacketSpec artifact

**Suggested tool:** Claude Code subagent (requires judgment about what's worth recording, tied to design intent).

**Files:**
- Create: `docs/decisions/rosetta_build.fields.json`
- Create: `docs/decisions/rosetta_build.schema.json`
- Generated by Step 3: `docs/decisions/rosetta_build.md`, `docs/decisions/rosetta_build.cpn`, `docs/decisions/rosetta_build.rosetta.lock`

**Interfaces:**
- Consumes: `rosetta` CLI (Task 10).
- Produces: a real, running example of the PacketSpec kind, used as the worked example in Task 12's end-to-end test and as proof the system works on itself.

- [ ] **Step 1: Write `docs/decisions/rosetta_build.schema.json`**

```json
{
  "type": "object",
  "required": ["DECISION_COUNT", "SCHEMA_VER"],
  "properties": {
    "DECISION_COUNT": {"type": "integer", "minimum": 0},
    "FIELD_VALUE_TYPES": {"type": "string"},
    "CONFLICT_POLICY": {"type": "string"},
    "SCHEMA_VER": {"type": "string", "pattern": "^\\d+\\.\\d+$"}
  }
}
```

- [ ] **Step 2: Write `docs/decisions/rosetta_build.fields.json`**

```json
{
  "schema_ver": "1.0",
  "fields": {
    "DECISION_COUNT": 3,
    "FIELD_VALUE_TYPES": "str,int,float",
    "CONFLICT_POLICY": "explicit,no-auto-merge"
  }
}
```

- [ ] **Step 3: Run `rosetta compile` to generate the human and machine views**

Run: `rosetta compile rosetta_build --dir docs/decisions`
Expected: prints `sync: bootstrap`; creates `docs/decisions/rosetta_build.md`, `docs/decisions/rosetta_build.cpn`, `docs/decisions/rosetta_build.rosetta.lock`.

- [ ] **Step 4: Hand-edit the generated `.md`'s notes region to record the actual decisions**

Open `docs/decisions/rosetta_build.md` and replace the empty notes region content (between the `ROSETTA:NOTES` markers) with:

```
1. Field values are restricted to str/int/float in V1 — nested dict-literal
   fields (per-source-class weighting) are deferred to a formal CPN grammar.
2. The human doc's auto-section embeds a JSON comment for lossless field
   round-trip, instead of parsing free-form prose bullets back into typed
   values.
3. Sync conflicts are never auto-resolved, even when only one field differs —
   the full differing-key list is surfaced and resolution is manual.
```

- [ ] **Step 5: Verify the artifact validates, then re-sync to pick up the notes edit**

Run: `rosetta validate rosetta_build --dir docs/decisions`
Expected: `valid`

Run: `rosetta sync rosetta_build --dir docs/decisions`
Expected: `sync: human-to-machine`. This is correct, not a bug: Task 8's `sync()` hashes the whole `.md` file, not the auto-section alone, so editing the notes region still changes `human_hash` relative to the lock. Sync re-derives fields from the (unchanged) `ROSETTA:FIELDS` comment and rewrites `.cpn` with byte-identical content, then records the new `human_hash` in the lockfile. Running `rosetta sync` a second time immediately after this one should print `sync: no-op`.

- [ ] **Step 6: Commit**

```bash
git add docs/decisions/rosetta_build.fields.json docs/decisions/rosetta_build.schema.json docs/decisions/rosetta_build.md docs/decisions/rosetta_build.cpn docs/decisions/rosetta_build.rosetta.lock
git commit -m "Dogfood: record Rosetta's own build decisions as a PacketSpec artifact"
```

---

### Task 12: End-to-end example test

**Suggested tool:** Claude Code subagent (integration test spanning the whole system).

**Files:**
- Test: `tests/test_end_to_end.py`

**Interfaces:**
- Consumes: `sync`/`SyncConflict` (Task 8), `load_prompt` (Task 9), `FieldsStore` (Task 4).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_end_to_end.py
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
    (tmp_path / f"{name}.cpn").write_text("SCHEMA_VER=1.0\nTASK=NOT_A_REAL_TASK\n", encoding="utf-8")

    # Loader falls back to the human doc rather than serving an invalid packet.
    fallback_prompt = load_prompt(name, tmp_path, SCHEMA)
    assert fallback_prompt == (tmp_path / f"{name}.md").read_text(encoding="utf-8")
    assert "Entity Resolution Policy" in fallback_prompt
```

- [ ] **Step 2: Run test to verify it passes immediately**

This task adds no new production code — `sync()` (Task 8) and `load_prompt()` (Task 9) are already implemented and independently tested. This test only verifies they compose correctly end-to-end, so unlike every other task in this plan, it should pass on the first run rather than fail first.

Run: `pytest tests/test_end_to_end.py -v`
Expected: PASS immediately. `load_prompt` returns the `.cpn` contents on the first call (packet is valid), then after `TASK` is corrupted to `NOT_A_REAL_TASK`, `parse_packet` still succeeds (it doesn't validate values) but `validate_fields` rejects `NOT_A_REAL_TASK` against the `TASK` enum, so `load_prompt` falls through to `.md`. If this fails instead, the bug is in Task 8 or Task 9's already-committed code, not in this test — stop and fix the earlier task.

- [ ] **Step 3: Run the full test suite**

Run: `pytest -v`
Expected: all tests across every task pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_end_to_end.py
git commit -m "Add end-to-end lifecycle test: bootstrap, edit, runtime fallback"
```

---

## Self-Review Notes

- **Spec coverage:** canonical store (Task 4), CPN machine view + canonicalization (Task 5), human view + notes region (Task 6), bidirectional sync + conflict detection (Task 8), runtime fallback ordering (Task 9), JSON Schema validation (Task 3), dogfooding (Task 11) — all covered. `.gitattributes` LF enforcement (Task 1) covers the cache-stability requirement. Deferred per spec's own "Open questions": nested dict-literal CPN fields, publishing mechanism, pre-commit vs. CI wiring for `rosetta sync` — none of these block a working V1.
- **Out of scope for this plan, by design:** OSTINT integration and Thesis-formatting-tool-mvp integration are separate follow-on plans — writing real (non-guessed) steps for them requires first reading each repo's actual LLM call sites.
