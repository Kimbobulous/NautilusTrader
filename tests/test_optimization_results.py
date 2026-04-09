from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import csv
import json

import optuna

from mgc_bt.config import OptimizationConfig
from mgc_bt.config import PathsConfig
from mgc_bt.config import load_settings
from mgc_bt.optimization.results import ranked_trial_rows
from mgc_bt.optimization.study import run_optimization
from mgc_bt.optimization.walk_forward import WalkForwardAggregateSummary
from mgc_bt.optimization.walk_forward import WalkForwardWindowResult


def test_ranked_trial_rows_use_locked_tie_break_order() -> None:
    study = optuna.create_study(direction="maximize")

    def objective(trial):
        if trial.number == 0:
            trial.set_user_attr("sharpe_ratio", 1.0)
            trial.set_user_attr("total_pnl", 100.0)
            trial.set_user_attr("win_rate", 50.0)
            trial.set_user_attr("max_drawdown_pct", 12.0)
            trial.set_user_attr("total_trades", 40)
            return 1.5
        trial.set_user_attr("sharpe_ratio", 1.0)
        trial.set_user_attr("total_pnl", 110.0)
        trial.set_user_attr("win_rate", 51.0)
        trial.set_user_attr("max_drawdown_pct", 8.0)
        trial.set_user_attr("total_trades", 45)
        return 1.5

    study.optimize(objective, n_trials=2)
    rows = ranked_trial_rows(study)
    assert rows[0]["trial_number"] == 1
    assert rows[0]["rank"] == 1
    assert rows[1]["trial_number"] == 0


