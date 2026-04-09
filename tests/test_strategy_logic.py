from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from mgc_bt.backtest.state import ConfirmedPivot
from mgc_bt.backtest.state import StrategyPhase
from mgc_bt.backtest.state import TradeDirection
from mgc_bt.backtest.strategy import MIN_READY_BARS
from mgc_bt.backtest.strategy import MgcSignalEngine
from mgc_bt.backtest.strategy import MgcStrategyConfig
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.enums import PositionSide
from nautilus_trader.model.identifiers import InstrumentId


def test_trend_gate_disagreement_keeps_engine_flat() -> None:
    engine = MgcSignalEngine(_strategy_config())
    _prime_ready_state(engine, supertrend_direction=-1, vwap_value=120.0)
    engine.state.last_confirmed_swing_low = ConfirmedPivot(index=190, value=99.0)

    decision = engine.on_bar(_bar(open_=100.0, high=101.0, low=99.5, close=100.5, volume=200.0, index=200))

    assert not decision.has_action
    assert engine.state.phase == StrategyPhase.FLAT


def test_pullback_arms_when_trend_valid_and_rearms_after_reset() -> None:
    engine = MgcSignalEngine(_strategy_config())
    _prime_ready_state(engine, supertrend_direction=-1, vwap_value=99.0)
    engine.state.last_confirmed_swing_low = ConfirmedPivot(index=190, value=98.0)

    first = engine.on_bar(_bar(open_=100.0, high=101.0, low=99.8, close=100.2, volume=110.0, index=200))
    assert not first.has_action
    assert engine.state.phase == StrategyPhase.PULLBACK_ARMED

    engine.supertrend.direction = 1
    engine.vwap.value = 101.0
    engine.on_bar(_bar(open_=100.1, high=100.4, low=99.9, close=100.0, volume=105.0, index=201))
    assert engine.state.phase == StrategyPhase.FLAT

    engine.supertrend.direction = -1
    engine.vwap.value = 99.0
    engine.state.last_confirmed_swing_low = ConfirmedPivot(index=192, value=98.5)
    engine.on_bar(_bar(open_=100.0, high=100.6, low=99.7, close=100.3, volume=111.0, index=202))
    assert engine.state.phase == StrategyPhase.PULLBACK_ARMED


def test_entry_requires_optional_confirmation() -> None:
    engine = MgcSignalEngine(_strategy_config())
    _prime_ready_state(engine, supertrend_direction=-1, vwap_value=99.0)
    engine.state.last_confirmed_swing_low = ConfirmedPivot(index=190, value=98.0)

    for _ in range(60):
        engine.on_trade_tick(_trade_tick(AggressorSide.BUYER, 2.0, _bar_ts(200)))

    no_optional = engine.on_bar(_bar(open_=100.0, high=101.0, low=99.0, close=100.4, volume=110.0, index=200))
    assert not no_optional.has_action

    for _ in range(60):
        engine.on_trade_tick(_trade_tick(AggressorSide.BUYER, 2.0, _bar_ts(201)))

    with_optional = engine.on_bar(_bar(open_=100.0, high=105.0, low=99.5, close=104.9, volume=115.0, index=201))
    assert with_optional.enter_direction == TradeDirection.LONG


def test_delta_uses_buyer_and_seller_enum_names() -> None:
    engine = MgcSignalEngine(_strategy_config())
    _prime_ready_state(engine, supertrend_direction=-1, vwap_value=99.0)
    engine.state.last_confirmed_swing_low = ConfirmedPivot(index=190, value=98.0)

    for _ in range(10):
        engine.on_trade_tick(_trade_tick(AggressorSide.BUYER, 3.0, _bar_ts(200)))
    for _ in range(5):
        engine.on_trade_tick(_trade_tick(AggressorSide.SELLER, 1.0, _bar_ts(200)))

    bar = _bar(open_=100.0, high=104.0, low=99.0, close=103.9, volume=50.0, index=200)
    engine.on_bar(bar)
    bucket = bar.ts_event // 60_000_000_000
    assert engine._bar_deltas[bucket] == 25.0


def test_exit_requires_atr_stop_or_hard_dual_gate_flip() -> None:
    engine = MgcSignalEngine(_strategy_config())
    _prime_ready_state(engine, supertrend_direction=-1, vwap_value=99.0, atr_value=1.0)
    engine.state.position_open = True
    engine.state.phase = StrategyPhase.IN_TRADE
    engine.state.position_direction = TradeDirection.LONG
    engine.state.highest_close_since_entry = 110.0
    engine.state.current_trailing_stop = 108.0

    stay = engine.on_bar(_bar(open_=109.0, high=110.0, low=108.5, close=109.2, volume=120.0, index=200))
    assert not stay.has_action

    engine.supertrend.direction = 1
    engine.vwap.value = 111.0
    flip = engine.on_bar(_bar(open_=109.0, high=109.5, low=108.8, close=109.0, volume=120.0, index=201))
    assert flip.exit_trade


