from __future__ import annotations

import optuna

from mgc_bt.config import load_settings
from mgc_bt.optimization.objective import OBJECTIVE_PENALTY
from mgc_bt.optimization.objective import TrialEvaluator
from mgc_bt.optimization.objective import evaluate_params
from mgc_bt.optimization.objective import compute_objective_score
from mgc_bt.optimization.search_space import optimized_param_names
from mgc_bt.optimization.search_space import sample_trial_params


def test_compute_objective_score_applies_locked_penalties() -> None:
    assert compute_objective_score({"total_trades": 10, "max_drawdown_pct": 5.0, "sharpe_ratio": 3.0}) == OBJECTIVE_PENALTY
    assert compute_objective_score({"total_trades": 40, "max_drawdown_pct": 30.0, "sharpe_ratio": 3.0}) == OBJECTIVE_PENALTY
    assert compute_objective_score({"total_trades": 40, "max_drawdown_pct": 10.0, "sharpe_ratio": 1.5}) == 1.5


def test_search_space_contains_strategy_and_custom_risk_only() -> None:
    class DummyTrial:
        def suggest_int(self, name: str, low: int, high: int) -> int:
            return low

        def suggest_float(self, name: str, low: float, high: float) -> float:
            return low

    trial = DummyTrial()
    params = sample_trial_params(trial)
    assert "supertrend_atr_length" in params
    assert "max_loss_per_trade_dollars" in params
    assert "max_daily_loss_dollars" in params
    assert "max_consecutive_losses" in params
    assert "max_drawdown_pct" in params
    assert "max_daily_trades" not in params
    assert "native_max_order_submit_rate" not in params
    assert optimized_param_names() == list(params.keys())


def test_trial_evaluator_calls_shared_runner(monkeypatch) -> None:
    settings = load_settings("configs/settings.toml")
    captured: dict[str, object] = {}

    def fake_run_backtest(passed_settings, params):
        captured["settings"] = passed_settings
        captured["params"] = params
        return {
            "total_trades": 55,
            "max_drawdown_pct": 8.0,
            "sharpe_ratio": 1.25,
            "total_pnl": 1500.0,
            "win_rate": 45.0,
            "max_drawdown": 250.0,
            "start_date": params["start_date"],
            "end_date": params["end_date"],
            "instrument_id": "AUTO_ROLL:MGC",
        }

    monkeypatch.setattr("mgc_bt.optimization.objective.run_backtest", fake_run_backtest)
    evaluator = TrialEvaluator(settings)

    trial = optuna.trial.FixedTrial(
        {
            "supertrend_atr_length": 10,
            "supertrend_factor": 3.0,
            "supertrend_training_period": 100,
            "vwap_reset_hour_utc": 0,
            "wavetrend_n1": 10,
            "wavetrend_n2": 21,
            "wavetrend_ob_level": 2.0,
            "delta_imbalance_threshold": 0.4,
            "absorption_volume_multiplier": 1.5,
            "absorption_range_multiplier": 0.6,
            "volume_lookback": 20,
            "atr_trail_length": 14,
            "atr_trail_multiplier": 2.0,
            "min_pullback_bars": 3,
            "max_loss_per_trade_dollars": 150.0,
            "max_daily_loss_dollars": 300.0,
            "max_consecutive_losses": 4,
            "max_drawdown_pct": 5.0,
        },
    )

    score = evaluator(trial)
    assert score == 1.25
    assert captured["settings"] == settings
    params = captured["params"]
    assert params["start_date"] == settings.optimization.in_sample_start
    assert params["end_date"] == settings.optimization.in_sample_end
    assert params["instrument_id"] is None


def test_evaluate_params_routes_walk_forward_windows_through_shared_runner(monkeypatch) -> None:
    settings = load_settings("configs/settings.toml")
    captured: dict[str, object] = {}

    def fake_run_backtest(passed_settings, params):
        captured["settings"] = passed_settings
        captured["params"] = params
        return {
            "mode": "auto_roll",
            "instrument_id": "AUTO_ROLL:MGC",
            "start_date": params["start_date"],
            "end_date": params["end_date"],
            "sharpe_ratio": 0.9,
            "total_pnl": 120.0,
            "win_rate": 45.0,
            "max_drawdown": 50.0,
            "max_drawdown_pct": 4.0,
            "total_trades": 12,
            "parameters": params,
        }

    monkeypatch.setattr("mgc_bt.optimization.objective.run_backtest", fake_run_backtest)
    result = evaluate_params(
        settings,
        {"supertrend_factor": 2.5},
        start_date="2022-01-01T00:00:00+00:00",
        end_date="2022-02-01T00:00:00+00:00",
        evaluation_window="validation",
    )

    assert captured["settings"] == settings
    assert captured["params"]["start_date"] == "2022-01-01T00:00:00+00:00"
    assert captured["params"]["end_date"] == "2022-02-01T00:00:00+00:00"
    assert captured["params"]["instrument_id"] is None
    assert result["evaluation_window"] == "validation"
