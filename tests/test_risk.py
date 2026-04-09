from __future__ import annotations

from types import SimpleNamespace

from mgc_bt.backtest.risk import RiskManager
from mgc_bt.backtest.state import TradeDirection


def test_can_enter_rejects_when_stop_risk_exceeds_limit() -> None:
    risk = _risk(max_loss_per_trade_dollars=50.0)
    risk._sync_session(_ts(0), 50_000.0)

    allowed = risk.can_enter(TradeDirection.LONG, stop_distance=6.0, account_equity=50_000.0)

    assert not allowed


def test_can_enter_rejects_when_daily_trade_limit_is_reached() -> None:
    risk = _risk(max_daily_trades=1)
    risk._sync_session(_ts(0), 50_000.0)
    assert risk.can_enter(TradeDirection.LONG, stop_distance=2.0, account_equity=50_000.0)
    risk._position_open = False

    allowed = risk.can_enter(TradeDirection.LONG, stop_distance=2.0, account_equity=50_100.0)

    assert not allowed


def test_can_enter_rejects_when_daily_loss_limit_is_breached() -> None:
    risk = _risk(max_daily_loss_dollars=300.0)
    risk._sync_session(_ts(0), 50_000.0)
    risk._sync_session(_ts(1), 49_650.0)

    allowed = risk.can_enter(TradeDirection.LONG, stop_distance=2.0, account_equity=49_650.0)

    assert not allowed


def test_can_enter_rejects_when_consecutive_losses_limit_is_hit() -> None:
    risk = _risk(max_consecutive_losses=2)
    risk._sync_session(_ts(0), 50_000.0)

    assert risk.can_enter(TradeDirection.LONG, stop_distance=2.0, account_equity=50_000.0)
    risk._finalize_closed_trade(49_900.0)
    assert risk.can_enter(TradeDirection.LONG, stop_distance=2.0, account_equity=49_900.0)
    risk._finalize_closed_trade(49_800.0)

    allowed = risk.can_enter(TradeDirection.LONG, stop_distance=2.0, account_equity=49_800.0)

    assert not allowed


def test_can_enter_rejects_when_account_equity_is_too_low() -> None:
    risk = _risk(min_account_equity=49_500.0)
    risk._sync_session(_ts(0), 49_000.0)

    allowed = risk.can_enter(TradeDirection.LONG, stop_distance=2.0, account_equity=49_000.0)

    assert not allowed


def test_should_exit_halts_trading_when_drawdown_limit_is_breached() -> None:
    risk = _risk(max_drawdown_pct=5.0)
    risk._sync_session(_ts(0), 50_000.0)

    should_exit = risk.should_exit(None, _bar(1), 47_000.0)

    assert should_exit
    assert risk.trading_halted_for_session


def test_should_exit_halts_trading_when_daily_loss_limit_is_breached_mid_trade() -> None:
    risk = _risk(max_daily_loss_dollars=300.0, max_drawdown_pct=50.0)
    risk._sync_session(_ts(0), 50_000.0)

    should_exit = risk.should_exit(None, _bar(1), 49_600.0)

    assert should_exit
    assert risk.trading_halted_for_session


def test_daily_reset_occurs_at_midnight_utc() -> None:
    risk = _risk()
    risk._sync_session(_ts(0), 50_000.0)
    risk.can_enter(TradeDirection.LONG, stop_distance=2.0, account_equity=50_000.0)
    risk._finalize_closed_trade(49_950.0)
    risk.trading_halted_for_session = True

    risk._sync_session(_ts(24 * 60), 49_950.0)

    assert risk.daily_trade_count == 0
    assert risk.daily_pnl == 0.0
    assert not risk.trading_halted_for_session
    assert risk.session_start_equity == 49_950.0


def _risk(**overrides) -> RiskManager:
    values = {
        "max_loss_per_trade_dollars": 150.0,
        "max_daily_trades": 10,
        "max_daily_loss_dollars": 300.0,
        "max_consecutive_losses": 4,
        "min_account_equity": 10_000.0,
        "max_drawdown_pct": 5.0,
    }
    values.update(overrides)
    return RiskManager(**values)


def _bar(minutes_from_start: int) -> SimpleNamespace:
    return SimpleNamespace(ts_event_ns=_ts(minutes_from_start))


def _ts(minutes_from_start: int) -> int:
    base_ns = 1_700_000_000_000_000_000
    return base_ns + (minutes_from_start * 60_000_000_000)
