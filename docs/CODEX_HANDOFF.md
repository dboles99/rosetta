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

**Last updated:** after all 12 tasks complete and independently reviewed (spec compliance + code quality) — plan fully checked off.

**Completed (all steps `- [x]`, all reviewed and approved by an independent task-reviewer pass, including Task 10 which Codex implemented during a handoff and was reviewed after the fact):** Tasks 1-12. The rosetta-core V1 (PacketSpec) implementation is functionally complete.

**Latest commit on `rosetta-core-v1`:** `abe61fe` — "Check off Tasks 10-12 in plan (all 12 tasks now complete)"

**Two cross-cutting fixes already applied — nothing to redo, just don't reintroduce these bugs:**
- Every production `Path.write_text()` call must pass `newline="\n"` explicitly (Windows would otherwise silently write `\r\n`). Applied in `fields.py`, `lockfile.py`, `sync.py`.
- `validate_fields()` in `schema.py` coerces stringly-typed values (CPN packets always parse fields as `str`) to the schema's declared `number`/`integer` type before validating. `loader.py`/`cli.py` rely on this — don't add redundant conversion.

**Full test suite status:** 50/50 passing as of `0f238a4`. Run `pytest -v` (or `PYTHONPATH=src python3 -m pytest -q -s` if using WSL and pytest capture hits temp-file issues) from the worktree root.

**Remaining before this whole effort is done (in order):**
1. **Benchmark suite** (not started, not yet designed) — the user requested a second, separate body of work: design and build a benchmark comparing human-readable vs. machine-readable prompt performance (read/implementation speed, efficiency, completeness) across Azure Translation, Azure OpenAI, Claude, Codex, Cline, and Ollama, with a schema, a rubric, and a results spreadsheet. This needs its own brainstorming/planning pass — it is NOT part of the rosetta-core-v1 plan/branch and likely doesn't belong in this repo at all (probably its own project/repo, TBD during its design). If you're picking this up cold: don't start coding it, start by clarifying scope with the user the way the rest of this project was brainstormed (see the design spec's own history for the pattern).
2. **Final whole-branch code review** of the `rosetta-core-v1` branch (all 12 tasks together), then `superpowers:finishing-a-development-branch` to merge/PR/clean up. Do this only after the benchmark suite work above is also complete — the user explicitly asked for this ordering.

## If you are Codex picking this up cold

The plan's 12 tasks are all done and checked off — there is nothing left to implement in `docs/superpowers/plans/2026-07-07-rosetta-core-v1.md`. What's left is (1) a brand-new, undesigned benchmark-suite project (needs requirements clarification first, not code) and (2) the final review/merge of this branch. Don't re-run or redo any of Tasks 1-12.

## If you are Codex picking this up cold

You don't need the git history, the review packages, or the `.superpowers/sdd/` scratch directory (that's Claude-specific tooling state, gitignored, safe to ignore or delete). You only need:
1. This file (state + pointers)
2. The plan file (exact next steps)
3. A working Python 3.11+ environment with `pytest` and `jsonschema` installed

Implement the next unchecked task's steps exactly as written, run the tests, commit, check the boxes, update this file's "Current state," done.
