from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta

from mgc_bt.backtest.state import BarSnapshot


class SessionVwapIndicator:
    def __init__(self, reset_hour_utc: int) -> None:
        if not 0 <= reset_hour_utc <= 23:
            raise ValueError("VWAP reset hour must be between 0 and 23.")
        self.reset_hour_utc = reset_hour_utc
        self._current_session: tuple[int, int, int] | None = None
        self._cum_volume = 0.0
        self._cum_tpv = 0.0
        self._value: float | None = None

    def update(self, bar: BarSnapshot) -> float | None:
        session_key = self._session_key(bar.ts_event_ns)
        if self._current_session != session_key:
            self._current_session = session_key
            self._cum_volume = 0.0
            self._cum_tpv = 0.0

        self._cum_volume += bar.volume
        self._cum_tpv += bar.typical_price * bar.volume
        if self._cum_volume > 0:
            self._value = self._cum_tpv / self._cum_volume
        return self._value

    def _session_key(self, ts_event_ns: int) -> tuple[int, int, int]:
        dt = datetime.fromtimestamp(ts_event_ns / 1_000_000_000, tz=UTC)
        if dt.hour < self.reset_hour_utc:
            dt = dt - timedelta(days=1)
        adjusted = dt.replace(hour=self.reset_hour_utc, minute=0, second=0, microsecond=0)
        return adjusted.year, adjusted.month, adjusted.day

    @property
    def value(self) -> float | None:
        return self._value

    @property
    def is_ready(self) -> bool:
        return self._value is not None
