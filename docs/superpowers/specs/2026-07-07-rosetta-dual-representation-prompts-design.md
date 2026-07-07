# Rosetta: dual-representation prompts and metadata

**Status:** Draft, pending user review
**Date:** 2026-07-07

## Problem

Prompts, agent instructions, and metadata records currently exist as one representation: verbose, human-authored prose or documents (Markdown, freeform policy files). This is costly and fragile across every project that uses LLMs (OSTINT-INFRO REPORTING, Thesis-formatting-tool-mvp, ue-docxbridge, and others):

- **Token cost/latency**: verbose prose sent as context on every call burns tokens and time.
- **Consistency/maintainability**: prompts and metadata are hand-edited per project with no shared discipline; they drift from each other and from one project to the next.
- **Parsing reliability**: downstream code and LLMs sometimes misparse free-text, since nothing enforces a strict machine-readable shape.

The seed of a solution already exists, undocumented, in the OSTINT repo (`meaningful brainstorm_chat_about more features and internal communication_04JULY2026.md`, uncommitted): a "policy compiler" that distills verbose governance Markdown into a compact `KEY=VALUE` packet per task, e.g.:

```
TASK=ENTITY_RESOLUTION
SCOPE=PUBLIC_ONLY
TIME=2024-01-01..2026-07-04
GEO=TH,TW,US
ID_THRESHOLD=.92
```

This spec generalizes that idea into a standalone system usable across all of the user's applications, for prompts, metadata, and configuration alike.

## Goals

- One canonical dual-representation system: a compact machine-readable form and a human-readable form, always in sync.
- Usable for any dual-audience text artifact: LLM prompts/instructions, structured metadata records, configuration.
- The compact machine form is what's normally sent to an LLM or consumed by code; the human form is a genuine fallback, not routine traffic.
- Bidirectional sync: an edit to either representation propagates to the other. Divergent edits to both since the last sync must surface as an explicit conflict, never be silently resolved.
- Machine form is structured for both strict schema validation (code consumers) and LLM-token density (prompt consumers).
- Machine form's serialization is stable/canonical enough to maximize provider-side prompt caching (e.g. Anthropic `cache_control`) hits across repeated calls.
- Ships as a standalone, installable package (not vendored per-project), consumed first by OSTINT.

## Non-goals

- Not an LLM-based reconciliation engine. Conflicts are surfaced to a human, not auto-merged by an LLM.
- Not a general-purpose templating engine or document generator.
- Not tied to any single LLM provider's prompt format — the CPN notation and schema validation are provider-agnostic; provider-specific cache-control wiring is a thin adapter layer.

## Naming

- **Rosetta** — the system/package name. Metaphor: a Rosetta Stone — the same meaning preserved across two representations.
- **CPN (Compact Packet Notation)** — the flat `KEY=VALUE` / nested `KEY.SUBKEY=VALUE` dialect the compiler emits.

## Architecture

### Canonical store, not either file