def test_run_optimization_writes_ranked_results_and_holdout_exports(tmp_path, monkeypatch) -> None:
    settings = _temp_settings(tmp_path)

    def fake_sample_trial_params(trial):
        base = trial.number + 1
        return {
            "supertrend_atr_length": trial.suggest_int("supertrend_atr_length", 5 + trial.number, 5 + trial.number),
            "supertrend_factor": trial.suggest_float("supertrend_factor", 1.5 + trial.number, 1.5 + trial.number),
            "supertrend_training_period": trial.suggest_int("supertrend_training_period", 50, 50),
            "vwap_reset_hour_utc": trial.suggest_int("vwap_reset_hour_utc", 0, 0),
            "wavetrend_n1": trial.suggest_int("wavetrend_n1", 10, 10),
            "wavetrend_n2": trial.suggest_int("wavetrend_n2", 21, 21),
            "wavetrend_ob_level": trial.suggest_float("wavetrend_ob_level", 2.0, 2.0),
            "delta_imbalance_threshold": trial.suggest_float("delta_imbalance_threshold", 0.3, 0.3),
            "absorption_volume_multiplier": trial.suggest_float("absorption_volume_multiplier", 1.2, 1.2),
            "absorption_range_multiplier": trial.suggest_float("absorption_range_multiplier", 0.5, 0.5),
            "volume_lookback": trial.suggest_int("volume_lookback", 20, 20),
            "atr_trail_length": trial.suggest_int("atr_trail_length", 14, 14),
            "atr_trail_multiplier": trial.suggest_float("atr_trail_multiplier", 2.0, 2.0),
            "min_pullback_bars": trial.suggest_int("min_pullback_bars", 2 + trial.number, 2 + trial.number),
            "max_loss_per_trade_dollars": trial.suggest_float("max_loss_per_trade_dollars", 100.0 + base, 100.0 + base),
            "max_daily_loss_dollars": trial.suggest_float("max_daily_loss_dollars", 300.0 + base, 300.0 + base),
            "max_consecutive_losses": trial.suggest_int("max_consecutive_losses", 3, 3),
            "max_drawdown_pct": trial.suggest_float("max_drawdown_pct", 5.0, 5.0),
        }

    def fake_run_backtest(settings, params):
        start_date = params["start_date"]
        factor = float(params["supertrend_factor"])
        holdout = start_date == settings.optimization.holdout_start
        sharpe = factor - (0.4 if holdout else 0.0)
        return {
            "mode": "auto_roll",
            "instrument_id": "AUTO_ROLL:MGC",
            "segment_instruments": ["MGCJ1.GLBX"],
            "segment_count": 1,
            "start_date": params["start_date"],
            "end_date": params["end_date"],
            "total_pnl": factor * 1000.0,
            "sharpe_ratio": sharpe,
            "win_rate": 55.0,
            "max_drawdown": 250.0,
            "max_drawdown_pct": 10.0,
            "total_trades": 50,
            "parameters": params,
            "segments": [],
            "trade_log": [
                {
                    "instrument_id": "MGCJ1.GLBX",
                    "entry_side": "BUY",
                    "quantity": 1.0,
                    "opened_at": params["start_date"],
                    "closed_at": params["end_date"],
                    "avg_px_open": 100.0,
                    "avg_px_close": 101.0,
                    "realized_pnl": 10.0,
                    "realized_return": 0.01,
                    "commissions": 1.0,
                    "position_id": "1",
                    "slippage": 0.1,
                },
            ],
            "equity_curve": [
                {"timestamp": params["start_date"], "equity": 50000.0},
                {"timestamp": params["end_date"], "equity": 50500.0},
            ],
        }

    monkeypatch.setattr("mgc_bt.optimization.objective.sample_trial_params", fake_sample_trial_params)
    monkeypatch.setattr("mgc_bt.optimization.objective.run_backtest", fake_run_backtest)
    monkeypatch.setattr("mgc_bt.optimization.export.run_backtest", fake_run_backtest)

    result = run_optimization(settings, study_name="opt-test", max_trials=3)
    assert result["completed_trials"] == 3
    assert result["failed_trials"] == 0
    assert result["overfit_warning"] is True

    run_dir = result["run_dir"]
    assert (run_dir / "ranked_results.csv").exists()
    assert (run_dir / "optimization_summary.json").exists()
    assert (run_dir / "run_config.toml").exists()
    assert (run_dir / "failed_trials.json").exists()
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "best_run" / "summary.json").exists()
    assert (run_dir / "best_run" / "trades.csv").exists()
    assert (run_dir / "best_run" / "equity_curve.png").exists()
    assert (run_dir / "best_run" / "holdout_results.json").exists()
    assert (run_dir / "best_run" / "holdout_equity_curve.png").exists()
    assert (run_dir.parent / "latest" / "manifest.json").exists()
    assert (run_dir.parent / "latest" / "ranked_results.csv").exists()
    assert not (run_dir / "walk_forward").exists()
    assert not (run_dir / "monte_carlo").exists()
    assert not (run_dir / "stability").exists()

    with (run_dir / "ranked_results.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert rows[0].keys() == {
        "rank",
        "trial_number",
        "objective_score",
        "sharpe_ratio",
        "total_pnl",
        "win_rate",
        "max_drawdown_pct",
        "total_trades",
        "param_supertrend_atr_length",
        "param_supertrend_factor",
        "param_supertrend_training_period",
        "param_vwap_reset_hour_utc",
        "param_wavetrend_n1",
        "param_wavetrend_n2",
        "param_wavetrend_ob_level",
        "param_delta_imbalance_threshold",
        "param_absorption_volume_multiplier",
        "param_absorption_range_multiplier",
        "param_volume_lookback",
        "param_atr_trail_length",
        "param_atr_trail_multiplier",
        "param_min_pullback_bars",
        "param_max_loss_per_trade_dollars",
        "param_max_daily_loss_dollars",
        "param_max_consecutive_losses",
        "param_max_drawdown_pct",
    }

    manifest_payload = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "ranked_results.csv" in manifest_payload["files"]
    assert "optimization_summary.json" in manifest_payload["files"]
    summary_payload = json.loads((run_dir / "optimization_summary.json").read_text(encoding="utf-8"))
    assert "analysis_flags" not in summary_payload