def test_end_to_end_state_machine_sequence() -> None:
    engine = MgcSignalEngine(_strategy_config())
    _prime_ready_state(engine, supertrend_direction=-1, vwap_value=99.0, atr_value=1.0)
    engine.state.last_confirmed_swing_low = ConfirmedPivot(index=190, value=98.0)

    armed = engine.on_bar(_bar(open_=100.0, high=100.5, low=99.7, close=100.2, volume=105.0, index=200))
    assert not armed.has_action
    assert engine.state.phase == StrategyPhase.PULLBACK_ARMED

    for _ in range(60):
        engine.on_trade_tick(_trade_tick(AggressorSide.BUYER, 2.0, _bar_ts(201)))
    entry = engine.on_bar(_bar(open_=100.0, high=105.0, low=99.5, close=104.9, volume=115.0, index=201))
    assert entry.enter_direction == TradeDirection.LONG
    engine.entry_submitted(TradeDirection.LONG)
    engine.on_position_opened(PositionSide.LONG, 104.9)

    hold = engine.on_bar(_bar(open_=104.9, high=106.0, low=104.5, close=105.5, volume=116.0, index=202))
    assert not hold.has_action
    assert engine.state.phase == StrategyPhase.IN_TRADE

    engine.supertrend.direction = 1
    engine.vwap.value = 106.0
    exit_decision = engine.on_bar(_bar(open_=105.4, high=105.6, low=104.8, close=105.0, volume=120.0, index=203))
    assert exit_decision.exit_trade


def _prime_ready_state(
    engine: MgcSignalEngine,
    *,
    supertrend_direction: int,
    vwap_value: float,
    atr_value: float = 1.0,
) -> None:
    engine._bar_index = MIN_READY_BARS
    engine.supertrend = _StubSuperTrend(supertrend_direction)
    engine.vwap = _StubValueIndicator(vwap_value)
    engine.wavetrend = _StubWaveTrend()
    engine.atr_trail = _StubAtr(atr_value)
    engine.volume_mean = _StubMean(100.0)
    engine.range_mean = _StubMean(2.0)
    engine.swing_highs = _StubPivot()
    engine.swing_lows = _StubPivot()


def _strategy_config() -> MgcStrategyConfig:
    return MgcStrategyConfig(
        instrument_id=InstrumentId.from_str("MGCJ1.GLBX"),
        bar_type=BarType.from_str("MGCJ1.GLBX-1-MINUTE-LAST-EXTERNAL"),
        trade_size=Decimal("1"),
        supertrend_atr_length=10,
        supertrend_factor=3.0,
        supertrend_training_period=100,
        vwap_reset_hour_utc=0,
        wavetrend_n1=10,
        wavetrend_n2=21,
        wavetrend_ob_level=2.0,
        delta_imbalance_threshold=0.3,
        absorption_volume_multiplier=1.5,
        absorption_range_multiplier=0.7,
        volume_lookback=20,
        atr_trail_length=14,
        atr_trail_multiplier=2.0,
        min_pullback_bars=3,
    )


def _bar(*, open_: float, high: float, low: float, close: float, volume: float, index: int) -> SimpleNamespace:
    ts_event = _bar_ts(index)
    return SimpleNamespace(
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        ts_event=ts_event,
    )


def _trade_tick(side: AggressorSide, size: float, ts_event: int) -> SimpleNamespace:
    return SimpleNamespace(aggressor_side=side, size=size, ts_event=ts_event)


def _bar_ts(index: int) -> int:
    return 12_000_000_000_000 + (index * 60_000_000_000)


class _StubSuperTrend:
    def __init__(self, direction: int) -> None:
        self.direction = direction

    def update(self, bar) -> int:
        return self.direction

    @property
    def is_ready(self) -> bool:
        return True


class _StubValueIndicator:
    def __init__(self, value: float) -> None:
        self.value = value

    def update(self, bar) -> float:
        return self.value

    @property
    def is_ready(self) -> bool:
        return True


class _StubWaveTrend:
    def __init__(self) -> None:
        self.zscore = 0.0
        self.bullish_divergence = False
        self.bearish_divergence = False

    def update(self, bar) -> None:
        return None

    @property
    def is_ready(self) -> bool:
        return True


class _StubAtr:
    def __init__(self, value: float) -> None:
        self.value = value

    def update(self, bar) -> float:
        return self.value

    @property
    def is_ready(self) -> bool:
        return True


class _StubMean:
    def __init__(self, value: float) -> None:
        self.value = value

    def update(self, current) -> float:
        return self.value

    @property
    def is_ready(self) -> bool:
        return True


class _StubPivot:
    def update(self, index: int, value: float):
        return None
