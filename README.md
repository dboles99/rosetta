# rosetta-core

A small Python package that keeps a compact machine-readable prompt packet and a human-readable Markdown document in sync, and refuses to guess when both have changed.

**简体中文：** rosetta-core 为同一份提示词或元数据维护两种形式：给模型读的紧凑 `KEY=VALUE` 数据包（`.cpn`），和给人读的 Markdown 文档。任一方被修改后，`rosetta sync` 会把改动同步到另一方；如果两边都改了，它会报告冲突，而不是自动合并。

**繁體中文：** rosetta-core 為同一份提示詞或中繼資料維護兩種形式：給模型讀的精簡 `KEY=VALUE` 資料包（`.cpn`），以及給人讀的 Markdown 文件。任一方被修改後，`rosetta sync` 會把變更同步到另一方；若兩邊都改了，它會回報衝突，而不是自動合併。

## What it does

For one artifact called `<name>` it manages four files in a directory:

| File | Role |
|---|---|
| `<name>.fields.json` | Canonical field store (values plus a schema version) |
| `<name>.cpn` | Compact packet: `KEY=VALUE` lines, keys sorted, LF line endings |
| `<name>.md` | Human view: a generated section, plus a hand-written notes region that sync never touches |
| `<name>.rosetta.lock` | SHA-256 of the `.md` and `.cpn` at the last successful sync |

`rosetta sync` compares each view with the lock file:

- only the packet changed: update the fields and regenerate the Markdown (notes kept)
- only the Markdown changed: update the fields and regenerate the packet
- both changed: stop with a conflict that lists the differing keys, exit code 1
- neither changed: no-op

`rosetta validate` checks the fields against `<name>.schema.json` (JSON Schema). Packet values are always read as strings, so numbers are coerced to the type the schema declares before validation. `rosetta expand` prints the Markdown view for a fields store.

## Quick start

Needs Python 3.11 or later.

```bash
git clone <this repository>
cd rosetta
python -m venv .venv
.venv/bin/pip install -e ".[dev]"      # Windows: .venv\Scripts\pip install -e ".[dev]"
.venv/bin/python -m pytest -q          # 50 tests, no network or API key needed
```

## Example

`examples/rosetta_build/` holds a complete artifact. Copy it, change a value in the packet, and sync:

```bash
cp -r examples/rosetta_build /tmp/ex
sed -i 's/^DECISION_COUNT=3/DECISION_COUNT=4/' /tmp/ex/rosetta_build.cpn
.venv/bin/rosetta sync rosetta_build --dir /tmp/ex
```

```
sync: machine-to-human
```

The Markdown view now reads `- DECISION_COUNT: 4` and the fields store matches. Validation passes:

```bash
.venv/bin/rosetta validate rosetta_build --dir /tmp/ex
```

```
valid
```

If you then edit the same field in both the `.cpn` and the `.md`, sync refuses:

```
CONFLICT: conflicting fields: DECISION_COUNT
```

## Design notes

- The fields store is the source of truth, and the `.cpn` and `.md` files are views of it. A direct edit to either view is detected through the lock hashes.
- Conflicts are never resolved automatically, even when only one field differs. A person decides.
- The packet is meant to be the normal model input. The Markdown is a fallback if the packet is missing or invalid (`load_prompt` in `rosetta_core.loader`), and is never appended alongside it.
- Serialization is canonical (sorted keys, fixed float formatting, LF endings) so identical meaning gives identical bytes, which suits provider-side prompt caching.
- The full design, including deferred ideas, is in [docs/design.md](docs/design.md).

## Limits

- Only the "PacketSpec" artifact kind exists. The ProgramSpec idea in the design notes is not implemented.
- Field values are limited to strings, integers and floats. Nested values are not supported.
- `rosetta sync` notices edits to the `.cpn` and the `.md`. An edit made only to `<name>.fields.json` is not picked up (in the example above, changing the JSON by hand left both views unchanged and sync reported `no-op`).
- After a sync from the packet, numeric values are stored as strings in `fields.json`. `validate` coerces them back using the schema.
- Token savings are not measured here. A companion benchmark harness, rosetta-bench, is meant to test that claim; no results are published.

## Licence

Apache-2.0. See [LICENSE](LICENSE).

Designed and authored by Daniel Boles; implemented with coding agents.
