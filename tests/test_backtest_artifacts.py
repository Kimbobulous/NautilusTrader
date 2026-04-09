from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from mgc_bt.backtest.artifacts import write_backtest_artifacts
from mgc_bt.config import load_settings


def test_write_backtest_artifacts_creates_canonical_and_latest_outputs(tmp_path: Path) -> None:
    settings = load_settings("configs/settings.toml")
    settings = replace(settings, paths=replace(settings.paths, results_root=tmp_path))
    result = _sample_result()

    artifact_paths = write_backtest_artifacts(settings, result)

    assert artifact_paths["summary_path"].exists()
    assert artifact_paths["trades_path"].exists()
    assert artifact_paths["config_path"].exists()
    assert artifact_paths["plot_path"].exists()
    assert artifact_paths["manifest_path"].exists()
    assert artifact_paths["latest_dir"].exists()
    assert (artifact_paths["latest_dir"] / "summary.json").exists()
    assert (artifact_paths["latest_dir"] / "equity_curve.png").exists()
    assert (artifact_paths["latest_dir"] / "manifest.json").exists()
    assert (artifact_paths["run_dir"] / "analytics" / "audit_log.csv").exists()
    assert (artifact_paths["run_dir"] / "analytics" / "drawdown_episodes.csv").exists()
    assert (artifact_paths["run_dir"] / "analytics" / "underwater_curve.csv").exists()
    assert (artifact_paths["run_dir"] / "analytics" / "breakdowns" / "by_session.csv").exists()

    summary_payload = json.loads(artifact_paths["summary_path"].read_text(encoding="utf-8"))
    assert summary_payload["instrument_id"] == "MGCJ1.GLBX"
    assert summary_payload["total_pnl"] == 12.5
    assert summary_payload["win_rate"] == 50.0
    assert summary_payload["max_drawdown"] == 3.5
    assert summary_payload["max_drawdown_dollars"] == 3.5
    assert summary_payload["parameters"]["trade_size"] == "1"
    assert summary_payload["parameters"]["max_daily_trades"] == 10

    run_config_text = artifact_paths["config_path"].read_text(encoding="utf-8")
    assert 'native_max_order_submit_rate = "100/00:00:01"' in run_config_text
    assert 'instrument_id = "MGCJ1.GLBX"' in run_config_text
    assert 'roll_source = "explicit"' in run_config_text
    assert "max_drawdown_pct = 5.0" in run_config_text

    manifest_payload = json.loads(artifact_paths["manifest_path"].read_text(encoding="utf-8"))
    assert "summary.json" in manifest_payload["files"]
    assert "trades.csv" in manifest_payload["files"]
    assert "analytics/audit_log.csv" in manifest_payload["files"]
    assert manifest_payload["latest_refreshed"] is True


def test_write_backtest_artifacts_can_leave_latest_untouched(tmp_path: Path) -> None:
    settings = load_settings("configs/settings.toml")
    settings = replace(settings, paths=replace(settings.paths, results_root=tmp_path))
    result = _sample_result()

    artifact_paths = write_backtest_artifacts(settings, result, refresh_latest=False)

    assert artifact_paths["latest_dir"] is None
    assert not (tmp_path / settings.backtest.results_subdir / "latest").exists()
    manifest_payload = json.loads(artifact_paths["manifest_path"].read_text(encoding="utf-8"))
    assert manifest_payload["latest_refreshed"] is False


