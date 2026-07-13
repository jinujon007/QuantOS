# AI Operating System — `.ai/`

Fast-context bootstrap layer for any AI agent working in this repository.
Exists so a new session doesn't have to re-derive project state by reading
every governing document from scratch. It is a convenience cache, not a
source of truth.

## Reading order

1. **README.md** (this file) — how to use the other three.
2. **AI_CONTEXT.md** — what QuantOS is and why. Executive summary, grounded
   in the Constitution/Blueprint/Audit/Due Diligence. Changes rarely.
3. **PROJECT_STATE.yaml** — machine-readable snapshot of current state.
   Changes at the close of every work package.
4. **CURRENT_TASK.md** — the single active work package, right now. Changes
   most frequently of the four.

## File responsibilities

| File | Responsibility | Update cadence |
|---|---|---|
| `README.md` | This meta-guide. Reading order, precedence rule. | On workflow change only |
| `AI_CONTEXT.md` | 2-page executive summary of QuantOS — mission, architecture, roadmap, current phase. | When a governing document (Constitution, Blueprint, Audit, Due Diligence) changes |
| `PROJECT_STATE.yaml` | Concise machine-readable current state — phase, metrics, open risk/debt counts, repo facts. Actively maintained only, no history. | End of every work package |
| `CURRENT_TASK.md` | The currently active work package. Short. Never predicts future phases. | Whenever the active task changes |

## Precedence rule

**Repository evidence overrides AI context, always.** Code, tests, CI
results, `git log`, and the governing documents in `docs/` (Constitution,
Blueprint, ADRs, Audit, Due Diligence) are the actual source of truth. Files
in `.ai/` are a derived summary and can go stale the moment the repository
moves. If anything in `.ai/` conflicts with what the repository actually
shows, the repository wins — treat the `.ai/` file as wrong and due for
correction, not the other way around.

## What this is not

Not a replacement for `docs/00_governance/(AI) QuantOS Constitution.md`,
the Blueprint, or the ADRs. Those remain the ratified, frozen governing
documents. `.ai/` exists only to make the first five minutes of a session
faster.
