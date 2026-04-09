from __future__ import annotations

import csv

import optuna

from mgc_bt.config import load_settings
from mgc_bt.optimization.results import write_stability_artifacts
from mgc_bt.optimization.stability import HEATMAP_OFFSETS
from mgc_bt.optimization.stability import run_stability_analysis


def test_run_stability_analysis_builds_5x5_heatmap_and_robustness(monkeypatch, tmp_path) -> None:
    settings = load_settings("configs/settings.toml")
    study = optuna.create_study(direction="maximize")

    def objective(trial):
        factor = trial.suggest_float("supertrend_factor", 1.5, 5.0)
        pullback = trial.suggest_int("min_pullback_bars", 2, 8)
        return factor - (pullback * 0.05)

    study.optimize(objective, n_trials=8)

    def fake_evaluate_params(settings, params, *, start_date, end_date, evaluation_window):
        sharpe = float(params["supertrend_factor"]) - (float(params["min_pullback_bars"]) * 0.1)
        return {
            "sharpe_ratio": sharpe,
            "total_pnl": sharpe * 1000.0,
            "max_drawdown_pct": max(1.0, 15.0 - sharpe),
            "equity_curve": [{"timestamp": start_date, "equity": 50000.0}, {"timestamp": end_date, "equity": 51000.0}],
            "total_trades": 25,
        }

    monkeypatch.setattr("mgc_bt.optimization.stability.evaluate_params", fake_evaluate_params)
    analysis = run_stability_analysis(
        settings=settings,
        study=study,
        best_params={"supertrend_factor": 3.0, "min_pullback_bars": 3},
        evaluation_context={
            "mode": "holdout",
            "start": "2025-03-08T00:00:00+00:00",
            "end": "2025-06-08T00:00:00+00:00",
        },
    )

    assert analysis["status"] == "completed"
    assert len(analysis["heatmap_rows"]) == 25
    assert HEATMAP_OFFSETS == [-20, -10, 0, 10, 20]
    assert analysis["robustness_score"] >= 70.0
    assert analysis["robust"] is True
    assert all(2 <= row["value_y"] <= 8 for row in analysis["heatmap_rows"])

    outputs = write_stability_artifacts(tmp_path, analysis)
    with outputs["heatmap_path"].open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 25


def test_run_stability_analysis_skips_when_insufficient_completed_trials(monkeypatch) -> None:
    settings = load_settings("configs/settings.toml")
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda trial: trial.suggest_float("supertrend_factor", 1.5, 5.0), n_trials=1)

    monkeypatch.setattr(
        "mgc_bt.optimization.stability.evaluate_params",
        lambda *args, **kwargs: {"sharpe_ratio": 0.0, "total_pnl": 0.0, "max_drawdown_pct": 0.0},
    )
    analysis = run_stability_analysis(
        settings=settings,
        study=study,
        best_params={"supertrend_factor": 3.0},
        evaluation_context={
            "mode": "holdout",
            "start": "2025-03-08T00:00:00+00:00",
            "end": "2025-06-08T00:00:00+00:00",
        },
    )

    assert analysis["status"] == "skipped"
    assert analysis["skipped_reason"] == "insufficient_completed_trials"