def test_run_optimization_can_leave_latest_untouched(tmp_path, monkeypatch) -> None:
    settings = _temp_settings(tmp_path)

    def fake_sample_trial_params(trial):
        return {
            "supertrend_atr_length": 5,
            "supertrend_factor": 2.0,
            "supertrend_training_period": 50,
            "vwap_reset_hour_utc": 0,
            "wavetrend_n1": 10,
            "wavetrend_n2": 21,
            "wavetrend_ob_level": 2.0,
            "delta_imbalance_threshold": 0.3,
            "absorption_volume_multiplier": 1.2,
            "absorption_range_multiplier": 0.5,
            "volume_lookback": 20,
            "atr_trail_length": 14,
            "atr_trail_multiplier": 2.0,
            "min_pullback_bars": 2,
            "max_loss_per_trade_dollars": 101.0,
            "max_daily_loss_dollars": 301.0,
            "max_consecutive_losses": 3,
            "max_drawdown_pct": 5.0,
        }

    def fake_run_backtest(settings, params):
        return {
            "mode": "auto_roll",
            "instrument_id": "AUTO_ROLL:MGC",
            "segment_instruments": ["MGCJ1.GLBX"],
            "segment_count": 1,
            "start_date": params["start_date"],
            "end_date": params["end_date"],
            "total_pnl": 500.0,
            "sharpe_ratio": 1.0,
            "win_rate": 55.0,
            "max_drawdown": 250.0,
            "max_drawdown_pct": 10.0,
            "total_trades": 50,
            "parameters": params,
            "segments": [],
            "trade_log": [],
            "equity_curve": [
                {"timestamp": params["start_date"], "equity": 50000.0},
                {"timestamp": params["end_date"], "equity": 50500.0},
            ],
        }

    monkeypatch.setattr("mgc_bt.optimization.objective.sample_trial_params", fake_sample_trial_params)
    monkeypatch.setattr("mgc_bt.optimization.objective.run_backtest", fake_run_backtest)
    monkeypatch.setattr("mgc_bt.optimization.export.run_backtest", fake_run_backtest)

    result = run_optimization(settings, study_name="opt-no-latest", max_trials=1, refresh_latest=False)

    assert result["latest_dir"] is None
    assert not (result["run_dir"].parent / "latest").exists()
    manifest_payload = json.loads((result["run_dir"] / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_payload["latest_refreshed"] is False


def test_run_optimization_writes_walk_forward_artifacts(tmp_path, monkeypatch) -> None:
    settings = _temp_settings(tmp_path)

    monkeypatch.setattr(
        "mgc_bt.optimization.study.run_walk_forward_optimization",
        lambda *args, **kwargs: {
            "windows": [],
            "failed_trials": [],
            "final_test_result": None,
            "window_results": [
                WalkForwardWindowResult(
                    window_index=1,
                    train_start="2021-01-01T00:00:00+00:00",
                    train_end="2022-01-01T00:00:00+00:00",
                    validation_start="2022-01-01T00:00:00+00:00",
                    validation_end="2022-04-01T00:00:00+00:00",
                    test_start="2022-04-01T00:00:00+00:00",
                    test_end="2022-07-01T00:00:00+00:00",
                    status="completed",
                    skipped_reason=None,
                    inconclusive=False,
                    training_bar_count=60000,
                    training_completed_trials=3,
                    training_sharpe=1.2,
                    validation_sharpe=1.1,
                    validation_max_drawdown_pct=9.0,
                    validation_total_pnl=1000.0,
                    test_sharpe=0.9,
                    test_total_pnl=800.0,
                    test_total_trades=20,
                    test_bar_count=15000,
                    selected_params={"supertrend_factor": 2.5},
                    test_result={
                        "mode": "auto_roll",
                        "instrument_id": "AUTO_ROLL:MGC",
                        "segment_instruments": ["MGCJ1.GLBX"],
                        "segment_count": 1,
                        "start_date": "2022-04-01T00:00:00+00:00",
                        "end_date": "2022-07-01T00:00:00+00:00",
                        "total_pnl": 800.0,
                        "sharpe_ratio": 0.9,
                        "win_rate": 55.0,
                        "max_drawdown": 250.0,
                        "max_drawdown_pct": 10.0,
                        "total_trades": 20,
                        "parameters": {"supertrend_factor": 2.5},
                        "segments": [],
                        "trade_log": [],
                        "equity_curve": [
                            {"timestamp": "2022-04-01T00:00:00+00:00", "equity": 50000.0},
                            {"timestamp": "2022-07-01T00:00:00+00:00", "equity": 50800.0},
                        ],
                    },
                ),
                WalkForwardWindowResult(
                    window_index=2,
                    train_start="2021-04-01T00:00:00+00:00",
                    train_end="2022-04-01T00:00:00+00:00",
                    validation_start="2022-04-01T00:00:00+00:00",
                    validation_end="2022-07-01T00:00:00+00:00",
                    test_start="2022-07-01T00:00:00+00:00",
                    test_end="2022-10-01T00:00:00+00:00",
                    status="inconclusive",
                    skipped_reason=None,
                    inconclusive=True,
                    training_bar_count=61000,
                    training_completed_trials=2,
                    training_sharpe=1.0,
                    validation_sharpe=0.8,
                    validation_max_drawdown_pct=12.0,
                    validation_total_pnl=500.0,
                    test_sharpe=0.2,
                    test_total_pnl=100.0,
                    test_total_trades=5,
                    test_bar_count=15000,
                    selected_params={"supertrend_factor": 2.0},
                    test_result={
                        "mode": "auto_roll",
                        "instrument_id": "AUTO_ROLL:MGC",
                        "segment_instruments": ["MGCQ1.GLBX"],
                        "segment_count": 1,
                        "start_date": "2022-07-01T00:00:00+00:00",
                        "end_date": "2022-10-01T00:00:00+00:00",
                        "total_pnl": 100.0,
                        "sharpe_ratio": 0.2,
                        "win_rate": 40.0,
                        "max_drawdown": 300.0,
                        "max_drawdown_pct": 12.0,
                        "total_trades": 5,
                        "parameters": {"supertrend_factor": 2.0},
                        "segments": [],
                        "trade_log": [],
                        "equity_curve": [
                            {"timestamp": "2022-07-01T00:00:00+00:00", "equity": 50800.0},
                            {"timestamp": "2022-10-01T00:00:00+00:00", "equity": 50900.0},
                        ],
                    },
                ),
            ],
            "aggregate": WalkForwardAggregateSummary(
                completed_window_count=1,
                skipped_window_count=0,
                inconclusive_window_count=1,
                aggregated_oos_sharpe=0.9,
                aggregated_oos_total_pnl=800.0,
                aggregated_equity_curve=[
                    {"timestamp": "2022-04-01T00:00:00+00:00", "equity": 50000.0},
                    {"timestamp": "2022-07-01T00:00:00+00:00", "equity": 50800.0},
                ],
                selected_params=[
                    {"window_index": 1, "supertrend_factor": 2.5},
                    {"window_index": 2, "supertrend_factor": 2.0},
                ],
                status="completed",
            ),
        },
    )

    result = run_optimization(settings, study_name="wf-test", max_trials=2, walk_forward=True)

    walk_root = result["run_dir"] / "walk_forward"
    assert (walk_root / "window_results.csv").exists()
    assert (walk_root / "aggregated_summary.json").exists()
    assert (walk_root / "equity_curve.png").exists()
    assert (walk_root / "params_over_time.csv").exists()

    summary_payload = json.loads((walk_root / "aggregated_summary.json").read_text(encoding="utf-8"))
    assert summary_payload["schema_version"] == 1
    assert summary_payload["analysis_type"] == "walk_forward"
    assert summary_payload["status"] == "completed"
    assert summary_payload["completed_window_count"] == 1
    assert summary_payload["inconclusive_window_count"] == 1


def _temp_settings(tmp_path: Path):
    settings = load_settings("configs/settings.toml")
    return replace(
        settings,
        paths=replace(
            settings.paths,
            project_root=tmp_path,
            catalog_root=tmp_path / "catalog",
            results_root=tmp_path / "results",
        ),
        optimization=replace(
            settings.optimization,
            study_name="opt-test",
            max_trials=3,
            max_runtime_seconds=60,
            early_stop_window=50,
            results_subdir="optimization",
        ),
    )
