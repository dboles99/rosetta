# HANDOFF — resume here

_Refresh with `/handoff`. Mechanical state is auto-saved to `.anchor/session-state.md`._

## Goal
Rosetta decision layer: decide whether optional typed decision engines (Jev primary, clef challenger) improve useful
output while Rosetta stays deterministic. Final verdict: one of KEEP_BASELINE / BENCH_ONLY / ADVISORY_ONLY /
SELECTIVE_REPLACEMENT / INCONCLUSIVE. Draft: ADVISORY_ONLY.

## Done (session 2026-11-09)
- Core `exp/decision-layer`: decision contracts, state, answers, policy, receipts, canonical cache (149 tests).
- Bench `exp/decision-layer` (includes `exp/improvements`): 29 logged runs, 15 insights, 3-sample comparison of
  thinking on / reason-first / thinking off, paraphrase ensembles (rejected), calibration tool, REPORT_DEFECT,
  notebook sections 5-6 (435 tests). Both branches pushed to origin; nothing merged to `master`/`main`.

## Next step
- Read `G:\dev2\rosetta-bench\.worktrees\exp-decision-layer\results\NEXT_SESSION_PLAN.md`, then start item 1:
  gate reason-first PROCEED plans with clef `premise_valid` on usefulness_v3.

## Open threads / gotchas
- Owner actions block the final verdict: routing_v1 labels, Jev pack decision, merge approval.
- Python: `G:\dev2\rosetta\.worktrees\.venv-exp\Scripts\python.exe`; from a worktree other than bench
  `exp-decision-layer`, set `PYTHONPATH=src`.
- Never open, print or name the jevmodel credential notes file in a command; the key is read in-process by a helper.
- Untracked owner files in this repo root (brief, raw brainstorming chat, Jev PDF, `model_chain.py`) were left as they are.

## Key files
- Bench: `results/INSIGHTS.md`, `results/NEXT_SESSION_PLAN.md`, `results/COMPARISON_3x3.md`, `results/EXPERIMENT_LOG.md`,
  `notebooks/decision_layer_analysis.ipynb`, `src/rosetta_bench/usefulness/reason_first.py`, `src/rosetta_bench/decision/`
- Core: `.worktrees/exp-decision-layer/src/rosetta_core/decision/`
- Ledger: `memory/decisions.md`, `memory/FACTS.md`, `memory/status.md`
