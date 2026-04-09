from __future__ import annotations

from typing import Any

from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.events import PositionClosed
from nautilus_trader.model.events import PositionOpened
from nautilus_trader.trading.strategy import Strategy

from mgc_bt.backtest.state import StrategyDecision
from mgc_bt.backtest.state import TradeDirection


class BaseResearchStrategy(Strategy):
    def __init__(self, config: Any, engine: Any) -> None:
        super().__init__(config)
        self._engine = engine

    def on_start(self) -> None:
        self._engine.start()
        instrument = self.cache.instrument(self.config.instrument_id)
        if instrument is None:
            self.log.error(f"Could not find instrument for {self.config.instrument_id}")
            self.stop()
            return
        self.subscribe_bars(self.config.bar_type)
        self.subscribe_trade_ticks(self.config.instrument_id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        self._engine.on_trade_tick(tick)

    def on_bar(self, bar: Bar) -> None:
        decision = self._engine.on_bar(bar, account_equity=self._current_account_equity())
        self._handle_decision(decision)

    def on_position_opened(self, event: PositionOpened) -> None:
        self._engine.on_position_opened(event)

    def on_position_closed(self, event: PositionClosed) -> None:
        self._engine.on_position_closed(event)

    def on_stop(self) -> None:
        self.close_all_positions(self.config.instrument_id)
        self._engine.stop()

    def _handle_decision(self, decision: StrategyDecision) -> None:
        if not decision.has_action:
            return
        if decision.exit_trade and self._engine.state.position_open and not self._engine.state.exit_pending:
            self.close_all_positions(self.config.instrument_id)
            self._engine.exit_submitted(decision.reason)
            return
        if decision.enter_direction is None or self._engine.state.position_open or self._engine.state.entry_pending:
            return
        self._submit_entry_order(decision.enter_direction)
        self._engine.entry_submitted(decision.enter_direction)

    def _submit_entry_order(self, direction: TradeDirection) -> None:
        side = OrderSide.BUY if direction == TradeDirection.LONG else OrderSide.SELL
        instrument = self.cache.instrument(self.config.instrument_id)
        if instrument is None:
            self.log.error(f"Could not find instrument for {self.config.instrument_id}")
            self.stop()
            return
        order = self.order_factory.market(
            self.config.instrument_id,
            side,
            instrument.make_qty(self.config.trade_size),
        )
        self.submit_order(order)

    def _current_account_equity(self) -> float | None:
        account = self.portfolio.account(venue=self.config.instrument_id.venue)
        if account is None:
            account = self.cache.account_for_venue(venue=self.config.instrument_id.venue)
        if account is None:
            return None

        balance_total = account.balance_total()
        if balance_total is None:
            return None
        return float(balance_total.as_double())
