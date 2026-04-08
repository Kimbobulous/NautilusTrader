from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy


class Phase2HarnessConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal


class Phase2HarnessStrategy(Strategy):
    """
    Minimal Phase 2 runner-enablement strategy.

    It reacts only to completed 1-minute bars so the backtest plumbing, native
    next-bar latency model, reporting, and artifact contracts can be proven
    before Phase 3 implements the actual production signal logic.
    """

    def __init__(self, config: Phase2HarnessConfig):
        super().__init__(config)
        self._last_close: float | None = None

    def on_start(self) -> None:
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar) -> None:
        close_price = float(bar.close)
        if self._last_close is None:
            self._last_close = close_price
            return

        desired_side: OrderSide | None = None
        if close_price > self._last_close:
            desired_side = OrderSide.BUY
        elif close_price < self._last_close:
            desired_side = OrderSide.SELL

        self._last_close = close_price
        if desired_side is None:
            return

        if self.portfolio.is_flat(self.config.instrument_id):
            self._submit_market_order(desired_side)
            return

        if desired_side == OrderSide.BUY and self.portfolio.is_net_short(self.config.instrument_id):
            self.close_all_positions(self.config.instrument_id)
            self._submit_market_order(OrderSide.BUY)
        elif desired_side == OrderSide.SELL and self.portfolio.is_net_long(self.config.instrument_id):
            self.close_all_positions(self.config.instrument_id)
            self._submit_market_order(OrderSide.SELL)

    def on_stop(self) -> None:
        self.close_all_positions(self.config.instrument_id)

    def _submit_market_order(self, side: OrderSide) -> None:
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
