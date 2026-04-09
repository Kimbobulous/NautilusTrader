from __future__ import annotations

from typing import Any

import optuna


def sample_trial_params(trial: optuna.trial.Trial) -> dict[str, Any]:
    return {
        "supertrend_atr_length": trial.suggest_int("supertrend_atr_length", 5, 20),
        "supertrend_factor": trial.suggest_float("supertrend_factor", 1.5, 5.0),
        "supertrend_training_period": trial.suggest_int("supertrend_training_period", 50, 200),
        "vwap_reset_hour_utc": trial.suggest_int("vwap_reset_hour_utc", 0, 23),
        "wavetrend_n1": trial.suggest_int("wavetrend_n1", 5, 20),
        "wavetrend_n2": trial.suggest_int("wavetrend_n2", 10, 30),
        "wavetrend_ob_level": trial.suggest_float("wavetrend_ob_level", 1.5, 3.0),
        "delta_imbalance_threshold": trial.suggest_float("delta_imbalance_threshold", 0.3, 0.8),
        "absorption_volume_multiplier": trial.suggest_float("absorption_volume_multiplier", 1.2, 2.5),
        "absorption_range_multiplier": trial.suggest_float("absorption_range_multiplier", 0.4, 0.8),
        "volume_lookback": trial.suggest_int("volume_lookback", 10, 30),
        "atr_trail_length": trial.suggest_int("atr_trail_length", 10, 20),
        "atr_trail_multiplier": trial.suggest_float("atr_trail_multiplier", 1.0, 4.0),
        "min_pullback_bars": trial.suggest_int("min_pullback_bars", 2, 8),
        "max_loss_per_trade_dollars": trial.suggest_float("max_loss_per_trade_dollars", 75.0, 250.0),
        "max_daily_loss_dollars": trial.suggest_float("max_daily_loss_dollars", 150.0, 600.0),
        "max_consecutive_losses": trial.suggest_int("max_consecutive_losses", 2, 8),
        "max_drawdown_pct": trial.suggest_float("max_drawdown_pct", 2.0, 10.0),
    }


def optimized_param_names() -> list[str]:
    return list(sample_trial_params(_ParamNameTrial()).keys())


class _ParamNameTrial:
    def suggest_int(self, name: str, low: int, high: int) -> int:
        return low

    def suggest_float(self, name: str, low: float, high: float) -> float:
        return low
