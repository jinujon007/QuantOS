---
type: adr
number: 044
date: 2026-07-21
status: accepted  # operator approved 2026-07-21 ("do it"), same day as proposal
supersedes: none
---

# ADR-044 — Bhavcopy-Primary EOD Data, yfinance Quarantined

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

## Approval

Filed as proposed (external data surfaces + future paid plan are the
operator's call, not an autonomous session's); operator approved
2026-07-21 same-day. **Acceptance correction:** exchange-calendars has
no ``XNSE`` calendar — the Indian equity calendar is registered as
``XBOM`` (NSE/BSE share the trading-holiday calendar); item 4 is
implemented with XBOM (v4.13.2, verified: 2026-07-20 session, Sundays
and Republic Day 2026 non-sessions).

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
