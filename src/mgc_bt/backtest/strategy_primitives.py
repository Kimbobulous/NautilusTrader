from __future__ import annotations

from collections import defaultdict

from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AggressorSide

from mgc_bt.backtest.state import BarSnapshot
from mgc_bt.backtest.state import PendingInsideBar
from mgc_bt.backtest.state import TradeDirection


class DeltaAccumulator:
    def __init__(self) -> None:
        self._trade_buckets: dict[int, dict[str, float]] = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})
        self.bar_deltas: dict[int, float] = {}

    def on_trade_tick(self, tick: TradeTick) -> None:
        bucket = minute_bucket(int(tick.ts_event))
        size = float(tick.size)
        if tick.aggressor_side == AggressorSide.BUYER:
            self._trade_buckets[bucket]["buy"] += size
        elif tick.aggressor_side == AggressorSide.SELLER:
            self._trade_buckets[bucket]["sell"] += size

    def consume_completed_bar(self, ts_event_ns: int) -> float:
        current_bucket = minute_bucket(ts_event_ns)
        completed_bucket = current_bucket - 1
        bucket_data = self._trade_buckets.pop(completed_bucket, {"buy": 0.0, "sell": 0.0})
        delta_value = bucket_data["buy"] - bucket_data["sell"]
        self.bar_deltas[completed_bucket] = delta_value
        return delta_value


def minute_bucket(ts_event_ns: int) -> int:
    return ts_event_ns // 60_000_000_000


def volume_pass(*, volume: float, prior_volume_avg: float | None) -> bool:
    return prior_volume_avg is not None and volume > prior_volume_avg


def delta_pass(
    *,
    snapshot: BarSnapshot,
    direction: TradeDirection,
    delta_value: float,
    threshold_fraction: float,
) -> bool:
    if snapshot.volume <= 0:
        return False
    if abs(delta_value) < (threshold_fraction * snapshot.volume):
        return False
    if direction == TradeDirection.LONG:
        return delta_value > 0 and snapshot.is_bullish
    return delta_value < 0 and snapshot.is_bearish


class AbsorptionDetector:
    def __init__(self, *, volume_multiplier: float, range_multiplier: float) -> None:
        self.volume_multiplier = volume_multiplier
        self.range_multiplier = range_multiplier

    def confirmed(
        self,
        *,
        snapshot: BarSnapshot,
        direction: TradeDirection,
        prior_volume_avg: float | None,
        prior_range_avg: float | None,
    ) -> bool:
        if prior_volume_avg is None or prior_range_avg is None or snapshot.range <= 0:
            return False
        if snapshot.volume <= (prior_volume_avg * self.volume_multiplier):
            return False
        if snapshot.range >= (prior_range_avg * self.range_multiplier):
            return False
        close_location = (snapshot.close - snapshot.low) / snapshot.range
        if direction == TradeDirection.LONG:
            return close_location >= 0.6
        return close_location <= 0.4


def pin_bar_direction(snapshot: BarSnapshot, recent_bars: list[BarSnapshot], lookback: int) -> TradeDirection | None:
    if snapshot.range <= 0 or len(recent_bars) < lookback:
        return None
    lower_wick = min(snapshot.open, snapshot.close) - snapshot.low
    upper_wick = snapshot.high - max(snapshot.open, snapshot.close)
    close_location = (snapshot.close - snapshot.low) / snapshot.range
    prior_lows = [bar.low for bar in recent_bars[-lookback:]]
    prior_highs = [bar.high for bar in recent_bars[-lookback:]]
    if lower_wick >= (0.66 * snapshot.range) and close_location >= 0.66 and snapshot.low < min(prior_lows):
        return TradeDirection.LONG
    if upper_wick >= (0.66 * snapshot.range) and close_location <= 0.34 and snapshot.high > max(prior_highs):
        return TradeDirection.SHORT
    return None


def shaved_bar_direction(snapshot: BarSnapshot) -> TradeDirection | None:
    if snapshot.range <= 0:
        return None
    close_location = (snapshot.close - snapshot.low) / snapshot.range
    if close_location >= 0.95:
        return TradeDirection.LONG
    if close_location <= 0.05:
        return TradeDirection.SHORT
    return None


def inside_bar_breakout_direction(
    snapshot: BarSnapshot,
    pending_inside_bar: PendingInsideBar | None,
) -> TradeDirection | None:
    if pending_inside_bar is None:
        return None
    if snapshot.index != pending_inside_bar.index + 1:
        return None
    if snapshot.close > pending_inside_bar.high:
        return TradeDirection.LONG
    if snapshot.close < pending_inside_bar.low:
        return TradeDirection.SHORT
    return None
