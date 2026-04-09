from __future__ import annotations

from collections import deque

from mgc_bt.backtest.indicators.atr import AtrIndicator
from mgc_bt.backtest.state import BarSnapshot


class AdaptiveSuperTrendIndicator:
    def __init__(self, atr_length: int, factor: float, training_period: int) -> None:
        self.atr_indicator = AtrIndicator(atr_length)
        self.factor = float(factor)
        self.training_period = int(training_period)
        self._atr_history: deque[float] = deque(maxlen=self.training_period)
        self._final_upper: float | None = None
        self._final_lower: float | None = None
        self._supertrend: float | None = None
        self._prev_close: float | None = None
        self._selected_centroid: float | None = None
        self._selected_cluster: int | None = None
        self._direction: int | None = None

    def update(self, bar: BarSnapshot) -> int | None:
        atr_value = self.atr_indicator.update(bar)
        if atr_value is None:
            self._prev_close = bar.close
            return None

        self._atr_history.append(atr_value)
        if len(self._atr_history) < self.training_period:
            self._prev_close = bar.close
            return None

        self._selected_centroid, self._selected_cluster = self._nearest_centroid(atr_value)
        band_distance = self._selected_centroid * self.factor
        hl2 = (bar.high + bar.low) / 2.0
        basic_upper = hl2 + band_distance
        basic_lower = hl2 - band_distance

        if self._final_upper is None or self._prev_close is None:
            self._final_upper = basic_upper
            self._final_lower = basic_lower
        else:
            if basic_upper < self._final_upper or self._prev_close > self._final_upper:
                self._final_upper = basic_upper
            if basic_lower > self._final_lower or self._prev_close < self._final_lower:
                self._final_lower = basic_lower

        if self._supertrend is None:
            self._supertrend = self._final_lower if bar.close >= self._final_lower else self._final_upper
        elif self._supertrend == self._final_upper:
            self._supertrend = self._final_upper if bar.close <= self._final_upper else self._final_lower
        else:
            self._supertrend = self._final_lower if bar.close >= self._final_lower else self._final_upper

        self._direction = -1 if bar.close >= self._supertrend else 1
        self._prev_close = bar.close
        return self._direction

    def _nearest_centroid(self, atr_value: float) -> tuple[float, int]:
        values = list(self._atr_history)
        low = min(values)
        high = max(values)
        mid = sorted(values)[len(values) // 2]
        centroids = [low, mid, high]
        for _ in range(8):
            clusters = {index: [] for index in range(3)}
            for value in values:
                index = min(range(3), key=lambda item: abs(value - centroids[item]))
                clusters[index].append(value)
            next_centroids = []
            for index, centroid in enumerate(centroids):
                bucket = clusters[index]
                next_centroids.append(sum(bucket) / len(bucket) if bucket else centroid)
            if all(abs(a - b) < 1e-9 for a, b in zip(centroids, next_centroids, strict=False)):
                break
            centroids = next_centroids
        nearest_index = min(range(3), key=lambda item: abs(atr_value - centroids[item]))
        return centroids[nearest_index], nearest_index + 1

    @property
    def direction(self) -> int | None:
        return self._direction

    @property
    def value(self) -> float | None:
        return self._supertrend

    @property
    def selected_centroid(self) -> float | None:
        return self._selected_centroid

    @property
    def selected_cluster(self) -> int | None:
        return self._selected_cluster

    @property
    def is_ready(self) -> bool:
        return self._direction is not None
