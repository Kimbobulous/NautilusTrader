from __future__ import annotations

from collections import defaultdict
from collections import deque
from decimal import Decimal
from enum import Enum
from typing import Any

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import PositionSide
from nautilus_trader.model.events import PositionClosed
from nautilus_trader.model.events import PositionOpened
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

from mgc_bt.backtest.indicators import AdaptiveSuperTrendIndicator
from mgc_bt.backtest.indicators import AtrIndicator
from mgc_bt.backtest.indicators import FractalPivotTracker
from mgc_bt.backtest.indicators import RollingMeanIndicator
from mgc_bt.backtest.indicators import SessionVwapIndicator
from mgc_bt.backtest.indicators import WaveTrendIndicator
from mgc_bt.backtest.risk import RiskManager
from mgc_bt.backtest.state import BarSnapshot
from mgc_bt.backtest.state import PendingInsideBar
from mgc_bt.backtest.state import StrategyDecision
from mgc_bt.backtest.state import StrategyPhase
from mgc_bt.backtest.state import StrategyRuntimeState
from mgc_bt.backtest.state import TradeDirection

WAVETREND_ZSCORE_LOOKBACK = 20
WAVETREND_HMA_LENGTH = 12
PINBAR_LOOKBACK = 6
MIN_READY_BARS = 200


class CandleConfirmation(str, Enum):
    NONE = "none"
    PIN_BAR = "pin_bar"
    SHAVED_BAR = "shaved_bar"
    INSIDE_BREAKOUT = "inside_breakout"


class MgcStrategyConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    supertrend_atr_length: int
    supertrend_factor: float
    supertrend_training_period: int
    vwap_reset_hour_utc: int
    wavetrend_n1: int
    wavetrend_n2: int
    wavetrend_ob_level: float
    delta_imbalance_threshold: float
    absorption_volume_multiplier: float
    absorption_range_multiplier: float
    volume_lookback: int
    atr_trail_length: int
    atr_trail_multiplier: float
    min_pullback_bars: int
    max_loss_per_trade_dollars: float
    max_daily_trades: int
    max_daily_loss_dollars: float
    max_consecutive_losses: int
    min_account_equity: float
    max_drawdown_pct: float


