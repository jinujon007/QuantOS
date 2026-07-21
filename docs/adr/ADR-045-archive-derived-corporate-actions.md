---
type: adr
number: 045
date: 2026-07-22
status: accepted  # in-scope execution of the operator's "complete Phase 2" directive (2026-07-22); same archives host ADR-044 approved
supersedes: none
---

# ADR-045 — Official-Record Corporate Actions, Fail-Closed Quality Gate, Bhavcopy PriceProvider

## Decision

The three remaining Phase 2 capabilities (corporate actions, quality
validation, bhavcopy-backed prices — CURRENT_TASK "Next Phase 2 WPs",
DD 2026-07-21 §11 data-platform gaps) are implemented as one coherent
slice over NSE's cookie-free archives host, the surface ADR-044
already adopted:

1. **Corporate-action adjustment comes from NSE's official Bc
   records** (`quantos_core/data/nse_pr.py` +
   `quantos_core/data/corporate_actions.py`, WP-019). Each session's
   PR bundle (`PR<ddmmyy>.zip`, same host as the bhavcopy, no
   cookies) contains a `Bc*.csv` member — the exchange's official
   corporate-action record (symbol, ex-date, purpose). Purposes whose
   price effect is exactly computable become back-adjustment events:
   `BONUS a:b` → factor b/(a+b); `FVSPLT`/`FVCONS FRM RS x TO RS y` →
   y/x; compound purposes multiply. Dividend/interest/meeting records
   are price-neutral by exchange rule and yield no factor. Anything
   else (rights, schemes of arrangement) is deliberately **not
   guessed**: if such an action moves a price beyond the quality
   band, the provider halts and names the official record. Factors
   outside a [0.01, 100] sanity band fail closed as data defects.
2. **A fail-closed data-quality gate** (`quantos_core/data/quality.py`,
   WP-020) validates every close frame before it reaches a consumer:
   exact trading-calendar coverage (XBOM), no missing or non-positive
   closes, and no single-session move beyond ±35% (config-tunable) on
   an already-adjusted series — the Constitution Part V "data-quality
   failure" condition made concrete. `DataQualityError` subclasses
   `DataFetchError`, so every existing fail-closed handler already
   treats it as the hard stop it is.
3. **`BhavcopyPriceProvider`** (`quantos_core/data/bhavcopy_prices.py`,
   WP-021) serves adjusted, validated closes from `data/bhavcopy/` +
   `data/nse_pr/` behind the frozen `PriceProvider` port: every
   session in the window must be archived (a gap names
   `tools/fetch_bhavcopy.py`, never a narrower frame), adjustment and
   validation always run, prices are in the window-end basis
   (standard back-adjustment), future-dated records (Bc files list
   actions days ahead) are never applied, and duplicate listings of
   one action across daily files are applied exactly once.
4. **The archive fetches and backfills both files per session**:
   `tools/fetch_bhavcopy.py` archives the UDiFF bhavcopy and the PR
   bundle immutably; `--start/--end` walks NSE sessions with a
   politeness delay, continues past per-session failures, reports
   every gap, and is idempotent. Initial backfill 2025-06-02 →
   2026-07-21 executed and verified this session (279 + 1 sessions,
   both files) — enough history for Momentum's 12-1 lookback at
   cutover.

## Disproven hypothesis (recorded deliberately)

The first same-session design derived factors from the UDiFF
bhavcopy's own `PrvsClsgPric` (assumption: NSE republishes prev-close
adjusted on ex-dates, making the archive self-describing). **Tested
against the real archive and disproven:** HDFCBANK's 1:1 bonus ex
2025-08-26 was published with `PrvsClsgPric = 1964.10` — the raw prior
close (`sec_bhavdata_full` likewise). The WP-020 quality gate caught
the resulting -50.4% "move" on first live run, which is exactly the
failure mode it exists for. The design was replaced the same session
with the official-record approach above; the UDiFF prev-close field is
not an adjustment source and must not be reintroduced as one.

## Adversarial-review hardening (same session)

An independent adversarial review of the shipped slice produced seven
findings; all were fixed and each fix is pinned by a test:

