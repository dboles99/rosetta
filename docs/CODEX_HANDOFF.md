# Codex handoff — Rosetta Core V1

Purpose: if Claude usage runs out mid-build, this file plus the plan file is
everything a fresh Codex (or any other agent) session needs to resume with
zero prior context. Update the "Current state" section after every task.

## Where things live

- **Repo:** `C:\Users\danie\dev2\rosetta` (git repo, branch `master` untouched)
- **Active work branch:** `rosetta-core-v1`
- **Worktree:** `C:\Users\danie\dev2\rosetta\.worktrees\rosetta-core-v1` — do all work here, not in the main repo checkout
- **Plan (source of truth for what to do next):** `docs/superpowers/plans/2026-07-07-rosetta-core-v1.md`
- **Design spec (background/why):** `docs/superpowers/specs/2026-07-07-rosetta-dual-representation-prompts-design.md`

## How to resume (tool-agnostic)

1. `cd` into the worktree above, confirm branch: `git branch --show-current` → should print `rosetta-core-v1`.
2. Open the plan file. Every step under every `### Task N` heading is a markdown
   checkbox. `- [x]` means done, `- [ ]` means not done yet.
3. Find the first `### Task N` heading that still has any `- [ ]` steps under
   it — that's the task to work on next. **Do not skip ahead or re-do a task
   whose steps are all `- [x]`.**
4. Each task's brief is fully self-contained in the plan: exact file paths,
   complete test code, complete implementation code, exact commands to run
   and their expected output. Follow it verbatim — this plan was written so
   an implementer needs no other context than the task's own text.
5. After finishing a task's steps (tests passing, committed), flip its
   `- [ ]` boxes to `- [x]` in the plan file and commit that alongside the
   code, so the next resumption (by any tool) sees accurate state.
6. Update the "Current state" section below and commit it too.

## Current state

**Last updated:** after Task 10 CLI implementation was recovered, verified, and committed by Codex.

**Completed (all steps `- [x]`, all reviewed and approved):** Tasks 1-9.

**Completed by Codex continuation:** Task 10 (CLI). `src/rosetta_core/cli.py` and `tests/test_cli.py` were present as untracked files after the handoff; Codex verified the full suite with `PYTHONPATH=src python3 -m pytest -q -s` (`49 passed`), recorded `task-10-report.md`, checked off the plan, and committed the files.

**Not started:** Tasks 11 (dogfooding decision log), 12 (end-to-end test).

**Latest commit on `rosetta-core-v1`:** Task 10 commit — "Add rosetta CLI: sync, compile, validate, expand"

**Two cross-cutting fixes already applied that a fresh implementer must know about** (both already in the code — nothing to redo, just don't reintroduce the bugs):
- Every production `Path.write_text()` call must pass `newline="\n"` explicitly (Windows would otherwise silently write `\r\n`). Already applied in `fields.py`, `lockfile.py`, `sync.py`. Any new file-writing code must do the same.
- `validate_fields()` in `schema.py` coerces stringly-typed values (CPN packets always parse fields as `str`) to the schema's declared `number`/`integer` type before validating. This is why `loader.py` and any future CLI/validation code does not need to do its own type conversion — just pass parsed fields straight to `validate_fields`.

**Full test suite status:** 49/49 passing after Task 10. Run `PYTHONPATH=src python3 -m pytest -q -s` from the worktree root if pytest capture hits temp-file issues in WSL.

**After Task 12 completes:** the user has requested a separate, second body of work — designing and building a benchmark suite comparing human-readable vs. machine-readable prompt performance across Azure Translation, Azure OpenAI, Claude, Codex, Cline, and Ollama (read/implementation speed, efficiency, completeness), with a schema, a rubric, and a results spreadsheet. This has **not been designed yet** — it needs its own brainstorming/planning pass, not a continuation of this plan's tasks. Do not start it before Task 12 is done; do the final whole-branch review only after both this plan's Task 12 and the benchmark work are complete.

## If you are Codex picking this up cold

You don't need the git history, the review packages, or the `.superpowers/sdd/` scratch directory (that's Claude-specific tooling state, gitignored, safe to ignore or delete). You only need:
1. This file (state + pointers)
2. The plan file (exact next steps)
3. A working Python 3.11+ environment with `pytest` and `jsonschema` installed

Implement the next unchecked task's steps exactly as written, run the tests, commit, check the boxes, update this file's "Current state," done.
