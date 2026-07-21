---
type: adr
number: 040
date: 2026-07-21
status: accepted
supersedes: none
---

# ADR-040 — Live Paper State Is Untracked; Backups Are the History (WP-015)

## Decision

`data/paper_state.json` is removed from git tracking (working file kept)
and gitignored, alongside `data/paper_trades.csv` (already untracked,
now ignored deliberately rather than by omission). Their history and
off-repo protection is WP-014's dated daily backup (ADR-039), not git.

`data/universe_pit.db` and `data/results/*.csv` stay tracked: the PIT
membership store is audit evidence whose git history is valuable and
changes only weekly; the results CSVs are pinned, deliberately-refreshed
artifacts, not runtime state.

Untracked session scaffolding that never belonged to the platform
(`LOOP.md`, `STATE.md`, `loop-*.md`, `.claude/`) is gitignored so the
working tree stays clean.

## Context

TD-016: the scheduled task mutates `paper_state.json` daily while git
tracks it — every session opened on a dirty tree, and any
`git checkout/restore/stash -- data/` would silently roll the live
validation account back in time. The register required a decision:
commit state daily, or untrack the live file.

## Rationale

Committing state daily from the unattended runner would couple the
15:40 task to push credentials, pollute source history with ~250
state-churn commits/year, and still lose same-day granularity. WP-014
now provides dated daily copies with rotation — strictly better as
state history — which is what made this the right moment to decide
TD-016 (it was deliberately left open until a real backup existed).

The rollback foot-gun inverts into protection: switching to a historic
commit where the file WAS tracked now refuses rather than silently
overwriting the untracked live file.

## Consequences

- Working tree is clean between runs; `git status` noise ends.
- `paper_state.json`'s last committed copy (2026-07-21 state) remains
  in history at this ADR's commit^ for archaeology.
- TD-016 closed. INVENTORY regenerated (git-tracked files only).
- The trade audit trail's durability now rests entirely on ADR-039
  backups — one more reason the operator should point
  `QUANTOS_BACKUP_DIR` off-machine.
