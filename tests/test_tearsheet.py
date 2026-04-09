from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import csv
import json

from mgc_bt.backtest.artifacts import write_backtest_artifacts
from mgc_bt.reporting.comparison import write_comparison_tearsheet
from mgc_bt.config import load_settings
from mgc_bt.reporting.loaders import SECTION_UNAVAILABLE_PREFIX
from mgc_bt.reporting.loaders import load_tearsheet_payload
from mgc_bt.reporting.tearsheet import render_tearsheet


def test_loader_reads_backtest_run_folder(tmp_path: Path) -> None:
    settings = load_settings("configs/settings.toml")
    settings = replace(settings, paths=replace(settings.paths, results_root=tmp_path))
    artifacts = write_backtest_artifacts(settings, _sample_result())

    payload = load_tearsheet_payload(artifacts["run_dir"])

    assert payload.run_type == "backtest"
    assert payload.summary["instrument_id"] == "MGCJ1.GLBX"
    assert payload.audit_log is not None
    assert payload.breakdowns["by_session"]


def test_loader_reads_optimization_layout_and_marks_missing_optional_sections(tmp_path: Path) -> None:
    run_dir = tmp_path / "optimization" / "2026-04-09_000000"
    best_run = run_dir / "best_run"
    best_run.mkdir(parents=True)
    (best_run / "analytics" / "breakdowns").mkdir(parents=True)
    (best_run / "summary.json").write_text(json.dumps({"instrument_id": "AUTO_ROLL:MGC", "start_date": "2021-01-01T00:00:00+00:00", "end_date": "2021-12-31T00:00:00+00:00", "total_pnl": 10, "sharpe_ratio": 1.2, "win_rate": 55.0, "max_drawdown_pct": 5.0, "max_drawdown": 250.0, "total_trades": 10}), encoding="utf-8")
    (best_run / "trades.csv").write_text("opened_at,closed_at,realized_pnl,realized_return\n2021-01-01T00:00:00+00:00,2021-01-01T00:10:00+00:00,10.0,0.01\n", encoding="utf-8")
    (best_run / "run_config.toml").write_text("[run]\nmode = \"auto_roll\"\ninstrument_id = \"AUTO_ROLL:MGC\"\n", encoding="utf-8")
    (best_run / "analytics" / "underwater_curve.csv").write_text("timestamp,equity,running_peak,underwater_dollars,underwater_pct\n2021-01-01T00:00:00+00:00,50000,50000,0,0\n", encoding="utf-8")
    (best_run / "analytics" / "drawdown_episodes.csv").write_text("episode_start,episode_end,episode_duration_bars,episode_duration_days,drawdown_pct,drawdown_dollars,recovery_start,recovery_end,recovery_duration_bars,recovery_duration_days,recovered\n", encoding="utf-8")
    (best_run / "analytics" / "breakdowns" / "by_session.csv").write_text("bucket,trade_count,win_rate,total_pnl,average_pnl_per_trade,sharpe_ratio,max_drawdown\nrth,1,100,10,10,0,0\n", encoding="utf-8")
    for name in ["by_volatility_regime.csv", "by_month.csv", "by_year.csv", "by_day_of_week.csv", "by_hour.csv"]:
        (best_run / "analytics" / "breakdowns" / name).write_text("bucket,trade_count,win_rate,total_pnl,average_pnl_per_trade,sharpe_ratio,max_drawdown\n", encoding="utf-8")
    (best_run / "analytics" / "audit_log.csv").write_text("record_type,timestamp,optional_confirmation_count,entry_fired,entry_rejected_reason\narmed_bar,2021-01-01T00:00:00+00:00,1,false,volume_fail\n", encoding="utf-8")
    (run_dir / "optimization_summary.json").write_text(json.dumps({"study_name": "x"}), encoding="utf-8")
    (run_dir / "ranked_results.csv").write_text("rank,trial_number,objective_score,sharpe_ratio,total_pnl,win_rate,max_drawdown_pct,total_trades\n1,0,1.2,1.2,10,55,5,10\n", encoding="utf-8")

    payload = load_tearsheet_payload(run_dir)

    assert payload.run_type == "optimize"
    assert payload.shared_run_dir == best_run
    assert payload.notices["parameter_sensitivity.csv"].startswith(SECTION_UNAVAILABLE_PREFIX)
    assert payload.notices["window_results.csv"].startswith(SECTION_UNAVAILABLE_PREFIX)


def test_render_tearsheet_is_self_contained_and_shows_missing_sections(tmp_path: Path) -> None:
    settings = load_settings("configs/settings.toml")
    settings = replace(settings, paths=replace(settings.paths, results_root=tmp_path))
    artifacts = write_backtest_artifacts(settings, _sample_result(), refresh_latest=False)
    audit_path = artifacts["run_dir"] / "analytics" / "audit_log.csv"
    audit_path.unlink()

    payload = load_tearsheet_payload(artifacts["run_dir"])
    html_text = render_tearsheet(payload)

    assert "Executive summary" in html_text
    assert "Audit diagnostics" in html_text
    assert "Section unavailable - audit_log.csv not found" in html_text
    assert "cdn.plot.ly" not in html_text
    assert "https://" not in html_text
    assert html_text.count("window.PlotlyConfig") <= 1