def test_write_backtest_artifacts_warns_and_keeps_core_bundle_when_analytics_fail(tmp_path: Path, monkeypatch, capsys) -> None:
    settings = load_settings("configs/settings.toml")
    settings = replace(settings, paths=replace(settings.paths, results_root=tmp_path))
    result = _sample_result()

    monkeypatch.setattr(
        "mgc_bt.backtest.artifacts.write_backtest_analytics",
        lambda result, run_dir: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    artifact_paths = write_backtest_artifacts(settings, result)

    assert artifact_paths["summary_path"].exists()
    assert artifact_paths["trades_path"].exists()
    assert artifact_paths["config_path"].exists()
    assert artifact_paths["plot_path"].exists()
    assert artifact_paths["manifest_path"].exists()
    stderr = capsys.readouterr().err
    assert "Warning: analytics generation failed for backtest run" in stderr


def _sample_result() -> dict[str, object]:
    return {
        "mode": "single_contract",
        "instrument_id": "MGCJ1.GLBX",
        "segment_instruments": ["MGCJ1.GLBX"],
        "segment_count": 1,
        "start_date": "2021-03-08T00:00:00+00:00",
        "end_date": "2021-03-08T00:59:00+00:00",
        "total_pnl": 12.5,
        "sharpe_ratio": 1.23,
        "win_rate": 50.0,
        "max_drawdown": 3.5,
        "max_drawdown_pct": 0.01,
        "total_trades": 2,
        "parameters": {
            "instrument_id": "MGCJ1.GLBX",
            "start_date": "2021-03-08T00:00:00+00:00",
            "end_date": "2021-03-08T00:59:00+00:00",
            "trade_size": "1",
            "roll_source": "explicit",
            "max_loss_per_trade_dollars": 150.0,
            "max_daily_trades": 10,
            "max_daily_loss_dollars": 300.0,
            "max_consecutive_losses": 4,
            "max_drawdown_pct": 5.0,
        },
        "segments": [
            {
                "instrument_id": "MGCJ1.GLBX",
                "start_date": "2021-03-08T00:00:00+00:00",
                "end_date": "2021-03-08T00:59:00+00:00",
                "total_pnl": 12.5,
                "total_trades": 2,
                "roll_reason": "explicit",
            },
        ],
        "trade_log": [
            {
                "instrument_id": "MGCJ1.GLBX",
                "entry_side": "BUY",
                "quantity": 1.0,
                "opened_at": "2021-03-08T00:10:00+00:00",
                "closed_at": "2021-03-08T00:20:00+00:00",
                "avg_px_open": 1700.0,
                "avg_px_close": 1701.0,
                "realized_pnl": 10.0,
                "realized_return": 0.001,
                "commissions": 1.0,
                "position_id": "POS-1",
                "slippage": 0.1,
            },
            {
                "instrument_id": "MGCJ1.GLBX",
                "entry_side": "SELL",
                "quantity": 1.0,
                "opened_at": "2021-03-08T00:30:00+00:00",
                "closed_at": "2021-03-08T00:40:00+00:00",
                "avg_px_open": 1702.0,
                "avg_px_close": 1701.5,
                "realized_pnl": 2.5,
                "realized_return": 0.0005,
                "commissions": 1.0,
                "position_id": "POS-2",
                "slippage": 0.1,
            },
        ],
        "analytics_trade_log": [
            {
                "instrument_id": "MGCJ1.GLBX",
                "entry_timestamp": "2021-03-08T00:10:00+00:00",
                "exit_timestamp": "2021-03-08T00:20:00+00:00",
                "entry_price": 1700.0,
                "exit_price": 1701.0,
                "direction": "long",
                "pnl": 10.0,
                "pnl_dollars": 10.0,
                "exit_reason": "atr_stop_long",
                "max_favorable_excursion": 1.5,
                "max_adverse_excursion": 0.4,
                "bars_held": 10,
                "volatility_cluster_at_entry": 2,
                "session_at_entry": "rth",
                "realized_pnl": 10.0,
                "opened_at": "2021-03-08T00:10:00+00:00",
            },
            {
                "instrument_id": "MGCJ1.GLBX",
                "entry_timestamp": "2021-03-08T00:30:00+00:00",
                "exit_timestamp": "2021-03-08T00:40:00+00:00",
                "entry_price": 1702.0,
                "exit_price": 1701.5,
                "direction": "short",
                "pnl": 2.5,
                "pnl_dollars": 2.5,
                "exit_reason": "hard_flip_short",
                "max_favorable_excursion": 0.7,
                "max_adverse_excursion": 0.2,
                "bars_held": 10,
                "volatility_cluster_at_entry": 3,
                "session_at_entry": "london",
                "realized_pnl": 2.5,
                "opened_at": "2021-03-08T00:30:00+00:00",
            },
        ],
        "equity_curve": [
            {"timestamp": "2021-03-08T00:00:00+00:00", "equity": 50000.0},
            {"timestamp": "2021-03-08T00:10:00+00:00", "equity": 50002.5},
            {"timestamp": "2021-03-08T00:20:00+00:00", "equity": 50012.5},
        ],
    }