The naive design ("human file is source, machine file is compiled from it") cannot guarantee bidirectional sync — a direct edit to the machine packet (which will happen; it's what pipelines and on-call engineers touch at runtime) would silently diverge from the prose forever.

Instead, a small structured **fields store** is the actual source of truth for a given Rosetta artifact. Both the human document and the machine packet are *generated views* over those fields:

```
canonical fields (<name>.fields.json)
        │                                    │
        ▼                                    ▼
  <name>.md                             <name>.cpn
  - auto-generated narrative            - compiled KEY=VALUE packet
    section (rendered from fields         canonicalized (sorted keys,
    + their schema descriptions)          fixed float precision, LF)
  - hand-written "notes" region,        - what's sent to the LLM /
    never touched by sync                 consumed by code, normally
```

### File layout (per artifact)

```
prompts/entity_resolution/
  fields.json       # canonical structured data + schema ref
  entity_resolution.md    # human view: auto section + notes region
  entity_resolution.cpn   # machine view: compiled packet
  .rosetta.lock            # last-synced hashes of both views
```

### Human document structure

```markdown
<!-- ROSETTA:AUTO-GENERATED — do not edit below this marker, edits will be overwritten by `rosetta sync` -->
# Entity Resolution Policy
- Task: ENTITY_RESOLUTION
- Scope: Public sources only
- Identity match threshold: 0.92
<!-- /ROSETTA:AUTO-GENERATED -->

<!-- ROSETTA:NOTES — hand-written, sync never touches this region -->
Analysts should treat anything below the 0.92 threshold as a lead, not
a match, and escalate ambiguous cases to a human reviewer rather than
lowering the threshold.
<!-- /ROSETTA:NOTES -->
```

### Sync algorithm (`rosetta sync <name>`)

Run pre-commit, on load, or on demand. Compares each view's current hash against the hash recorded in `.rosetta.lock` at the last successful sync:

1. Only the fields/packet changed since last sync → regenerate the `.md` auto-section (the notes region is preserved verbatim).
2. Only the `.md` auto-section changed → re-derive fields from it → recompile the `.cpn` packet.
3. **Both changed since last sync → conflict.** Report the differing fields; require explicit resolution. Never silently prefer one side.
4. Neither changed → no-op.

Conflict detection:

```
conflict = (human_hash_now ≠ human_hash_at_lock) AND (machine_hash_now ≠ machine_hash_at_lock)
```

### Runtime loader (fallback ordering)

Only the compiled `.cpn` packet is sent to the LLM (or consumed by code) in the normal path. The human `.md` document is sent only as a full replacement when the packet is unavailable or invalid — it is never appended alongside the packet in a normal call.

```python
try:
    prompt = load_and_validate(f"{name}.cpn")
except (MissingFile, ParseError, SchemaError):
    log.warning("packet invalid or missing — falling back to human-readable source")
    prompt = load(f"{name}.md")  # full replacement, not appended
```

Because the human document is rarely sent, the hand-written notes region carries real weight: it should be trustworthy on its own for the rare moment the system actually falls back to it.

## Formulas and algorithms

**Canonicalization** (maximizes provider prompt-cache hits — identical meaning must serialize to an identical string):

```
canonical(packet) = sort_keys_lexicographically(packet)
                     with fixed float precision (e.g. %.2f), LF line endings,
                     no trailing whitespace, deterministic key casing
```

**Staleness detection** (also the basis for conflict detection above):

```
compiled_from_hash = sha256(source_bytes)
on load: if sha256(current_source) != compiled_from_hash → stale, recompile or warn
```

**Compression value metric** (to quantify savings):

```
compression_ratio = tokens(machine_packet) / tokens(human_source)
```

**Relevance-based packing** (compiling a task-specific packet out of many source policy documents under a token budget; greedy knapsack approximation):

```
score(chunk) = relevance(chunk, task) / tokens(chunk)
add chunks by descending score until token_budget is exhausted
```

**Weighted source re-weighting** (generalizing the OSTINT source-credibility trick — exponential moving average blending on event triggers):

```
w_new = w_old * (1 - alpha) + w_trigger * alpha
```

**Schema versioning gate:**

```
SCHEMA_VER=major.minor   # stamped in both the fields store and the compiled packet header
loader refuses/warns if the packet's major version != the loader's supported major version
```

## Example schema (JSON Schema for a compiled packet, strict-consumer case)

```json
{
  "type": "object",
  "required": ["TASK", "SCOPE", "SCHEMA_VER"],
  "properties": {
    "TASK": {"type": "string", "enum": ["ENTITY_RESOLUTION", "VERIFICATION"]},
    "ID_THRESHOLD": {"type": "number", "minimum": 0, "maximum": 1},
    "SCHEMA_VER": {"type": "string", "pattern": "^\\d+\\.\\d+$"}
  }
}
```

## Delivery plan

- New standalone repo (this one: `rosetta`), versioned and published independently.
- Core package (`rosetta-core`): fields store model, CPN compiler/serializer, `.md` renderer, sync engine, JSON Schema validator, runtime loader with fallback.
- CLI (`rosetta compile|validate|sync|expand`).
- OSTINT is the first consumer, via a path dependency during development; other projects (Thesis-formatting-tool-mvp, ue-docxbridge) adopt once proven.

## Open questions

- Exact serialization rules for nested dict-literal CPN fields (e.g. the weighted per-source-class blocks from the OSTINT brainstorm) — needs a formal grammar, not just examples.
- Whether `rosetta sync` runs as a pre-commit hook, a CI check, or both.
- Publishing mechanism (private package index vs. path/git dependency across projects) — deferred until the core package is proven in OSTINT.
