---
type: adr
number: 034
date: 2026-07-14
status: accepted
supersedes: none
---

# ADR-034 — Demo Vertical Slice Ahead of Roadmap Phase Order (WP-008)

## Decision

Build thin slices of `brokers` (Phase 6/8), `risk` kill switch
(Phase 4), and `execution` (Phase 6) now — ahead of Phase 2/3
completion — as one demoable vertical: PaperBrokerAdapter (ADR-011
implementation #1) plus native ZerodhaKiteAdapter and
AngelOneSmartApiAdapter (implementations #2 and #3 of the same
segregated ports, per ADR-012), the persisted kill switch (ADR-009),
and a minimal limit-order-only execution engine, driven end-to-end by
`tools/demo_pipeline.py` in paper mode.

## Context

Operator direction (Jinu, 2026-07-14): a working demo is the
condition for continuing the roadmap, and BOTH Zerodha and Angel One
must be connectable — broker choice deliberately open (the 2026-07-14
verified research recommends Zerodha primary/Fyers backup, but the
operator has not ratified retiring Angel One; both adapters keep that
decision open at near-zero extra cost since they implement one port).

## Why this does not break the freeze or the roadmap's safety intent

- Zero live-capital risk: the demo runs PaperBrokerAdapter only; real
  adapters refuse to construct without credentials, and no credentials
  exist yet. Phase 8's gate (SEBI checklist, staged rollout) is
  untouched.
- Prospective Validation untouched: the demo computes a clearly-labeled
  DEMO approximation of the momentum rank via `quantos_core.data`; the
  validated strategy stays frozen in `paper_trader.py`, unmodified,
  and demo output is never a trading signal.
- Interfaces are the frozen ones: ports per ADR-011/012, kill switch
  per ADR-009 (a `storage` flag checked before every order, no
  bypass), limit-orders-only per the verified SEBI/NSE constraint.
- ADR-032 boundaries hold mechanically (brokers→utils only;
  execution→brokers/storage/utils/monitoring; risk→storage/utils/
  monitoring); the WP-005 CI gate enforces this on every run.
- Remaining phase work (real order lifecycle states, reconciliation,
  slippage metrics, SAFE_MODE heartbeats, OAuth flows under SEBI
  rules) stays owned by Phases 4/6/7/8 — this ADR builds the seam,
  not the phase.

## Alternatives Considered

- **Refuse until Phases 2-5 complete.** Rejected: operator explicitly
  conditioned continued work on a demo; the slice carries no capital
  risk and every line lands behind the frozen interfaces it would
  eventually need anyway.
- **Demo via OpenAlgo instead of native adapters.** Rejected per the
  verified 2026-07-14 research: REFERENCE only, never in the order
  path.

## Consequences

- Phase 6/8 work packages later *harden* these adapters (order
  lifecycle, reconciliation, heartbeats) rather than create them.
- The Angel One adapter exists despite the research recommendation to
  retire it — cost: one file behind the same port; benefit: broker
  decision stays genuinely open until the operator ratifies it.
- The demo tool lives in `tools/` (dependency leaf) and may compose
  modules freely; nothing in `quantos_core` depends on it.