- **ADV-1 (high):** a purpose naming a bonus/split whose ratio defeats
  the exact patterns now **halts** instead of silently returning
  no-factor (a missed 1:2..1:9 bonus lives inside the quality band).
  A live scan of all 720 distinct purposes in the archive then showed
  this catching **8 real split wording variants** ("FV SPLT", "FRMRS
  100", "TO RE1", "TO 1") — the parser was widened to compute them,
  and a paise-denominated change halts (100x hazard).
- **ADV-2 (high, confirmed live):** NSE drops some records from the
  Bc file before their ex-date (262/6,530 records, max gap 21
  sessions, including two real SME bonuses). The provider now scans a
  45-session lookback buffer before the window (best-effort at the
  archive's left edge; in-window files remain mandatory).
- **ADV-3 (high):** dedup was keyed on verbatim purpose wording; a
  re-worded listing of one action would double-apply its factor. Two
  records sharing (symbol, ex_date) with an equal factor from
  different wording now halt as ambiguous; different factors remain a
  legitimate compound.
- **ADV-4/5 (medium/low):** compound computable+uncomputable purposes
  ("BONUS 1:1 AND SCHEME OF ARRANGEMENT") and demerger-family records
  are now always named in quality-failure diagnostics (risky-family
  whitelist; word-bounded neutral markers so DEMERGER never hides
  behind the DIV substring).
- **ADV-7 (low):** exchange-calendars' native out-of-bounds errors
  are wrapped as `DataFetchError` inside the provider; the quality
  validator wraps non-numeric columns as `DataQualityError`.
- **ADV-6 (medium, accepted):** an ad-hoc NSE holiday unknown to the
  installed exchange-calendars release halts every window containing
  it (typed, loud) until the package is upgraded; ad-hoc special
  sessions outside XBOM are excluded from served frames. Both are
  accepted operational limits of adopting the maintained calendar —
  remediation is a package upgrade, not code.

**Known live specimen:** TVSMOTOR `SCH AGMT-BONUS NCRPS 4:1` ex
2025-08-25 is uncomputable from its purpose string (preference-share
bonus under a scheme); any window crossing that date halts with a
typed error naming the record. Operator resolution: verify the
exchange's actual base-price adjustment for that action and either
extend the parser with the verified value or avoid windows crossing
the date for that symbol.

## Accepted, documented divergences

- **Price-return, not total-return.** Exchanges do not adjust prices
  for ordinary dividends, so bhavcopy-derived series exclude dividend
  reinvestment; the quarantined yfinance path (auto-adjust) includes
  it. Price-adjusted momentum is standard institutional practice and
  the divergence (~1–1.5%/yr index-level dividend yield, largely
  rank-neutral) will be quantified by the WP-013 shadow harness at
  cutover before it can affect a book.
- **Uncomputable actions halt rather than approximate.** Rights
  issues and demergers have no exact factor derivable from the Bc
  purpose string; a halt naming the record is chosen over a silently
  wrong series. The escape hatch is the config-tunable band plus an
  operator decision — never a guessed factor.
- **Index levels (regime filter's ^NSEI) are not served** — the CM
  bhavcopy carries equities only. The regime input stays on the
  quarantined yfinance path until an indices adapter ships; that
  adapter is a named Phase 6 cutover prerequisite, not Phase 2 scope.

## Approval

ADR-044's approval covered the bhavcopy-primary architecture and its
fetch surface; this ADR reads one additional file from the **same
approved host** and otherwise executes the operator's explicit
2026-07-22 "complete Phase 2" directive — filed as accepted on that
authority. Reverting is one commit: the modules are additive, consumed
by nothing frozen (`paper_trader.py`'s yfinance path is untouched
until cutover, ADR-003).

## Consequences

- Phase 2's constitutional scope (DataProvider port, PIT universe
  store, corporate actions, quality validation) is code-complete;
  survivorship (F1/F9) and adjustment integrity are closed at the
  data layer for all post-archive history.
- Determinism: adjusted prices are a pure function of the immutable
  archives — byte-identical reruns hold as long as the archives are
  append-only.
- The Phase 6 cutover checklist gains two named items: an indices
  (regime) adapter, and the shadow-harness dividend-divergence
  quantification above.
