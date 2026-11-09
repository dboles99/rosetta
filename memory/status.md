# Status

## Now
- [ ] Decision-layer experiment: evidence gathered, draft verdict ADVISORY_ONLY, awaiting calibration

## Next
- [ ] Gate reason-first PROCEED plans with clef `premise_valid`; run on usefulness_v3 (3 samples)
- [ ] Reason-first with executor thinking for code plans only
- [ ] Grow corpora: about 60 labelled items per decision question; usefulness towards a few hundred tasks
- [ ] Postflight on failing code; P vs M replication
- [ ] Final code review of both `exp/decision-layer` branches, then the written recommendation

## Blocked
- [ ] Owner: label `labelling/routing_v1_to_label.xlsx` (bench), then import and calibrate
- [ ] Owner: Jev $9.90 pack for a full run, or stay with clef
- [ ] Owner: approval to merge `exp/decision-layer` to `master` / `main`

## Done
- [x] Initialized Anchor memory ledger (2026-11-09)
- [x] Core decision contracts, fail-closed state, receipts, replay, canonical cache (core `exp/decision-layer`)
- [x] Bench: shadow runs, decision eval (142 items), usefulness matrix, Docker sandbox, catalog/db/notebook (2026-11-09)
- [x] Paired statistics, calibrated abstention tool, REPORT_DEFECT + usefulness_v3, paraphrase ensembles (2026-11-09)
- [x] Reason-first arm, fixed to plan schema 1.1; 3-sample comparison of three arms (runs 18-29) (2026-11-09)
- [x] Literature review (bench `results/LITERATURE_REVIEW.md`) (2026-11-09)
