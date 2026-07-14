---
type: work-package
id: WP-008
date: 2026-07-14
status: complete
phase: demo-slice (ADR-034; slices of phases 4, 6, 8)
---

# WP-008 — Execution Vertical Slice (Demo)

## Objective

Operator direction: a working demo ASAP, with BOTH Zerodha and Angel
One connectable (broker decision deliberately open). Delivered as an
ADR-034-governed vertical slice: broker ports + three adapters, the
persisted kill switch, a gated execution engine, and a runnable
end-to-end demo — zero network, zero capital risk, zero frozen-file
changes.

## Delivered

**`quantos_core/brokers`** (imports only `utils` — ADR-032 verified by
the WP-005 gate):
- `LimitOrder` / `OrderReceipt` / typed errors. Market orders are
  *unrepresentable by type construction* (SEBI/NSE algo rules: limit
  orders only).
- Segregated ports `OrderPlacer` + `AccountReader` (ADR-012).
- `PaperBrokerAdapter` (ADR-011 #1): deterministic limit-fill
  semantics, real cash/holdings discipline, overspend/oversell reject.
- `ZerodhaKiteAdapter` (#2): native Kite Connect v3 HTTP (no stale SDK
  dependency); free Personal-plan endpoints; CNC limit orders,
  holdings, margins. **No POST retries** — connection failure =
  UNKNOWN state, reconciliation required (Constitution Part V).
- `AngelOneSmartApiAdapter` (#3): native SmartAPI HTTP; TOTP login
  method (SEBI 2FA); DELIVERY product mapping, `-EQ` suffix,
  symboltoken injection (instrument-master download is Phase 8
  hardening). Same no-retry rule. Quirks pattern-verified against the
  OpenAlgo reference tree, reimplemented not copied.
- All three adapters substitutable behind the same port (tested).

**`quantos_core/risk`** (slice of Phase 4): `KillSwitch` — persisted
via `storage.Repository` (ADR-009), fail-closed with zero exceptions
(unreadable state = engaged); `KillSwitchGate` — the pre-trade gate
seam Phase 4 extends with the full Part V control table.

**`quantos_core/execution`** (slice of Phase 6): `ExecutionEngine` —
constructor-mandatory `PreTradeGate` (no gate, no engine = no bypass
path), places through any `OrderPlacer`, journals EVERY attempt
(FILLED/OPEN/REJECTED/FAILED/BLOCKED) via `Repository[OrderJournalEntry]`,
emits structured JSON log events (WP-004 logger).

**Tools** (dependency leaves):
- `tools/demo_pipeline.py` — the demo: config → PIT universe (real
  2026-07-14 snapshot) → fail-closed cached prices (444 served / 60
  skipped, counted) → labeled DEMO momentum rank → gated limit orders
  → paper fills → kill-switch drill (order BLOCKED) → audit trail.
  **Executed successfully end-to-end this WP.**
- `tools/broker_connect_check.py` — read-only connectivity probe for
  real credentials (env-var supplied, never files); places nothing.

## Governance

- ADR-034 records the deviation (demo slice ahead of phase order) and
  why it does not touch the freeze, live-capital gates, or frozen
  interfaces. Prospective Validation clock unaffected: demo rank is
  labeled non-signal; `paper_trader.py` untouched.
- Broker decision stays open per operator: both adapters ship behind
  one port; the 2026-07-14 research recommendation (Zerodha primary /
  retire Angel) awaits operator ratification — cost of keeping both
  is one file.

## Validation

| Gate | Result |
|---|---|
| `ruff check` / `format --check` | Clean |
| `mypy --strict -p quantos_core` | Success — **34** source files (was 26) |
| `pytest -m "not network"` | **131 passed** (37 new slice cases; zero network anywhere — fake transports catch retry bugs by construction) |
| Coverage `quantos_core/*` | **100%** (468 stmts, 0 miss) |
| `tools/verify_determinism.py 3` | 3/3 byte-identical; baseline sha `e3d29859aa00...` unchanged |
| Six frozen scripts | `git diff` empty |
| Demo | Ran end-to-end: 7 fills, 3 too-expensive skips, kill-switch drill BLOCKED, 8 journal rows persisted |

## Out of Scope (owned by later phases)

Order-book reconciliation & fill confirmation loop, SAFE_MODE broker
heartbeats, slippage metrics, position/sector/drawdown limits in the
gate, Angel instrument-master download, OAuth request-token automation
for Zerodha, credential storage in the OS secret store (probe uses env
vars, documented).

## Next

Operator: run the demo (`python tools/demo_pipeline.py`); create
Zerodha and/or Angel API keys and run
`tools/broker_connect_check.py both` to see the real adapters
authenticate. Engineering: Phase 2 continuation, then Phase 3
(strategy port) — after which the demo pipeline's rank is replaced by
the real frozen strategy behind the `Strategy` interface.
