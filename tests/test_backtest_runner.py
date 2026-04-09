from __future__ import annotations

from typing import Any

from mgc_bt.backtest.runner import run_backtest
from mgc_bt.cli import main
from mgc_bt.config import load_settings


def test_run_backtest_returns_structured_summary() -> None:
    settings = load_settings("configs/settings.toml")

    result = run_backtest(
        settings,
        {
            "instrument_id": "MGCJ1.GLBX",
            "start_date": "2021-03-08T00:00:00+00:00",
            "end_date": "2021-03-08T06:00:00+00:00",
        },
    )

    assert result["mode"] == "single_contract"
    assert result["instrument_id"] == "MGCJ1.GLBX"
    assert result["total_trades"] >= 0
    assert "total_pnl" in result
    assert "sharpe_ratio" in result
    assert "win_rate" in result
    assert "max_drawdown" in result
    assert isinstance(result["trade_log"], list)
    assert isinstance(result["equity_curve"], list)
    assert result["parameters"]["instrument_id"] == "MGCJ1.GLBX"
    assert result["parameters"]["supertrend_atr_length"] == settings.backtest.supertrend_atr_length
    assert result["parameters"]["max_daily_trades"] == settings.risk.max_daily_trades
    assert result["start_date"] == "2021-03-08T00:00:00+00:00"
    assert result["end_date"] == "2021-03-08T06:00:00+00:00"


def test_cli_backtest_uses_shared_runner(monkeypatch, capsys) -> None:
    captured_params: dict[str, Any] = {}

    def fake_run_backtest(settings, params):
        captured_params.update(params)
        return {
            "mode": "single_contract",
            "instrument_id": "MGCM4.GLBX",
            "start_date": "2024-01-01T00:00:00+00:00",
            "end_date": "2024-01-02T00:00:00+00:00",
            "total_pnl": 12.5,
            "sharpe_ratio": 1.2,
            "win_rate": 50.0,
            "max_drawdown": 2.0,
            "total_trades": 4,
        }

    def fake_write_backtest_artifacts(settings, result, refresh_latest=True):
        return {
            "run_dir": "results/backtests/2026-04-08_120000",
            "latest_dir": "results/backtests/latest",
        }

    monkeypatch.setattr("mgc_bt.backtest.runner.run_backtest", fake_run_backtest)
    monkeypatch.setattr("mgc_bt.backtest.artifacts.write_backtest_artifacts", fake_write_backtest_artifacts)

    exit_code = main(
        [
            "backtest",
            "--instrument-id",
            "MGCM4.GLBX",
            "--start-date",
            "2024-01-01T00:00:00+00:00",
            "--end-date",
            "2024-01-02T00:00:00+00:00",
        ],
    )

    stdout = capsys.readouterr().out
    assert exit_code == 0
    assert captured_params["instrument_id"] == "MGCM4.GLBX"
    assert "Mode: single_contract" in stdout
    assert "Instrument: MGCM4.GLBX" in stdout
    assert "Run directory: results/backtests/2026-04-08_120000" in stdout
