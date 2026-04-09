from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import csv
import json

from mgc_bt.compare import run_comparison
from mgc_bt.config import load_settings
from mgc_bt.reporting.comparison import write_comparison_tearsheet


def test_run_comparison_creates_two_normal_runs_and_summary_folder(tmp_path: Path, monkeypatch) -> None:
    settings = load_settings("configs/settings.toml")
    settings = replace(settings, paths=replace(settings.paths, results_root=tmp_path))

    def fake_run_backtest(settings, params):
        result = _sample_result()
        result["instrument_id"] = params.get("instrument_id") or "MGCJ1.GLBX"
        result["parameters"]["strategy"] = params.get("strategy")
        result["strategy_name"] = params.get("strategy")
        if params.get("strategy") == "phase2_harness":
            result["total_pnl"] = 20.0
            result["sharpe_ratio"] = 2.0
            result["max_drawdown"] = 1.0
            result["trade_log"][0]["realized_pnl"] = 20.0
            result["analytics_trade_log"][0]["realized_pnl"] = 20.0
        return result

    monkeypatch.setattr("mgc_bt.compare.run_backtest", fake_run_backtest)

    result = run_comparison(
        settings,
        strategy_a="mgc_production",
        strategy_b="phase2_harness",
        strategy_class_b="mgc_bt.backtest.strategy_stub:Phase2HarnessStrategy",
        instrument_id="MGCJ1.GLBX",
        start_date="2021-03-08T00:00:00+00:00",
        end_date="2021-03-08T00:59:00+00:00",
    )

    assert Path(result["strategy_a_run_dir"]).exists()
    assert Path(result["strategy_b_run_dir"]).exists()
    assert Path(result["comparison_summary_path"]).exists()
    assert Path(result["metrics_delta_path"]).exists()
    assert Path(result["comparison_tearsheet_path"]).exists()

    summary = json.loads(Path(result["comparison_summary_path"]).read_text(encoding="utf-8"))
    assert summary["strategy_a"]["summary"]["total_pnl"] == 12.5
    assert summary["strategy_b"]["summary"]["total_pnl"] == 20.0

    with Path(result["metrics_delta_path"]).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert any(row["metric"] == "total_pnl" for row in rows)


def test_write_comparison_tearsheet_uses_persisted_run_artifacts(tmp_path: Path) -> None:
    run_a = tmp_path / "backtests" / "a"
    run_b = tmp_path / "backtests" / "b"
    comparison_dir = tmp_path / "comparisons" / "c"
    comparison_dir.mkdir(parents=True)
    _write_minimal_run(run_a, "mgc_production", 10.0)
    _write_minimal_run(run_b, "phase2_harness", 5.0)
    (comparison_dir / "metrics_delta.csv").write_text(
        "metric,strategy_a,strategy_b,delta_b_minus_a\ntotal_pnl,10.0,5.0,-5.0\n",
        encoding="utf-8",
    )

    output_path = write_comparison_tearsheet(
        comparison_dir=comparison_dir,
        strategy_a_run_dir=run_a,
        strategy_b_run_dir=run_b,
        strategy_a_label="mgc_production",
        strategy_b_label="phase2_harness",
    )

    html_text = output_path.read_text(encoding="utf-8")
    assert "Strategy comparison" in html_text
    assert "mgc_production" in html_text
    assert "phase2_harness" in html_text
    assert "cdn.plot.ly" not in html_text


def _write_minimal_run(run_dir: Path, strategy_name: str, total_pnl: float) -> None:
    (run_dir / "analytics" / "breakdowns").mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "strategy_name": strategy_name,
                "instrument_id": "MGCJ1.GLBX",
                "start_date": "2021-03-08T00:00:00+00:00",
                "end_date": "2021-03-08T00:59:00+00:00",
                "total_pnl": total_pnl,
                "sharpe_ratio": 1.0,
                "win_rate": 50.0,
                "max_drawdown_pct": 1.0,
                "max_drawdown": 1.0,
                "total_trades": 1,
            },
        ),
        encoding="utf-8",
    )
    (run_dir / "trades.csv").write_text(
        "opened_at,closed_at,realized_pnl,realized_return\n2021-03-08T00:00:00+00:00,2021-03-08T00:10:00+00:00,1.0,0.01\n",
        encoding="utf-8",
    )
    (run_dir / "run_config.toml").write_text(
        f"[backtest]\nstrategy = \"{strategy_name}\"\n[run]\nmode = \"single_contract\"\ninstrument_id = \"MGCJ1.GLBX\"\n",
        encoding="utf-8",
    )
    (run_dir / "analytics" / "underwater_curve.csv").write_text(
        "timestamp,equity,running_peak,underwater_dollars,underwater_pct\n2021-03-08T00:00:00+00:00,50000,50000,0,0\n",
        encoding="utf-8",
    )
    (run_dir / "analytics" / "drawdown_episodes.csv").write_text(
        "episode_start,episode_end,episode_duration_bars,episode_duration_days,drawdown_pct,drawdown_dollars,recovery_start,recovery_end,recovery_duration_bars,recovery_duration_days,recovered\n",
        encoding="utf-8",
    )
    for name in ["by_session.csv", "by_volatility_regime.csv", "by_month.csv", "by_year.csv", "by_day_of_week.csv", "by_hour.csv"]:
        (run_dir / "analytics" / "breakdowns" / name).write_text(
            "bucket,trade_count,win_rate,total_pnl,average_pnl_per_trade,sharpe_ratio,max_drawdown\nrth,1,100,1,1,0,0\n",
            encoding="utf-8",
        )
    (run_dir / "analytics" / "audit_log.csv").write_text(
        "record_type,timestamp,optional_confirmation_count,entry_fired,entry_rejected_reason\narmed_bar,2021-03-08T00:00:00+00:00,1,false,core_triggers_failed\n",
        encoding="utf-8",
    )


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
        ],
        "equity_curve": [
            {"timestamp": "2021-03-08T00:00:00+00:00", "equity": 50000.0},
            {"timestamp": "2021-03-08T00:10:00+00:00", "equity": 50012.5},
        ],
    }
