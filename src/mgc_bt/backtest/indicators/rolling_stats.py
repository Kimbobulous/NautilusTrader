from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
import math

from mgc_bt.backtest.state import ConfirmedPivot


class RollingMeanIndicator:
    def __init__(self, length: int) -> None:
        if length <= 0:
            raise ValueError("Rolling mean length must be positive.")
        self.length = length
        self._values: deque[float] = deque()
        self._sum = 0.0

    def update(self, value: float) -> float | None:
        numeric = float(value)
        self._values.append(numeric)
        self._sum += numeric
        if len(self._values) > self.length:
            self._sum -= self._values.popleft()
        return self.value

    @property
    def value(self) -> float | None:
        if len(self._values) < self.length:
            return None
        return self._sum / len(self._values)

    @property
    def is_ready(self) -> bool:
        return len(self._values) >= self.length


class ExponentialMovingAverage:
    def __init__(self, length: int) -> None:
        if length <= 0:
            raise ValueError("EMA length must be positive.")
        self.length = length
        self._multiplier = 2.0 / (length + 1)
        self._value: float | None = None

    def update(self, value: float) -> float:
        numeric = float(value)
        if self._value is None:
            self._value = numeric
        else:
            self._value += (numeric - self._value) * self._multiplier
        return self._value

    @property
    def value(self) -> float | None:
        return self._value

    @property
    def is_ready(self) -> bool:
        return self._value is not None


class WeightedMovingAverage:
    def __init__(self, length: int) -> None:
        if length <= 0:
            raise ValueError("WMA length must be positive.")
        self.length = length
        self._values: deque[float] = deque()
        self._weights = list(range(1, length + 1))
        self._denominator = sum(self._weights)

    def update(self, value: float) -> float | None:
        self._values.append(float(value))
        if len(self._values) > self.length:
            self._values.popleft()
        return self.value

    @property
    def value(self) -> float | None:
        if len(self._values) < self.length:
            return None
        return sum(v * w for v, w in zip(self._values, self._weights, strict=False)) / self._denominator

    @property
    def is_ready(self) -> bool:
        return len(self._values) >= self.length


class HullMovingAverage:
    def __init__(self, length: int) -> None:
        if length <= 1:
            raise ValueError("HMA length must be greater than 1.")
        self.length = length
        self._half_wma = WeightedMovingAverage(max(1, length // 2))
        self._full_wma = WeightedMovingAverage(length)
        self._output_wma = WeightedMovingAverage(max(1, int(math.sqrt(length))))
        self._value: float | None = None

    def update(self, value: float) -> float | None:
        half = self._half_wma.update(value)
        full = self._full_wma.update(value)
        if half is None or full is None:
            self._value = None
            return None
        raw = (2.0 * half) - full
        self._value = self._output_wma.update(raw)
        return self._value

    @property
    def value(self) -> float | None:
        return self._value

    @property
    def is_ready(self) -> bool:
        return self._output_wma.is_ready


@dataclass
class PivotSample:
    index: int
    value: float


class FractalPivotTracker:
    def __init__(self, kind: str, left_span: int = 2, right_span: int = 2) -> None:
        if kind not in {"high", "low"}:
            raise ValueError("FractalPivotTracker kind must be 'high' or 'low'.")
        self.kind = kind
        self.left_span = left_span
        self.right_span = right_span
        self._window: deque[PivotSample] = deque()
        self.last_confirmed: ConfirmedPivot | None = None

    def update(self, index: int, value: float) -> ConfirmedPivot | None:
        self._window.append(PivotSample(index=index, value=float(value)))
        needed = self.left_span + self.right_span + 1
        if len(self._window) < needed:
            return None
        if len(self._window) > needed:
            self._window.popleft()

        center = self._window[self.left_span]
        left = list(self._window)[: self.left_span]
        right = list(self._window)[self.left_span + 1 :]
        if self.kind == "high":
            confirmed = all(center.value > item.value for item in (*left, *right))
        else:
            confirmed = all(center.value < item.value for item in (*left, *right))
        if not confirmed:
            return None

        pivot = ConfirmedPivot(index=center.index, value=center.value)
        self.last_confirmed = pivot
        return pivot


def zscore(values: Iterable[float]) -> float | None:
    values_list = [float(value) for value in values]
    if len(values_list) < 2:
        return None
    mean = sum(values_list) / len(values_list)
    variance = sum((value - mean) ** 2 for value in values_list) / len(values_list)
    if variance <= 0:
        return 0.0
    return (values_list[-1] - mean) / math.sqrt(variance)
