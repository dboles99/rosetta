# FACTS — mandatory read before any plan, experiment, or recommendation

**Purpose:** single-page source of truth for current facts + what's been tried.
Prevents re-proposing already-failed approaches and re-quoting stale numbers.

**Rule:** Read this FIRST every session. Before proposing any new approach, confirm
it is not on the "Tried & failed" list below.

**Last verified:** 2026-11-09

---

## Current facts

<!-- @meta
id: fact-next-plan
status: active
anchors:
  - kind: file_exists
    file: memory/HANDOFF.md
    expect: present
-->

| Fact | Source | Verified |
|------|--------|----------|
| Core tests: 149 pass on `exp/decision-layer`; bench: 435 pass, 4 skipped | test runs | 2026-11-09 |
| Usefulness_v2 (66 tasks, 3 samples): thinking on 0.90, reason-first 0.78, thinking off 0.63 | bench `results/COMPARISON_3x3.md` | 2026-11-09 |
| Thinking costs about 11x output tokens (211k vs 19k per run) and carries the honest refusals | bench INSIGHTS 9 | 2026-11-09 |
| Decision layer before generation: no accuracy gain, +34-69% tokens per success | bench INSIGHTS 2-4 | 2026-11-09 |
| clef decision_v1 accuracy: 1.00 on meaning/support/notes/views, 0.84-0.86 feasibility/premise (ja worst) | bench run `_11` | 2026-11-09 |
| No decision threshold is calibrated yet; about 60 labelled items per question are needed | bench INSIGHTS 13 | 2026-11-09 |
| 66 tasks cannot detect a 5-point difference (about 500-1,000 needed) | bench `COMPARISON_3x3.md` | 2026-11-09 |
| jevmodel.org free tokens are used up; a full Jev run needs the $9.90 pack | bench run `_21` | 2026-11-09 |

## Tried & failed (anti-repetition firewall)

| Approach | Why it failed | When |
|----------|---------------|------|
| Similarity caching of decisions | 47/56 opposite-answer pairs had similarity >= 0.90 | 2026-11-09 |
| Batching several requests per decision call | 16% fewer tokens (route list repeated per slot), accuracy fell | 2026-11-09 |
| Paraphrase ensembles as an uncertainty signal | no accuracy gain; AUROC 0.68 vs 0.99 for the single margin | 2026-11-09 |
| Intake routing before generation on these corpora | cannot pay for itself; break-even needs about 2.1k-2.7k generator tokens saved per decline | 2026-11-09 |
| Reason-first plan schema 1.0 | dropped all non-code tasks (fixed in 1.1) | 2026-11-09 |
