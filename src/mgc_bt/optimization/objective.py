from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import optuna

from mgc_bt.backtest.runner import run_backtest
from mgc_bt.config import Settings
from mgc_bt.optimization.search_space import sample_trial_params

OBJECTIVE_PENALTY = -10.0


def evaluate_params(
    settings: Settings,
    params: dict[str, Any],
    *,
    start_date: str,
    end_date: str,
    evaluation_window: str,
) -> dict[str, Any]:
    run_params = dict(params)
    run_params.update(
        {
            "instrument_id": None,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
    result = run_backtest(settings, run_params)
    result.setdefault("parameters", run_params)
    result["evaluation_window"] = evaluation_window
    return result


def apply_result_user_attrs(
    trial: optuna.trial.Trial | optuna.trial.FrozenTrial,
    result: dict[str, Any],
    *,
    objective_score: float,
    evaluation_window: str,
) -> None:
    trial.set_user_attr("mode", result.get("mode", "auto_roll"))
    trial.set_user_attr("evaluation_window", evaluation_window)
    trial.set_user_attr("objective_score", objective_score)
    trial.set_user_attr("sharpe_ratio", result.get("sharpe_ratio"))
    trial.set_user_attr("total_pnl", float(result.get("total_pnl", 0.0)))
    trial.set_user_attr("win_rate", float(result.get("win_rate", 0.0)))
    trial.set_user_attr("max_drawdown_pct", float(result.get("max_drawdown_pct") or 0.0))
    trial.set_user_attr("max_drawdown", float(result.get("max_drawdown") or 0.0))
    trial.set_user_attr("total_trades", int(result.get("total_trades", 0)))
    trial.set_user_attr("start_date", result.get("start_date"))
    trial.set_user_attr("end_date", result.get("end_date"))
    trial.set_user_attr("instrument_id", result.get("instrument_id"))


def compute_objective_score(result: dict[str, Any]) -> float:
    total_trades = int(result.get("total_trades", 0))
    max_drawdown_pct = float(result.get("max_drawdown_pct") or 0.0)
    if total_trades < 30:
        return OBJECTIVE_PENALTY
    if max_drawdown_pct > 25.0:
        return OBJECTIVE_PENALTY
    sharpe_ratio = result.get("sharpe_ratio")
    if sharpe_ratio is None:
        return 0.0
    return float(sharpe_ratio)


@dataclass
class TrialEvaluator:
    settings: Settings
    start_date: str | None = None
    end_date: str | None = None
    evaluation_window: str = "in_sample"

    def __call__(self, trial: optuna.trial.Trial) -> float:
        sampled_params = sample_trial_params(trial)
        try:
            result = evaluate_params(
                self.settings,
                sampled_params,
                start_date=self.start_date or self.settings.optimization.in_sample_start,
                end_date=self.end_date or self.settings.optimization.in_sample_end,
                evaluation_window=self.evaluation_window,
            )
        except Exception as exc:
            trial.set_user_attr("error", f"{type(exc).__name__}: {exc}")
            raise

        objective_score = compute_objective_score(result)
        apply_result_user_attrs(
            trial,
            result,
            objective_score=objective_score,
            evaluation_window=self.evaluation_window,
        )
        return objective_score
