from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import optuna

from mgc_bt.backtest.runner import run_backtest
from mgc_bt.config import Settings
from mgc_bt.optimization.search_space import sample_trial_params

OBJECTIVE_PENALTY = -10.0


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

    def __call__(self, trial: optuna.trial.Trial) -> float:
        sampled_params = sample_trial_params(trial)
        run_params = dict(sampled_params)
        run_params.update(
            {
                "instrument_id": None,
                "start_date": self.settings.optimization.in_sample_start,
                "end_date": self.settings.optimization.in_sample_end,
            },
        )
        trial.set_user_attr("mode", "auto_roll")
        trial.set_user_attr("evaluation_window", "in_sample")
        try:
            result = run_backtest(self.settings, run_params)
        except Exception as exc:
            trial.set_user_attr("error", f"{type(exc).__name__}: {exc}")
            raise

        objective_score = compute_objective_score(result)
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
        return objective_score
