# memory/

The project's git-tracked ledger (source of truth).

- **FACTS.md** — read first; current facts + tried-and-failed firewall.
- **decisions.md** — load-bearing decisions (why + impact).
- **status.md** — done / next / blocked.

Entries can carry `@meta` anchors (see `docs/anchor-anchors-spec.md`) so
`memory_lint.py` flags any entry that drifts from the live repo.
