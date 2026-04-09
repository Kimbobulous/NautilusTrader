from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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
