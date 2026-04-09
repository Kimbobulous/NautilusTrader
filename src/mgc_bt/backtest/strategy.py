from __future__ import annotations

from collections import deque
from datetime import UTC
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import PositionSide
from nautilus_trader.model.events import PositionClosed
from nautilus_trader.model.events import PositionOpened
from nautilus_trader.model.identifiers import InstrumentId

from mgc_bt.backtest.indicators import AdaptiveSuperTrendIndicator
from mgc_bt.backtest.indicators import AtrIndicator
from mgc_bt.backtest.indicators import FractalPivotTracker
from mgc_bt.backtest.indicators import RollingMeanIndicator
from mgc_bt.backtest.indicators import SessionVwapIndicator
from mgc_bt.backtest.indicators import WaveTrendIndicator
from mgc_bt.backtest.analytics import AuditLogWriter
from mgc_bt.backtest.analytics import append_trade_metadata
from mgc_bt.backtest.analytics import classify_session
from mgc_bt.backtest.analytics import timestamp_from_ns
from mgc_bt.backtest.risk import RiskManager
from mgc_bt.backtest.strategy_base import BaseResearchStrategy
from mgc_bt.backtest.strategy_primitives import AbsorptionDetector
from mgc_bt.backtest.strategy_primitives import DeltaAccumulator
from mgc_bt.backtest.strategy_primitives import delta_pass
from mgc_bt.backtest.strategy_primitives import inside_bar_breakout_direction
from mgc_bt.backtest.strategy_primitives import pin_bar_direction
from mgc_bt.backtest.strategy_primitives import shaved_bar_direction
from mgc_bt.backtest.strategy_primitives import volume_pass
from mgc_bt.backtest.state import ArmedAuditSnapshot
from mgc_bt.backtest.state import BarSnapshot
from mgc_bt.backtest.state import OpenTradeSnapshot
from mgc_bt.backtest.state import PendingInsideBar
from mgc_bt.backtest.state import PendingTradeContext
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
    max_drawdown_pct: float
    audit_log_path: str | None = None
    trade_metadata_path: str | None = None


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
            max_drawdown_pct=config.max_drawdown_pct,
        )
        self._bar_index = 0
        self._recent_bars: deque[BarSnapshot] = deque(maxlen=PINBAR_LOOKBACK + 3)
        self.delta_accumulator = DeltaAccumulator()
        self._bar_deltas = self.delta_accumulator.bar_deltas
        self.absorption_detector = AbsorptionDetector(
            volume_multiplier=config.absorption_volume_multiplier,
            range_multiplier=config.absorption_range_multiplier,
        )
        self._audit_writer: AuditLogWriter | None = None
        self._trade_metadata_path = Path(config.trade_metadata_path) if config.trade_metadata_path else None

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

    def start(self) -> None:
        if self.config.audit_log_path:
            self._audit_writer = AuditLogWriter(Path(self.config.audit_log_path))
            self._audit_writer.open()

    def stop(self) -> None:
        if self._audit_writer is not None:
            self._audit_writer.close()
            self._audit_writer = None

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.delta_accumulator.on_trade_tick(tick)

    def on_bar(self, bar: Bar, account_equity: float | None = None) -> StrategyDecision:
        snapshot = self._to_snapshot(bar)
        if account_equity is not None:
            self.risk._sync_session(snapshot.ts_event_ns, account_equity)
        delta_value = self.delta_accumulator.consume_completed_bar(snapshot.ts_event_ns)

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

        self._record_armed_audit(
            snapshot=snapshot,
            trend_direction=trend_direction,
            delta_value=delta_value,
            prior_volume_avg=prior_volume_avg,
            candle_confirmation=candle_confirmation,
            decision=decision,
        )

        if self.state.open_trade_snapshot is not None:
            self.state.open_trade_snapshot.update_excursions(snapshot.close)

        self._update_inside_bar_state(snapshot)
        self._recent_bars.append(snapshot)
        self._bar_index += 1
        return decision

    def on_position_opened(self, event: PositionOpened | PositionSide, avg_px_open: float | None = None) -> None:
        self.state.position_open = True
        self.state.entry_pending = False
        self.state.exit_pending = False
        self.state.phase = StrategyPhase.IN_TRADE
        if isinstance(event, PositionOpened):
            side = event.side
            avg_open = float(event.avg_px_open)
        else:
            side = event
            avg_open = float(avg_px_open or 0.0)
        if side == PositionSide.LONG:
            self.state.position_direction = TradeDirection.LONG
        elif side == PositionSide.SHORT:
            self.state.position_direction = TradeDirection.SHORT
        self.state.highest_close_since_entry = avg_open
        self.state.lowest_close_since_entry = avg_open
        self.state.current_trailing_stop = None
        pending_context = self.state.pending_trade_context
        if pending_context is not None:
            self.state.open_trade_snapshot = OpenTradeSnapshot(
                entry_timestamp=pending_context.timestamp,
                entry_timestamp_ns=pending_context.timestamp_ns,
                direction=pending_context.direction,
                entry_price=avg_open,
                entry_bar_index=pending_context.bar_index,
                volatility_cluster=pending_context.volatility_cluster,
                session=pending_context.session,
                peak_close=avg_open,
                trough_close=avg_open,
            )
        self.state.pending_trade_context = None

    def on_position_closed(self, event: PositionClosed) -> None:
        open_trade_snapshot = self.state.open_trade_snapshot
        if open_trade_snapshot is not None:
            trade_row = open_trade_snapshot.to_metadata(
                instrument_id=str(event.instrument_id),
                exit_timestamp=timestamp_from_ns(int(event.ts_closed)),
                exit_timestamp_ns=int(event.ts_closed),
                exit_price=float(event.avg_px_close),
                realized_pnl=float(event.realized_pnl.as_double()),
                bars_held=max(self._bar_index - open_trade_snapshot.entry_bar_index, 0),
            )
            if self._audit_writer is not None:
                self._audit_writer.write_trade(trade_row)
            if self._trade_metadata_path is not None:
                append_trade_metadata(self._trade_metadata_path, trade_row)
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
        if self._recent_bars:
            latest = self._recent_bars[-1]
            self.state.pending_trade_context = PendingTradeContext(
                timestamp=timestamp_from_ns(latest.ts_event_ns),
                timestamp_ns=latest.ts_event_ns,
                direction=direction,
                volatility_cluster=getattr(self.supertrend, "selected_cluster", None),
                session=classify_session(datetime_from_ns(latest.ts_event_ns)),
                bar_index=latest.index,
            )

    def exit_submitted(self, reason: str | None = None) -> None:
        self.state.exit_pending = True
        if self.state.open_trade_snapshot is not None:
            self.state.open_trade_snapshot.exit_reason = reason

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
            return StrategyDecision(reason="trend_gate_failed")

        if not self._pullback_qualified(trend_direction, snapshot.index):
            self.state.phase = StrategyPhase.FLAT
            self.state.armed_direction = None
            return StrategyDecision(reason="pullback_not_ready")

        self.state.phase = StrategyPhase.PULLBACK_ARMED
        self.state.armed_direction = trend_direction
        if not self._core_triggers_met(snapshot, trend_direction, delta_value, prior_volume_avg):
            return StrategyDecision(reason="core_triggers_failed")

        if not self._has_optional_confirmation(
            snapshot=snapshot,
            direction=trend_direction,
            prior_volume_avg=prior_volume_avg,
            prior_range_avg=prior_range_avg,
            candle_confirmation=candle_confirmation,
        ):
            return StrategyDecision(reason="optional_confirmation_missing")

        if account_equity is not None and atr_value is not None:
            stop_distance = atr_value * self.config.atr_trail_multiplier
            if not self.risk.can_enter(trend_direction, stop_distance, account_equity):
                return StrategyDecision(reason="risk_gate_blocked")

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

    def _record_armed_audit(
        self,
        *,
        snapshot: BarSnapshot,
        trend_direction: TradeDirection | None,
        delta_value: float,
        prior_volume_avg: float | None,
        candle_confirmation: CandleConfirmation,
        decision: StrategyDecision,
    ) -> None:
        if self._audit_writer is None or self.state.phase != StrategyPhase.PULLBACK_ARMED or trend_direction is None:
            return
        volume_avg = prior_volume_avg
        volume_gate_pass = volume_pass(volume=snapshot.volume, prior_volume_avg=volume_avg)
        delta_threshold = self.config.delta_imbalance_threshold * snapshot.volume if snapshot.volume > 0 else 0.0
        delta_gate_pass = self._delta_pass(snapshot, trend_direction, delta_value)
        absorption_detected = self._absorption_confirmed(
            snapshot,
            trend_direction,
            prior_volume_avg,
            self.range_mean.value,
        )
        optional_confirmation_count = self._optional_confirmation_count(
            snapshot,
            trend_direction,
            prior_volume_avg,
            self.range_mean.value,
            candle_confirmation,
        )
        vwap_value = self.vwap.value
        price_vs_vwap = "above" if vwap_value is not None and snapshot.close > vwap_value else "below" if vwap_value is not None and snapshot.close < vwap_value else "at"
        audit_snapshot = ArmedAuditSnapshot(
            timestamp=timestamp_from_ns(snapshot.ts_event_ns),
            instrument_id=str(self.config.instrument_id),
            open=snapshot.open,
            high=snapshot.high,
            low=snapshot.low,
            close=snapshot.close,
            volume=snapshot.volume,
            supertrend_direction=self.supertrend.direction,
            supertrend_value=self.supertrend.value,
            volatility_cluster=getattr(self.supertrend, "selected_cluster", None),
            vwap_value=vwap_value,
            price_vs_vwap=price_vs_vwap,
            wavetrend_zscore=self.wavetrend.zscore,
            wavetrend_divergence_detected=bool(
                self.wavetrend.bullish_divergence if trend_direction == TradeDirection.LONG else self.wavetrend.bearish_divergence,
            ),
            delta_value=delta_value,
            delta_threshold=delta_threshold,
            delta_pass=delta_gate_pass,
            volume_avg=volume_avg,
            volume_pass=volume_gate_pass,
            absorption_detected=absorption_detected,
            candle_formation=candle_confirmation.value,
            optional_confirmation_count=optional_confirmation_count,
            entry_fired=decision.enter_direction is not None,
            entry_rejected_reason=None if decision.enter_direction is not None else decision.reason,
        )
        self._audit_writer.write_armed_bar(audit_snapshot)

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
        if not volume_pass(volume=snapshot.volume, prior_volume_avg=prior_volume_avg):
            return False
        return self._delta_pass(snapshot, direction, delta_value)

    def _delta_pass(self, snapshot: BarSnapshot, direction: TradeDirection, delta_value: float) -> bool:
        return delta_pass(
            snapshot=snapshot,
            direction=direction,
            delta_value=delta_value,
            threshold_fraction=self.config.delta_imbalance_threshold,
        )

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

    def _optional_confirmation_count(
        self,
        snapshot: BarSnapshot,
        direction: TradeDirection,
        prior_volume_avg: float | None,
        prior_range_avg: float | None,
        candle_confirmation: CandleConfirmation,
    ) -> int:
        count = 0
        if self._absorption_confirmed(snapshot, direction, prior_volume_avg, prior_range_avg):
            count += 1
        if candle_confirmation is not CandleConfirmation.NONE:
            count += 1
        if self._wavetrend_confirmed(direction):
            count += 1
        return count

    def _absorption_confirmed(
        self,
        snapshot: BarSnapshot,
        direction: TradeDirection,
        prior_volume_avg: float | None,
        prior_range_avg: float | None,
    ) -> bool:
        return self.absorption_detector.confirmed(
            snapshot=snapshot,
            direction=direction,
            prior_volume_avg=prior_volume_avg,
            prior_range_avg=prior_range_avg,
        )

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
        return pin_bar_direction(snapshot, list(self._recent_bars), PINBAR_LOOKBACK)

    def _shaved_bar(self, snapshot: BarSnapshot) -> TradeDirection | None:
        return shaved_bar_direction(snapshot)

    def _inside_bar_breakout(self, snapshot: BarSnapshot) -> TradeDirection | None:
        return inside_bar_breakout_direction(snapshot, self.state.pending_inside_bar)

    def _update_inside_bar_state(self, snapshot: BarSnapshot) -> None:
        if self._recent_bars:
            previous = self._recent_bars[-1]
            if snapshot.high < previous.high and snapshot.low > previous.low:
                self.state.pending_inside_bar = PendingInsideBar(high=snapshot.high, low=snapshot.low, index=snapshot.index)
                return
        self.state.pending_inside_bar = None

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


class MgcProductionStrategy(BaseResearchStrategy):
    def __init__(self, config: MgcStrategyConfig):
        super().__init__(config, MgcSignalEngine(config))


def datetime_from_ns(value: int):
    return datetime.fromtimestamp(value / 1_000_000_000, tz=UTC)
