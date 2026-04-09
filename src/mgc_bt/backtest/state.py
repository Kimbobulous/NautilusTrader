from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class StrategyPhase(str, Enum):
    FLAT = "FLAT"
    PULLBACK_ARMED = "PULLBACK_ARMED"
    IN_TRADE = "IN_TRADE"


class TradeDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True)
class BarSnapshot:
    index: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    ts_event_ns: int

    @property
    def range(self) -> float:
        return max(self.high - self.low, 0.0)

    @property
    def typical_price(self) -> float:
        return (self.high + self.low + self.close) / 3.0

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open


@dataclass(frozen=True)
class ConfirmedPivot:
    index: int
    value: float


@dataclass
class PendingInsideBar:
    high: float
    low: float
    index: int


@dataclass(frozen=True)
class ArmedAuditSnapshot:
    timestamp: str
    instrument_id: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    supertrend_direction: int | None
    supertrend_value: float | None
    volatility_cluster: int | None
    vwap_value: float | None
    price_vs_vwap: str
    wavetrend_zscore: float | None
    wavetrend_divergence_detected: bool
    delta_value: float
    delta_threshold: float
    delta_pass: bool
    volume_avg: float | None
    volume_pass: bool
    absorption_detected: bool
    candle_formation: str
    optional_confirmation_count: int
    entry_fired: bool
    entry_rejected_reason: str | None


@dataclass(frozen=True)
class PendingTradeContext:
    timestamp: str
    timestamp_ns: int
    direction: TradeDirection
    volatility_cluster: int | None
    session: str
    bar_index: int
    signal_reason: str | None = None


@dataclass
class OpenTradeSnapshot:
    entry_timestamp: str
    entry_timestamp_ns: int
    direction: TradeDirection
    entry_price: float
    entry_bar_index: int
    volatility_cluster: int | None
    session: str
    peak_close: float
    trough_close: float
    exit_reason: str | None = None

    def update_excursions(self, close: float) -> None:
        self.peak_close = max(self.peak_close, close)
        self.trough_close = min(self.trough_close, close)

    def to_metadata(
        self,
        *,
        instrument_id: str,
        exit_timestamp: str,
        exit_timestamp_ns: int,
        exit_price: float,
        realized_pnl: float,
        bars_held: int,
    ) -> dict[str, Any]:
        mfe = (self.peak_close - self.entry_price) if self.direction == TradeDirection.LONG else (self.entry_price - self.trough_close)
        mae = (self.entry_price - self.trough_close) if self.direction == TradeDirection.LONG else (self.peak_close - self.entry_price)
        return {
            "instrument_id": instrument_id,
            "entry_timestamp": self.entry_timestamp,
            "exit_timestamp": exit_timestamp,
            "entry_timestamp_ns": self.entry_timestamp_ns,
            "exit_timestamp_ns": exit_timestamp_ns,
            "entry_price": self.entry_price,
            "exit_price": exit_price,
            "direction": self.direction.value.lower(),
            "pnl": realized_pnl,
            "pnl_dollars": realized_pnl,
            "exit_reason": self.exit_reason or "end_of_data",
            "max_favorable_excursion": round(float(mfe), 6),
            "max_adverse_excursion": round(float(mae), 6),
            "bars_held": bars_held,
            "volatility_cluster_at_entry": self.volatility_cluster,
            "session_at_entry": self.session,
        }


@dataclass
class StrategyDecision:
    enter_direction: TradeDirection | None = None
    exit_trade: bool = False
    reason: str | None = None

    @property
    def has_action(self) -> bool:
        return self.enter_direction is not None or self.exit_trade


@dataclass
class StrategyRuntimeState:
    phase: StrategyPhase = StrategyPhase.FLAT
    armed_direction: TradeDirection | None = None
    position_direction: TradeDirection | None = None
    position_open: bool = False
    entry_pending: bool = False
    exit_pending: bool = False
    highest_close_since_entry: float | None = None
    lowest_close_since_entry: float | None = None
    current_trailing_stop: float | None = None
    last_confirmed_swing_high: ConfirmedPivot | None = None
    last_confirmed_swing_low: ConfirmedPivot | None = None
    pending_inside_bar: PendingInsideBar | None = None
    pending_trade_context: PendingTradeContext | None = None
    open_trade_snapshot: OpenTradeSnapshot | None = None
