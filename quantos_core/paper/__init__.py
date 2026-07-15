"""Paper-trading orchestration (WP-013, ADR-038).

`run_cycle(as_of) -> CycleReport` -- one daily paper cycle over the
portfolio accounting core, with injected market data and state store.
Runs in shadow (tools/run_paper_cycle.py) beside `paper_trader.py`
until two consecutive clean weekly rebalances match; cutover is an
operator decision recorded in CONTEXT.md. Engine-mediated execution
(PaperBrokerAdapter fills) is the Phase 6 step, after cutover.

Imports strategies/portfolio/risk internally (within the frozen
ADR-032 cell); market data and persistence arrive from the shell.
"""

from quantos_core.paper.cycle import CycleReport, MarketSnapshot, StateStore, run_cycle

__all__ = ["CycleReport", "MarketSnapshot", "StateStore", "run_cycle"]