def test_render_optimization_tearsheet_shows_optional_analysis_sections(tmp_path: Path) -> None:
    run_dir = tmp_path / "optimization" / "2026-04-09_000001"
    best_run = run_dir / "best_run"
    best_run.mkdir(parents=True)
    (best_run / "analytics" / "breakdowns").mkdir(parents=True)
    (best_run / "summary.json").write_text(json.dumps({"instrument_id": "AUTO_ROLL:MGC", "start_date": "2021-01-01T00:00:00+00:00", "end_date": "2021-12-31T00:00:00+00:00", "total_pnl": 10, "sharpe_ratio": 1.2, "win_rate": 55.0, "max_drawdown_pct": 5.0, "max_drawdown": 250.0, "total_trades": 10}), encoding="utf-8")
    (best_run / "trades.csv").write_text("opened_at,closed_at,realized_pnl,realized_return\n2021-01-01T00:00:00+00:00,2021-01-01T00:10:00+00:00,10.0,0.01\n", encoding="utf-8")
    (best_run / "run_config.toml").write_text("[run]\nmode = \"auto_roll\"\ninstrument_id = \"AUTO_ROLL:MGC\"\n", encoding="utf-8")
    (best_run / "analytics" / "underwater_curve.csv").write_text("timestamp,equity,running_peak,underwater_dollars,underwater_pct\n2021-01-01T00:00:00+00:00,50000,50000,0,0\n", encoding="utf-8")
    (best_run / "analytics" / "drawdown_episodes.csv").write_text("episode_start,episode_end,episode_duration_bars,episode_duration_days,drawdown_pct,drawdown_dollars,recovery_start,recovery_end,recovery_duration_bars,recovery_duration_days,recovered\n", encoding="utf-8")
    for name in ["by_session.csv", "by_volatility_regime.csv", "by_month.csv", "by_year.csv", "by_day_of_week.csv", "by_hour.csv"]:
        (best_run / "analytics" / "breakdowns" / name).write_text("bucket,trade_count,win_rate,total_pnl,average_pnl_per_trade,sharpe_ratio,max_drawdown\nrth,1,100,10,10,0,0\n", encoding="utf-8")
    (best_run / "analytics" / "audit_log.csv").write_text("record_type,timestamp,optional_confirmation_count,entry_fired,entry_rejected_reason\narmed_bar,2021-01-01T00:00:00+00:00,1,false,volume_fail\n", encoding="utf-8")
    (run_dir / "optimization_summary.json").write_text(json.dumps({"study_name": "x"}), encoding="utf-8")
    (run_dir / "ranked_results.csv").write_text("rank,trial_number,objective_score,sharpe_ratio,total_pnl,win_rate,max_drawdown_pct,total_trades\n1,0,1.2,1.2,10,55,5,10\n", encoding="utf-8")
    (run_dir / "analytics").mkdir(parents=True)
    (run_dir / "analytics" / "parameter_sensitivity.csv").write_text("parameter_name,correlation_with_objective,sharpe_range_across_buckets,most_sensitive\nsupertrend_factor,0.1,0.2,true\n", encoding="utf-8")
    (run_dir / "walk_forward").mkdir()
    (run_dir / "walk_forward" / "window_results.csv").write_text("window_index,test_sharpe\n1,1.1\n", encoding="utf-8")
    (run_dir / "monte_carlo").mkdir()
    (run_dir / "monte_carlo" / "equity_confidence_bands.csv").write_text("trade_index,p05,p25,p50,p75,p95\n0,1,2,3,4,5\n", encoding="utf-8")
    (run_dir / "stability").mkdir()
    (run_dir / "stability" / "top_pair_heatmap.csv").write_text("value_x,value_y,sharpe_ratio\n1,2,1.1\n", encoding="utf-8")

    html_text = render_tearsheet(load_tearsheet_payload(run_dir))

    assert "Optimization sections" in html_text
    assert "Walk-forward" in html_text
    assert "Monte Carlo" in html_text
    assert "Parameter heatmap" in html_text
    assert "Parameter sensitivity" in html_text


def test_render_comparison_tearsheet_reuses_persisted_run_folders(tmp_path: Path) -> None:
    run_a = tmp_path / "backtests" / "run_a"
    run_b = tmp_path / "backtests" / "run_b"
    comparison_dir = tmp_path / "comparisons" / "run_cmp"
    comparison_dir.mkdir(parents=True)
    _write_minimal_backtest_run(run_a, strategy_name="mgc_production", total_pnl=12.5)
    _write_minimal_backtest_run(run_b, strategy_name="phase2_harness", total_pnl=9.0)
    (comparison_dir / "metrics_delta.csv").write_text(
        "metric,strategy_a,strategy_b,delta_b_minus_a\ntotal_pnl,12.5,9.0,-3.5\n",
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


def _write_minimal_backtest_run(run_dir: Path, *, strategy_name: str, total_pnl: float) -> None:
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
