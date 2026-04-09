from __future__ import annotations

from collections import deque

from mgc_bt.backtest.indicators.rolling_stats import ExponentialMovingAverage
from mgc_bt.backtest.indicators.rolling_stats import FractalPivotTracker
from mgc_bt.backtest.indicators.rolling_stats import HullMovingAverage
from mgc_bt.backtest.indicators.rolling_stats import zscore
from mgc_bt.backtest.state import BarSnapshot
from mgc_bt.backtest.state import ConfirmedPivot


class WaveTrendIndicator:
    def __init__(self, n1: int, n2: int, zscore_lookback: int = 20, hma_length: int = 12) -> None:
        self._esa = ExponentialMovingAverage(n1)
        self._deviation = ExponentialMovingAverage(n1)
        self._wave = ExponentialMovingAverage(n2)
        self._hma = HullMovingAverage(hma_length)
        self._zscore_values: deque[float] = deque(maxlen=zscore_lookback)
        self._price_highs = FractalPivotTracker("high")
        self._price_lows = FractalPivotTracker("low")
        self._wave_highs = FractalPivotTracker("high")
        self._wave_lows = FractalPivotTracker("low")
        self._price_high_history: list[ConfirmedPivot] = []
        self._price_low_history: list[ConfirmedPivot] = []
        self._wave_high_history: list[ConfirmedPivot] = []
        self._wave_low_history: list[ConfirmedPivot] = []
        self._wt1: float | None = None
        self._wt2: float | None = None
        self._zscore: float | None = None
        self._bullish_divergence = False
        self._bearish_divergence = False

    def update(self, bar: BarSnapshot) -> None:
        price = bar.typical_price
        esa = self._esa.update(price)
        deviation = self._deviation.update(abs(price - esa))
        ci = (price - esa) / (0.015 * deviation) if deviation not in (None, 0.0) else 0.0
        self._wt1 = self._wave.update(ci)
        if self._wt1 is not None:
            self._wt2 = self._hma.update(self._wt1)
            self._zscore_values.append(self._wt1)
            self._zscore = zscore(self._zscore_values)

        self._bullish_divergence = False
        self._bearish_divergence = False
        self._track_price_pivots(bar)
        self._track_wave_pivots(bar)
        self._update_divergence_flags()

    def _track_price_pivots(self, bar: BarSnapshot) -> None:
        high_pivot = self._price_highs.update(bar.index, bar.high)
        if high_pivot is not None:
            self._price_high_history.append(high_pivot)
            self._price_high_history = self._price_high_history[-2:]
        low_pivot = self._price_lows.update(bar.index, bar.low)
        if low_pivot is not None:
            self._price_low_history.append(low_pivot)
            self._price_low_history = self._price_low_history[-2:]

    def _track_wave_pivots(self, bar: BarSnapshot) -> None:
        if self._wt2 is None:
            return
        high_pivot = self._wave_highs.update(bar.index, self._wt2)
        if high_pivot is not None:
            self._wave_high_history.append(high_pivot)
            self._wave_high_history = self._wave_high_history[-2:]
        low_pivot = self._wave_lows.update(bar.index, self._wt2)
        if low_pivot is not None:
            self._wave_low_history.append(low_pivot)
            self._wave_low_history = self._wave_low_history[-2:]

    def _update_divergence_flags(self) -> None:
        if len(self._price_low_history) >= 2 and len(self._wave_low_history) >= 2:
            price_prev, price_curr = self._price_low_history[-2:]
            wave_prev, wave_curr = self._wave_low_history[-2:]
            if price_curr.value < price_prev.value and wave_curr.value > wave_prev.value:
                self._bullish_divergence = True
        if len(self._price_high_history) >= 2 and len(self._wave_high_history) >= 2:
            price_prev, price_curr = self._price_high_history[-2:]
            wave_prev, wave_curr = self._wave_high_history[-2:]
            if price_curr.value > price_prev.value and wave_curr.value < wave_prev.value:
                self._bearish_divergence = True

    @property
    def value(self) -> float | None:
        return self._wt2

    @property
    def zscore(self) -> float | None:
        return self._zscore

    @property
    def bullish_divergence(self) -> bool:
        return self._bullish_divergence

    @property
    def bearish_divergence(self) -> bool:
        return self._bearish_divergence

    @property
    def is_ready(self) -> bool:
        return self._wt2 is not None and self._zscore is not None
