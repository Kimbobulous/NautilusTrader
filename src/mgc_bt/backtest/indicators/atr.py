from __future__ import annotations

from collections import deque

from mgc_bt.backtest.state import BarSnapshot


class AtrIndicator:
    def __init__(self, length: int) -> None:
        if length <= 0:
            raise ValueError("ATR length must be positive.")
        self.length = length
        self._tr_values: deque[float] = deque()
        self._atr: float | None = None
        self._prev_close: float | None = None

    def update(self, bar: BarSnapshot) -> float | None:
        if self._prev_close is None:
            true_range = bar.range
        else:
            true_range = max(
                bar.range,
                abs(bar.high - self._prev_close),
                abs(bar.low - self._prev_close),
            )
        self._tr_values.append(true_range)
        if len(self._tr_values) > self.length:
            self._tr_values.popleft()

        if len(self._tr_values) == self.length:
            if self._atr is None:
                self._atr = sum(self._tr_values) / self.length
            else:
                self._atr = ((self._atr * (self.length - 1)) + true_range) / self.length

        self._prev_close = bar.close
        return self._atr

    @property
    def value(self) -> float | None:
        return self._atr

    @property
    def is_ready(self) -> bool:
        return self._atr is not None
