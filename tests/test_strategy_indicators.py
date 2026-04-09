from __future__ import annotations

from mgc_bt.backtest.indicators import AdaptiveSuperTrendIndicator
from mgc_bt.backtest.indicators import AtrIndicator
from mgc_bt.backtest.indicators import SessionVwapIndicator
from mgc_bt.backtest.indicators import WaveTrendIndicator
from mgc_bt.backtest.strategy import MIN_READY_BARS
from mgc_bt.backtest.strategy import MgcSignalEngine
from mgc_bt.backtest.strategy import MgcStrategyConfig
from mgc_bt.backtest.state import BarSnapshot
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import InstrumentId
from decimal import Decimal


def test_atr_indicator_produces_positive_value_after_warmup() -> None:
    indicator = AtrIndicator(length=3)
    bars = _bars(6)

    for bar in bars:
        indicator.update(bar)

    assert indicator.is_ready
    assert indicator.value is not None
    assert indicator.value > 0


def test_session_vwap_resets_when_utc_session_changes() -> None:
    indicator = SessionVwapIndicator(reset_hour_utc=0)
    first = BarSnapshot(0, 100, 101, 99, 100, 10, 1_609_459_140_000_000_000)  # 2020-12-31 23:59 UTC
    second = BarSnapshot(1, 200, 201, 199, 200, 10, 1_609_459_200_000_000_000)  # 2021-01-01 00:00 UTC

    first_value = indicator.update(first)
    second_value = indicator.update(second)

    assert first_value is not None
    assert second_value is not None
    assert abs(second_value - second.typical_price) < 1e-9


def test_adaptive_supertrend_becomes_ready_after_training_window() -> None:
    indicator = AdaptiveSuperTrendIndicator(atr_length=5, factor=3.0, training_period=10)

    for bar in _bars(40):
        indicator.update(bar)

    assert indicator.is_ready
    assert indicator.direction in {-1, 1}
    assert indicator.selected_centroid is not None


def test_wavetrend_exposes_zscore_after_warmup() -> None:
    indicator = WaveTrendIndicator(n1=5, n2=8, zscore_lookback=10, hma_length=6)

    for bar in _bars(80):
        indicator.update(bar)

    assert indicator.is_ready
    assert indicator.value is not None
    assert indicator.zscore is not None


def test_strategy_engine_is_not_ready_before_minimum_bars() -> None:
    engine = MgcSignalEngine(_strategy_config())
    for bar in _bars(MIN_READY_BARS - 1):
        engine.on_bar(_fake_runtime_bar(bar))

    assert not engine.is_ready


def _strategy_config() -> MgcStrategyConfig:
    return MgcStrategyConfig(
        instrument_id=InstrumentId.from_str("MGCJ1.GLBX"),
        bar_type=BarType.from_str("MGCJ1.GLBX-1-MINUTE-LAST-EXTERNAL"),
        trade_size=Decimal("1"),
        supertrend_atr_length=5,
        supertrend_factor=3.0,
        supertrend_training_period=10,
        vwap_reset_hour_utc=0,
        wavetrend_n1=5,
        wavetrend_n2=8,
        wavetrend_ob_level=2.0,
        delta_imbalance_threshold=0.3,
        absorption_volume_multiplier=1.5,
        absorption_range_multiplier=0.7,
        volume_lookback=5,
        atr_trail_length=5,
        atr_trail_multiplier=2.0,
        min_pullback_bars=3,
    )


def _bars(count: int) -> list[BarSnapshot]:
    bars: list[BarSnapshot] = []
    base_ts = 1_700_000_000_000_000_000
    for index in range(count):
        open_price = 100.0 + (index * 0.15)
        close_price = open_price + (0.2 if index % 3 else -0.05)
        high = max(open_price, close_price) + 0.3
        low = min(open_price, close_price) - 0.25
        bars.append(
            BarSnapshot(
                index=index,
                open=open_price,
                high=high,
                low=low,
                close=close_price,
                volume=100 + index,
                ts_event_ns=base_ts + (index * 60_000_000_000),
            ),
        )
    return bars


class _fake_runtime_bar:
    def __init__(self, snapshot: BarSnapshot) -> None:
        self.open = snapshot.open
        self.high = snapshot.high
        self.low = snapshot.low
        self.close = snapshot.close
        self.volume = snapshot.volume
        self.ts_event = snapshot.ts_event_ns
