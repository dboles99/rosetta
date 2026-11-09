# Decisions

Load-bearing decisions only. Each: date, WHY, impact. **Check before "fixing"
something that looks wrong — it may be intentional.** Evidence for the experiment decisions lives in
`dboles99/rosetta-bench` branch `exp/decision-layer`, `results/INSIGHTS.md` (insight numbers cited below).

---

## 2026-11-09 — Adopted Anchor memory discipline
**Why:** keep agent memory verifiable and prevent re-litigating settled choices.
**Impact:** memory ledger + @meta anchors + integrity hooks are now in effect.
**Status:** active

## 2026-11-09 — Decision layer is an optional, default-off experiment on branches only
**Why:** owner brief: Rosetta core must stay deterministic; Jev/clef are evaluated, not adopted. Branch from dev `master`
(`G:\dev2\*`), publish to `main` only later and only with approval.
**Impact:** all work is on `exp/decision-layer` in both repos; no merge to `master`/`main`, no publish, no deploy.
**Status:** active

## 2026-11-09 — Providers: clef via local Ollama, Jev via jevmodel.org; $20 cap; 5 pp margin
**Why:** owner choice. jevmodel.org is an unaffiliated reseller with a free account; clef is the open look-alike on
Ollama Cloud. "Logical" sizing = a 5-point margin, about 250 cases.
**Impact:** profiles `clef-ollama` and `jevmodel` (served `jev-1.14.0`); spend stayed at $0 (subscription + free tokens).
The jevmodel key is used only in-process by a helper script and never printed; the credential notes file is gitignored.
**Status:** active

## 2026-11-09 — Cache decisions by exact canonical key only, never by similarity
**Why:** 47 of 56 opposite-answer pairs had similarity >= 0.90, so similarity caching would return wrong answers.
**Impact:** core `rosetta_core.decision.cache`: key = canonical state + question set + scope (provider, served model,
policy, TTL); only validated answers are cached. Warm runs cost 0 calls (insight 15).
**Status:** active

## 2026-11-09 — Compact question wording 1.2 adopted; batching rejected
**Why:** compact wording cut decision tokens 14% with equal or better accuracy; batching saved only 16% and degraded
answers (insight 15).
**Impact:** `--compact` (intake 1.2) is the preferred decision wording; `--batch-size` stays at 1.
**Status:** active

## 2026-11-09 — Paraphrase ensembles rejected as an uncertainty signal
**Why:** run 22: no accuracy gain (0.93 single vs 0.89 mean), spread AUROC 0.68 vs 0.99 for the single answer's margin;
two of seven rewordings broke (insight 12).
**Impact:** use the single pinned wording's margin; paraphrasing is only a wording-robustness check. Pinned question
hashes must change with any rewording.
**Status:** active

## 2026-11-09 — Reason-first plan schema 1.1: hand-off verdicts
**Why:** run 20 answered every non-code task with the bare NOT_A_CODE_TASK marker (my defect; the fake planner hid it).
**Impact:** NOT_A_CODE_TASK and NEEDS_CLARIFICATION execute the route contract without a plan; UNSOLVABLE,
PREMISE_REJECTED and REPORT_DEFECT stop with the marker. Plan schema 1.0 runs are not comparable (bench `7c8c174`).
**Status:** active

## 2026-11-09 — Rust port not started
**Why:** approved only if the three arms tied; they did not (thinking on 0.90, reason-first 0.78, thinking off 0.63,
3 samples each; insights 9-10).
**Impact:** none; revisit only if a future comparison ties.
**Status:** active

## 2026-11-09 — Draft verdict: ADVISORY_ONLY (not final)
**Why:** the decision layer adds 34-69% tokens per success with no accuracy gain on generation tasks, but clef answers
the decision questions well and signals its own uncertainty (insights 3, 6, 12).
**Impact:** final recommendation waits for calibrated, frozen thresholds on the routing_v1 calibration split (owner labels).
**Status:** active
