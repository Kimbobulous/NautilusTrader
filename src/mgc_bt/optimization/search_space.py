from __future__ import annotations

from typing import Any

import optuna


PARAM_SPECS: dict[str, dict[str, Any]] = {
    "supertrend_atr_length": {"type": "int", "low": 5, "high": 20},
    "supertrend_factor": {"type": "float", "low": 1.5, "high": 5.0},
    "supertrend_training_period": {"type": "int", "low": 50, "high": 200},
    "vwap_reset_hour_utc": {"type": "int", "low": 0, "high": 23},
    "wavetrend_n1": {"type": "int", "low": 5, "high": 20},
    "wavetrend_n2": {"type": "int", "low": 10, "high": 30},
    "wavetrend_ob_level": {"type": "float", "low": 1.5, "high": 3.0},
    "delta_imbalance_threshold": {"type": "float", "low": 0.3, "high": 0.8},
    "absorption_volume_multiplier": {"type": "float", "low": 1.2, "high": 2.5},
    "absorption_range_multiplier": {"type": "float", "low": 0.4, "high": 0.8},
    "volume_lookback": {"type": "int", "low": 10, "high": 30},
    "atr_trail_length": {"type": "int", "low": 10, "high": 20},
    "atr_trail_multiplier": {"type": "float", "low": 1.0, "high": 4.0},
    "min_pullback_bars": {"type": "int", "low": 2, "high": 8},
    "max_loss_per_trade_dollars": {"type": "float", "low": 75.0, "high": 250.0},
    "max_daily_loss_dollars": {"type": "float", "low": 150.0, "high": 600.0},
    "max_consecutive_losses": {"type": "int", "low": 2, "high": 8},
    "max_drawdown_pct": {"type": "float", "low": 2.0, "high": 10.0},
}


def sample_trial_params(trial: optuna.trial.Trial) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name, spec in PARAM_SPECS.items():
        if spec["type"] == "int":
            params[name] = trial.suggest_int(name, spec["low"], spec["high"])
        else:
            params[name] = trial.suggest_float(name, spec["low"], spec["high"])
    return params


def optimized_param_names() -> list[str]:
    return list(sample_trial_params(_ParamNameTrial()).keys())


def parameter_spec(name: str) -> dict[str, Any]:
    return dict(PARAM_SPECS[name])


class _ParamNameTrial:
    def suggest_int(self, name: str, low: int, high: int) -> int:
        return low

    def suggest_float(self, name: str, low: float, high: float) -> float:
        return low
