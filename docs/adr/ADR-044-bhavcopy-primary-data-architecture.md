---
type: adr
number: 044
date: 2026-07-21
status: proposed  # operator approval required — commits external data dependencies + live-time cost
supersedes: none
---

# ADR-044 (PROPOSED) — Bhavcopy-Primary EOD Data, yfinance Quarantined

## Decision (proposed)

Phase 2's remaining fetch-adapter scope is implemented as:

1. **NSE official bhavcopy becomes the primary EOD source** — a native
   fetch adapter behind the existing `PriceProvider` port, vendoring
   jugaad-data's URL/cookie/holiday handling as own code (never a
   dependency: the package is unlicensed). Bhavcopy includes
   later-delisted stocks, closing the survivorship channel at the
   source (DD §9.2: survivor-only backtests inflate returns
   ~+4.94pp/yr on NSE smallcaps).
2. **yfinance is demoted to quarantined cross-check** — stays behind
   the data port, cache-once-read-forever, never primary, never in
   the daily decision path. Grounds (DD §9.3): per-IP rate-limiting,
   curl_cffi browser-impersonation dependency, false-delisted
   defects on `.NS` symbols, and silent historical revisions — fatal
   for byte-identical reruns.
3. **Kite Connect historical API** (₹500/mo, bundled with the
   execution plan already required for live) becomes the live-time
   feed — decision activates at cutover, not before.
4. **`exchange-calendars` (XNSE)** is adopted for the Clock port's
   trading calendar — closes the hand-maintained-holiday-table
   problem with a maintained Apache-2.0 dependency.

## Why proposed, not accepted

This ADR commits new external surfaces an autonomous session should
not self-approve: a scraping relationship with NSE's endpoints
(operational + ToS posture), a future paid data plan, and a new
runtime dependency. The engineering direction is fully evidenced
(DD §§9.1–9.3, M-6); the approval is the operator's.

## Consequences (when accepted)

- New work package (WP-018 candidate): bhavcopy fetch adapter +
  golden-file tests + quarantine wiring; `paper_trader.py`'s frozen
  yfinance path is untouched until cutover (freeze rule).
- Determinism strengthens: official immutable files replace a source
  that silently revises history.
- The daily loop loses its browser-impersonation dependency.

## Until then

Phase 2 implementation beyond this ADR is blocked on approval
(engineering-loop stop condition: "an ADR must be approved before
continuing"). Everything else in the current phase's actionable
backlog is complete as of 2026-07-21.