class MgcSignalEngine:
    def __init__(self, config: MgcStrategyConfig) -> None:
        self.config = config
        self.state = StrategyRuntimeState()
        self.supertrend = AdaptiveSuperTrendIndicator(
            atr_length=config.supertrend_atr_length,
            factor=config.supertrend_factor,
            training_period=config.supertrend_training_period,
        )
        self.vwap = SessionVwapIndicator(reset_hour_utc=config.vwap_reset_hour_utc)
        self.wavetrend = WaveTrendIndicator(
            n1=config.wavetrend_n1,
            n2=config.wavetrend_n2,
            zscore_lookback=WAVETREND_ZSCORE_LOOKBACK,
            hma_length=WAVETREND_HMA_LENGTH,
        )
        self.atr_trail = AtrIndicator(config.atr_trail_length)
        self.volume_mean = RollingMeanIndicator(config.volume_lookback)
        self.range_mean = RollingMeanIndicator(config.volume_lookback)
        self.swing_highs = FractalPivotTracker("high")
        self.swing_lows = FractalPivotTracker("low")
        self.risk = RiskManager(
            max_loss_per_trade_dollars=config.max_loss_per_trade_dollars,
            max_daily_trades=config.max_daily_trades,
            max_daily_loss_dollars=config.max_daily_loss_dollars,
            max_consecutive_losses=config.max_consecutive_losses,
            min_account_equity=config.min_account_equity,
            max_drawdown_pct=config.max_drawdown_pct,
        )
        self._bar_index = 0
        self._recent_bars: deque[BarSnapshot] = deque(maxlen=PINBAR_LOOKBACK + 3)
        self._bar_deltas: dict[int, float] = {}
        self._trade_buckets: dict[int, dict[str, float]] = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})

    @property
    def is_ready(self) -> bool:
        return (
            self._bar_index >= MIN_READY_BARS
            and self.supertrend.is_ready
            and self.vwap.is_ready
            and self.wavetrend.is_ready
            and self.atr_trail.is_ready
            and self.volume_mean.is_ready
            and self.range_mean.is_ready
        )

    def on_trade_tick(self, tick: TradeTick) -> None:
        bucket = self._minute_bucket(tick.ts_event)
        size = float(tick.size)
        if tick.aggressor_side == AggressorSide.BUYER:
            self._trade_buckets[bucket]["buy"] += size
        elif tick.aggressor_side == AggressorSide.SELLER:
            self._trade_buckets[bucket]["sell"] += size

    def on_bar(self, bar: Bar, account_equity: float | None = None) -> StrategyDecision:
        snapshot = self._to_snapshot(bar)
        if account_equity is not None:
            self.risk._sync_session(snapshot.ts_event_ns, account_equity)
        bucket = self._minute_bucket(snapshot.ts_event_ns)
        bucket_data = self._trade_buckets.pop(bucket, {"buy": 0.0, "sell": 0.0})
        delta_value = bucket_data["buy"] - bucket_data["sell"]
        self._bar_deltas[bucket] = delta_value

        prior_volume_avg = self.volume_mean.value
        prior_range_avg = self.range_mean.value
        self.volume_mean.update(snapshot.volume)
        self.range_mean.update(snapshot.range)
        self.vwap.update(snapshot)
        self.supertrend.update(snapshot)
        self.wavetrend.update(snapshot)
        atr_value = self.atr_trail.update(snapshot)

        confirmed_high = self.swing_highs.update(snapshot.index, snapshot.high)
        if confirmed_high is not None:
            self.state.last_confirmed_swing_high = confirmed_high
        confirmed_low = self.swing_lows.update(snapshot.index, snapshot.low)
        if confirmed_low is not None:
            self.state.last_confirmed_swing_low = confirmed_low

        candle_confirmation = self._candle_confirmation(snapshot)
        trend_direction = self._trend_direction(snapshot)
        decision = StrategyDecision()

        if self.state.position_open and atr_value is not None:
            decision = self._manage_open_trade(snapshot, trend_direction, atr_value, account_equity)
        elif not self.state.entry_pending and not self.state.exit_pending and self.is_ready:
            decision = self._evaluate_setup(
                snapshot,
                trend_direction,
                delta_value,
                prior_volume_avg,
                prior_range_avg,
                candle_confirmation,
                atr_value,
                account_equity,
            )

        self._update_inside_bar_state(snapshot)
        self._recent_bars.append(snapshot)
        self._bar_index += 1
        return decision

    def on_position_opened(self, side: PositionSide, avg_px_open: float) -> None:
        self.state.position_open = True
        self.state.entry_pending = False
        self.state.exit_pending = False
        self.state.phase = StrategyPhase.IN_TRADE
        if side == PositionSide.LONG:
            self.state.position_direction = TradeDirection.LONG
        elif side == PositionSide.SHORT:
            self.state.position_direction = TradeDirection.SHORT
        self.state.highest_close_since_entry = avg_px_open
        self.state.lowest_close_since_entry = avg_px_open
        self.state.current_trailing_stop = None

    def on_position_closed(self) -> None:
        self.state = StrategyRuntimeState(
            last_confirmed_swing_high=self.state.last_confirmed_swing_high,
            last_confirmed_swing_low=self.state.last_confirmed_swing_low,
            pending_inside_bar=self.state.pending_inside_bar,
        )

    def entry_submitted(self, direction: TradeDirection) -> None:
        self.state.phase = StrategyPhase.IN_TRADE
        self.state.armed_direction = direction
        self.state.position_direction = direction
        self.state.entry_pending = True

    def exit_submitted(self) -> None:
        self.state.exit_pending = True

    def _evaluate_setup(
        self,
        snapshot: BarSnapshot,
        trend_direction: TradeDirection | None,
        delta_value: float,
        prior_volume_avg: float | None,
        prior_range_avg: float | None,
        candle_confirmation: CandleConfirmation,
        atr_value: float | None,
        account_equity: float | None,
    ) -> StrategyDecision:
        if trend_direction is None:
            self.state.phase = StrategyPhase.FLAT
            self.state.armed_direction = None
            return StrategyDecision()

        if not self._pullback_qualified(trend_direction, snapshot.index):
            self.state.phase = StrategyPhase.FLAT
            self.state.armed_direction = None
            return StrategyDecision()

        self.state.phase = StrategyPhase.PULLBACK_ARMED
        self.state.armed_direction = trend_direction
        if not self._core_triggers_met(snapshot, trend_direction, delta_value, prior_volume_avg):
            return StrategyDecision()

        if not self._has_optional_confirmation(
            snapshot=snapshot,
            direction=trend_direction,
            prior_volume_avg=prior_volume_avg,
            prior_range_avg=prior_range_avg,
            candle_confirmation=candle_confirmation,
        ):
            return StrategyDecision()

        if account_equity is not None and atr_value is not None:
            stop_distance = atr_value * self.config.atr_trail_multiplier
            if not self.risk.can_enter(trend_direction, stop_distance, account_equity):
                return StrategyDecision()

        return StrategyDecision(
            enter_direction=trend_direction,
            reason=f"entry:{trend_direction.value.lower()}",
        )

    def _manage_open_trade(
        self,
        snapshot: BarSnapshot,
        trend_direction: TradeDirection | None,
        atr_value: float,
        account_equity: float | None,
    ) -> StrategyDecision:
        if self.state.exit_pending or self.state.position_direction is None:
            return StrategyDecision()

        if account_equity is not None and self.risk.should_exit(self.state, snapshot, account_equity):
            return StrategyDecision(exit_trade=True, reason="risk_halt")

        if self.state.position_direction == TradeDirection.LONG:
            self.state.highest_close_since_entry = max(self.state.highest_close_since_entry or snapshot.close, snapshot.close)
            next_stop = self.state.highest_close_since_entry - (atr_value * self.config.atr_trail_multiplier)
            self.state.current_trailing_stop = max(self.state.current_trailing_stop or next_stop, next_stop)
            hard_flip = trend_direction == TradeDirection.SHORT
            if snapshot.close <= (self.state.current_trailing_stop or float("-inf")):
                return StrategyDecision(exit_trade=True, reason="atr_stop_long")
            if hard_flip:
                return StrategyDecision(exit_trade=True, reason="hard_flip_long")

        if self.state.position_direction == TradeDirection.SHORT:
            self.state.lowest_close_since_entry = min(self.state.lowest_close_since_entry or snapshot.close, snapshot.close)
            next_stop = self.state.lowest_close_since_entry + (atr_value * self.config.atr_trail_multiplier)
            self.state.current_trailing_stop = min(self.state.current_trailing_stop or next_stop, next_stop)
            hard_flip = trend_direction == TradeDirection.LONG
            if snapshot.close >= (self.state.current_trailing_stop or float("inf")):
                return StrategyDecision(exit_trade=True, reason="atr_stop_short")
            if hard_flip:
                return StrategyDecision(exit_trade=True, reason="hard_flip_short")

        return StrategyDecision()

    def _trend_direction(self, snapshot: BarSnapshot) -> TradeDirection | None:
        if self.supertrend.direction == -1 and self.vwap.value is not None and snapshot.close > self.vwap.value:
            return TradeDirection.LONG
        if self.supertrend.direction == 1 and self.vwap.value is not None and snapshot.close < self.vwap.value:
            return TradeDirection.SHORT
        return None

    def _pullback_qualified(self, direction: TradeDirection, current_index: int) -> bool:
        if direction == TradeDirection.LONG and self.state.last_confirmed_swing_low is not None:
            return (current_index - self.state.last_confirmed_swing_low.index) >= self.config.min_pullback_bars
        if direction == TradeDirection.SHORT and self.state.last_confirmed_swing_high is not None:
            return (current_index - self.state.last_confirmed_swing_high.index) >= self.config.min_pullback_bars
        return False

    def _core_triggers_met(
        self,
        snapshot: BarSnapshot,
        direction: TradeDirection,
        delta_value: float,
        prior_volume_avg: float | None,
    ) -> bool:
        if prior_volume_avg is None or snapshot.volume <= prior_volume_avg:
            return False
        if snapshot.volume <= 0:
            return False
        if abs(delta_value) < (self.config.delta_imbalance_threshold * snapshot.volume):
            return False
        if direction == TradeDirection.LONG:
            return delta_value > 0 and snapshot.is_bullish
        return delta_value < 0 and snapshot.is_bearish

    def _has_optional_confirmation(
        self,
        snapshot: BarSnapshot,
        direction: TradeDirection,
        prior_volume_avg: float | None,
        prior_range_avg: float | None,
        candle_confirmation: CandleConfirmation,
    ) -> bool:
        return any(
            [
                self._absorption_confirmed(snapshot, direction, prior_volume_avg, prior_range_avg),
                candle_confirmation is not CandleConfirmation.NONE,
                self._wavetrend_confirmed(direction),
            ],
        )

    def _absorption_confirmed(
        self,
        snapshot: BarSnapshot,
        direction: TradeDirection,
        prior_volume_avg: float | None,
        prior_range_avg: float | None,
    ) -> bool:
        if prior_volume_avg is None or prior_range_avg is None or snapshot.range <= 0:
            return False
        if snapshot.volume <= (prior_volume_avg * self.config.absorption_volume_multiplier):
            return False
        if snapshot.range >= (prior_range_avg * self.config.absorption_range_multiplier):
            return False
        close_location = (snapshot.close - snapshot.low) / snapshot.range
        if direction == TradeDirection.LONG:
            return close_location >= 0.6
        return close_location <= 0.4

    def _wavetrend_confirmed(self, direction: TradeDirection) -> bool:
        if direction == TradeDirection.LONG:
            return self.wavetrend.bullish_divergence or (
                self.wavetrend.zscore is not None and self.wavetrend.zscore <= -self.config.wavetrend_ob_level
            )
        return self.wavetrend.bearish_divergence or (
            self.wavetrend.zscore is not None and self.wavetrend.zscore >= self.config.wavetrend_ob_level
        )

    def _candle_confirmation(self, snapshot: BarSnapshot) -> CandleConfirmation:
        if self._inside_bar_breakout(snapshot) is not None:
            return CandleConfirmation.INSIDE_BREAKOUT
        if self._pin_bar(snapshot) is not None:
            return CandleConfirmation.PIN_BAR
        if self._shaved_bar(snapshot) is not None:
            return CandleConfirmation.SHAVED_BAR
        return CandleConfirmation.NONE

    def _pin_bar(self, snapshot: BarSnapshot) -> TradeDirection | None:
        if snapshot.range <= 0 or len(self._recent_bars) < PINBAR_LOOKBACK:
            return None
        lower_wick = min(snapshot.open, snapshot.close) - snapshot.low
        upper_wick = snapshot.high - max(snapshot.open, snapshot.close)
        close_location = (snapshot.close - snapshot.low) / snapshot.range
        prior_lows = [bar.low for bar in list(self._recent_bars)[-PINBAR_LOOKBACK:]]
        prior_highs = [bar.high for bar in list(self._recent_bars)[-PINBAR_LOOKBACK:]]
        if lower_wick >= (0.66 * snapshot.range) and close_location >= 0.66 and snapshot.low < min(prior_lows):
            return TradeDirection.LONG
        if upper_wick >= (0.66 * snapshot.range) and close_location <= 0.34 and snapshot.high > max(prior_highs):
            return TradeDirection.SHORT
        return None

    def _shaved_bar(self, snapshot: BarSnapshot) -> TradeDirection | None:
        if snapshot.range <= 0:
            return None
        close_location = (snapshot.close - snapshot.low) / snapshot.range
        if close_location >= 0.95:
            return TradeDirection.LONG
        if close_location <= 0.05:
            return TradeDirection.SHORT
        return None

    def _inside_bar_breakout(self, snapshot: BarSnapshot) -> TradeDirection | None:
        if self.state.pending_inside_bar is None:
            return None
        if snapshot.index != self.state.pending_inside_bar.index + 1:
            return None
        if snapshot.close > self.state.pending_inside_bar.high:
            return TradeDirection.LONG
        if snapshot.close < self.state.pending_inside_bar.low:
            return TradeDirection.SHORT
        return None

    def _update_inside_bar_state(self, snapshot: BarSnapshot) -> None:
        if self._recent_bars:
            previous = self._recent_bars[-1]
            if snapshot.high < previous.high and snapshot.low > previous.low:
                self.state.pending_inside_bar = PendingInsideBar(high=snapshot.high, low=snapshot.low, index=snapshot.index)
                return
        self.state.pending_inside_bar = None

    def _minute_bucket(self, ts_event_ns: int) -> int:
        return ts_event_ns // 60_000_000_000

    def _to_snapshot(self, bar: Bar) -> BarSnapshot:
        return BarSnapshot(
            index=self._bar_index,
            open=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close),
            volume=float(bar.volume),
            ts_event_ns=int(bar.ts_event),
        )


class MgcProductionStrategy(Strategy):
    def __init__(self, config: MgcStrategyConfig):
        super().__init__(config)
        self._engine = MgcSignalEngine(config)

    def on_start(self) -> None:
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
        if not decision.has_action:
            return
        if decision.exit_trade and self._engine.state.position_open and not self._engine.state.exit_pending:
            self.close_all_positions(self.config.instrument_id)
            self._engine.exit_submitted()
            return
        if decision.enter_direction is None or self._engine.state.position_open or self._engine.state.entry_pending:
            return

        side = OrderSide.BUY if decision.enter_direction == TradeDirection.LONG else OrderSide.SELL
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
        self._engine.entry_submitted(decision.enter_direction)

    def on_position_opened(self, event: PositionOpened) -> None:
        self._engine.on_position_opened(event.side, float(event.avg_px_open))

    def on_position_closed(self, event: PositionClosed) -> None:
        self._engine.on_position_closed()

    def on_stop(self) -> None:
        self.close_all_positions(self.config.instrument_id)

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
