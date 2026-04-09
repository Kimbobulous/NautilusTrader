from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from mgc_bt.backtest.state import StrategyDecision
from mgc_bt.backtest.state import TradeDirection
from mgc_bt.backtest.strategy_base import BaseResearchStrategy
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import InstrumentId


class _TestStrategyConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal


class _StubEngine:
    def __init__(self, decision: StrategyDecision | None = None) -> None:
        self.decision = decision or StrategyDecision()
        self.started = False
        self.stopped = False
        self.trade_ticks: list[object] = []
        self.opened_events: list[object] = []
        self.closed_events: list[object] = []
        self.state = SimpleNamespace(position_open=False, exit_pending=False, entry_pending=False)
        self.exit_reason = None
        self.entry_direction = None

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def on_trade_tick(self, tick: object) -> None:
        self.trade_ticks.append(tick)

    def on_bar(self, bar: object, account_equity: float | None = None) -> StrategyDecision:
        return self.decision

    def on_position_opened(self, event: object) -> None:
        self.opened_events.append(event)

    def on_position_closed(self, event: object) -> None:
        self.closed_events.append(event)

    def entry_submitted(self, direction: TradeDirection) -> None:
        self.entry_direction = direction

    def exit_submitted(self, reason: str | None = None) -> None:
        self.exit_reason = reason


class _DummyStrategy(BaseResearchStrategy):
    def __init__(self, engine: _StubEngine) -> None:
        self.submitted_entries: list[TradeDirection] = []
        self.closed_positions: list[object] = []
        super().__init__(
            _TestStrategyConfig(
                instrument_id=InstrumentId.from_str("MGCJ1.GLBX"),
                bar_type=BarType.from_str("MGCJ1.GLBX-1-MINUTE-LAST-EXTERNAL"),
                trade_size=Decimal("1"),
            ),
            engine,
        )

    def _submit_entry_order(self, direction: TradeDirection) -> None:
        self.submitted_entries.append(direction)

    def close_all_positions(self, instrument_id) -> None:
        self.closed_positions.append(instrument_id)

    def _current_account_equity(self) -> float | None:
        return None


def test_base_strategy_submits_entry_order_from_shared_decision_flow() -> None:
    engine = _StubEngine(StrategyDecision(enter_direction=TradeDirection.LONG, reason="entry:long"))
    strategy = _DummyStrategy(engine)

    strategy.on_bar(SimpleNamespace())

    assert strategy.submitted_entries == [TradeDirection.LONG]
    assert engine.entry_direction == TradeDirection.LONG


def test_base_strategy_closes_positions_for_exit_decision() -> None:
    engine = _StubEngine(StrategyDecision(exit_trade=True, reason="risk_halt"))
    engine.state.position_open = True
    strategy = _DummyStrategy(engine)

    strategy.on_bar(SimpleNamespace())

    assert strategy.closed_positions == [strategy.config.instrument_id]
    assert engine.exit_reason == "risk_halt"


def test_base_strategy_forwards_trade_and_position_events() -> None:
    engine = _StubEngine()
    strategy = _DummyStrategy(engine)

    trade_tick = SimpleNamespace()
    open_event = SimpleNamespace()
    close_event = SimpleNamespace()

    strategy.on_trade_tick(trade_tick)
    strategy.on_position_opened(open_event)
    strategy.on_position_closed(close_event)

    assert engine.trade_ticks == [trade_tick]
    assert engine.opened_events == [open_event]
    assert engine.closed_events == [close_event]
