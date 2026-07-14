"""Minimal execution engine (WP-008 slice of Phase 6, ADR-034).

Places CNC limit orders through any OrderPlacer, with a mandatory
pre-trade gate in front of every single order (no gate, no engine --
the no-bypass rule is a constructor requirement, not a convention) and
an order journal written through storage for every attempt, including
rejections. Same engine runs paper and live; only the injected adapter
differs (ADR-010).
"""

from typing import Protocol

from quantos_core.brokers import BrokerError, LimitOrder, OrderPlacer, OrderReceipt
from quantos_core.storage import Entity, Repository
from quantos_core.utils import get_logger


class ExecutionBlockedError(Exception):
    """An order was blocked before reaching the broker (gate refusal)."""


class PreTradeGate(Protocol):
    """The risk gate contract: raise to block, return to allow."""

    def check(self, order: LimitOrder) -> None: ...


class OrderJournalEntry(Entity):
    """Immutable record of one order attempt -- written for every
    outcome (filled, open, rejected, blocked), never only successes."""

    run_id: str
    ticker: str
    side: str
    quantity: int
    limit_price: float
    outcome: str
    broker_order_id: str | None
    detail: str


class ExecutionEngine:
    def __init__(
        self,
        broker: OrderPlacer,
        gate: PreTradeGate,
        journal: Repository[OrderJournalEntry],
        run_id: str,
    ) -> None:
        self._broker = broker
        self._gate = gate
        self._journal = journal
        self._run_id = run_id
        self._logger = get_logger("execution", run_id=run_id)
        # Resume numbering from what this run_id already journaled --
        # a re-run with the same run_id must append, never overwrite
        # (save() is an upsert; colliding ids would silently eat the
        # audit trail).
        self._sequence = len(self._journal.query({"run_id": run_id}))

    def _record(self, order: LimitOrder, outcome: str, broker_order_id: str | None, detail: str) -> None:
        self._sequence += 1
        entry = OrderJournalEntry(
            id=f"{self._run_id}-{self._sequence:04d}",
            run_id=self._run_id,
            ticker=order.ticker,
            side=order.side.value,
            quantity=order.quantity,
            limit_price=order.limit_price,
            outcome=outcome,
            broker_order_id=broker_order_id,
            detail=detail,
        )
        self._journal.save(entry)
        self._logger.info(
            "order_attempt",
            extra={
                "data": {
                    "ticker": order.ticker,
                    "side": order.side.value,
                    "quantity": order.quantity,
                    "limit_price": order.limit_price,
                    "outcome": outcome,
                    "broker_order_id": broker_order_id,
                }
            },
        )

    def execute(self, order: LimitOrder) -> OrderReceipt:
        """Gate -> place -> journal. Every path journals; every failure
        is a typed exception, never a silent skip."""
        try:
            self._gate.check(order)
        except Exception as exc:
            self._record(order, "BLOCKED", None, str(exc))
            raise ExecutionBlockedError(f"Pre-trade gate blocked {order.side.value} {order.ticker}: {exc}") from exc
        try:
            receipt = self._broker.place_order(order)
        except BrokerError as exc:
            self._record(order, "FAILED", None, str(exc))
            raise
        except Exception as exc:
            # A non-broker exception mid-placement (adapter bug, parse
            # crash) leaves the order state UNKNOWN. It must still hit
            # the journal -- "every path journals" has no exceptions --
            # then propagate for reconciliation.
            self._record(order, "UNKNOWN", None, f"non-broker failure mid-placement: {exc}")
            raise
        self._record(order, receipt.status, receipt.broker_order_id, f"filled={receipt.filled_quantity}")
        return receipt
