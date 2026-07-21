---
type: report
date: 2026-07-22
area: self
project: AlgoTrader
status: active
ai_generated: true
---

# Program Log — 2026-07-22 (Phase 2 completion loop: WP-019/020/021)

Session record, per the 2026-07-14 program-log convention. Operator
directive: **"complete Phase 2 in loop until perfect."** Everything
below is committed on branch `docs/institutional-dd-2026-07-21`
([PR #1](https://github.com/jinujon007/QuantOS/pull/1)), CI-gated.

## 1. Scope executed

The three capabilities CURRENT_TASK carried as "Next Phase 2 WPs"
after WP-018 — corporate actions, quality validators, bhavcopy-backed
PriceProvider — all shipped under **ADR-045** (accepted: in-scope
execution of the operator directive; adds no external surface beyond
what ADR-044 already approved).

| WP | Delivered |
|---|---|
| WP-019 | `quantos_core/data/nse_pr.py` + `corporate_actions.py` — corporate-action adjustment from **NSE's official Bc records** (the `Bc*.csv` member of each session's PR bundle, same cookie-free archives host as the bhavcopy). Purpose strings with exact price effects become events: `BONUS a:b` → b/(a+b), `FVSPLT`/`FVCONS` → new/old FV, compounds multiply; dividends are price-neutral; rights/schemes are deliberately never guessed. Fail-closed on format drift (both Bc naming/date eras handled), factors outside [0.01, 100], degenerate ratios. |
| WP-020 | `quantos_core/data/quality.py` — `DataQualityError(DataFetchError)` + `validate_close_frame`: exact XBOM-calendar coverage, no missing/non-positive closes, single-session moves capped at ±35% (tunable) on adjusted series. Constitution Part V "data-quality failure" made concrete; passing frames are fully dense and in-band. |
| WP-021 | `quantos_core/data/bhavcopy_prices.py` — `BhavcopyPriceProvider` behind the frozen `PriceProvider` port: reads `data/bhavcopy/` + `data/nse_pr/`, applies WP-019 adjustment (dedup across daily re-listings; future-dated records never applied), enforces WP-020 validation, window-end price basis, per-instance session caches. An archive gap is a typed failure naming `tools/fetch_bhavcopy.py`; a quality failure co-located with an uncomputable official record (rights/demerger) names that record. Plus `sessions_between` calendar helper and the two-file **range mode** in `tools/fetch_bhavcopy.py` (`--start/--end`, politeness delay, continues past per-session failures, idempotent re-runs fill only gaps). |

## 2. Disproven hypothesis — the loop's key event

The first WP-019 design derived factors from the UDiFF bhavcopy's own
`PrvsClsgPric` (assumption: NSE republishes prev-close adjusted on
ex-dates). All synthetic tests passed; the **first run against the
real archive failed loudly**: HDFCBANK's 1:1 bonus ex 2025-08-26 is
published with a *raw* prev-close (1964.10), so the adjusted series
showed -50.4% and the WP-020 gate halted — exactly the failure mode it
exists for. Verified `sec_bhavdata_full` behaves the same. The design
was replaced in the same loop iteration with the official-record
approach (PR bundle `Bc*.csv`, verified live: HDFCBANK "BONUS 1:1"
EX_DT 26/08/2025, forward-listed and on-date). Full record in
ADR-045's "Disproven hypothesis" section.

## 3. Archive backfill (live network operation)

Bhavcopies: `--start 2025-06-02 --end 2026-07-20` → **279/279
sessions archived clean** (280 files with 2026-07-21, ~50 MB,
`data/bhavcopy/`). PR bundles: same range through 2026-07-21 →
`data/nse_pr/`. Both gitignored, regenerable, immutable. Zero 404s —
the XBOM calendar matched NSE's actual sessions across the full
13.5-month window. Enough history for Momentum's 12-1 lookback at the
Phase 6 cutover.

## 4. Live verification on real data

`BhavcopyPriceProvider` exercised against the real backfilled archives
(RELIANCE, TCS, HDFCBANK, INFY; window 2025-06-02 → 2026-07-21):
serves a fully-validated 280-session × 4-symbol frame in ~17s (cached
re-reads ~0.01s); HDFCBANK's bonus-adjusted series passes the quality
gate with the pre-ex close back-adjusted to exactly 982.05 = 1964.10
× 0.5 and a max single-session move of 1.6% around the ex-date;
RELIANCE 2026-07-20 close 1323.10 matches the WP-018 golden value.
Both backfills finished 100% clean: 279/279 bhavcopies + 280/280 PR
bundles.

## 5. Adversarial review round (loop iteration 3)

An independent adversarial-review agent examined the shipped slice:
seven findings (3 high), all fixed and test-pinned same session — full
list in ADR-045's hardening section. The highest-value outcomes, both
verified against the real archive:

- The ADV-1 fix (unparseable bonus/split family → halt, never silent
  no-factor) immediately caught **8 real split wording variants** in
  the live archive that the original regex missed ("FV SPLT FRM RS 2
  TO RE 1", "FVSPLT FRMRS 100 TO RE 1", ...) — parser widened, all 8
  now compute exact factors; 720 distinct live purposes scan clean
  with exactly one remaining (correct) halt: TVSMOTOR's uncomputable
  NCRPS bonus ex 2025-08-25.
- The ADV-2 fix (45-session Bc lookback before the window) answers a
  confirmed live behaviour: 262/6,530 records drop off the Bc file
  before their ex-date (max gap 21 sessions).

## 6. Gates at close

341 offline tests (282 → 341; +59 across the three WPs, PR fetch,
range mode, and review-round pins) · ruff check · ruff format ·
`mypy --strict -p quantos_core` (50 files) · determinism 3×
byte-identical (`e3d29859…` / `6192c9d6…`) · import-boundary matrix ·
INVENTORY.md regenerated post-staging. All green.

## 7. Phase 2 status after this session

Constitutional Phase 2 scope — DataProvider port (WP-007), PIT
universe store (WP-007, weekly snapshots since 2026-07-14), corporate
actions (WP-019), quality validation (WP-020) — is **code-complete**,
with the bhavcopy-primary source (WP-018) and consuming provider
(WP-021) shipped and live-verified. Accepted, documented limits:
pre-2026 PIT universe *history* remains unavailable (recorded in the
DD 2026-07-21); bhavcopy series are price-return (ordinary dividends
unadjusted — divergence to be quantified by the shadow harness at
cutover); index/regime data stays on the quarantined yfinance path
until the Phase 6 indices adapter. Frozen scripts untouched; the
validation clock is intact.

## 8. Next

Phase 3 continuation (remaining strategy migrations) or Phase 4
risk-engine expansion per roadmap; operator queue unchanged
(SEBI/Zerodha checklist, `QUANTOS_ALERT_URL`, off-machine backup dir,
cutover decision after Fri 2026-07-25, PR #1 review/merge).
