from __future__ import annotations

from pathlib import Path
import csv

from mgc_bt.optimization.analytics import build_parameter_sensitivity_rows
from mgc_bt.optimization.analytics import write_parameter_sensitivity_csv


def test_parameter_sensitivity_uses_bucketed_sharpe_range(tmp_path: Path) -> None:
    ranked_rows = []
    for index in range(5):
        ranked_rows.append(
            {
                "objective_score": float(index),
                "sharpe_ratio": float(index) + 0.5,
                "param_supertrend_factor": 1.5 + index,
                "param_supertrend_atr_length": 5 + index,
                "param_supertrend_training_period": 50 + index,
                "param_vwap_reset_hour_utc": index,
                "param_wavetrend_n1": 10 + index,
                "param_wavetrend_n2": 21 + index,
                "param_wavetrend_ob_level": 2.0 + index,
                "param_delta_imbalance_threshold": 0.3 + index,
                "param_absorption_volume_multiplier": 1.2 + index,
                "param_absorption_range_multiplier": 0.4 + index,
                "param_volume_lookback": 20 + index,
                "param_atr_trail_length": 14 + index,
                "param_atr_trail_multiplier": 2.0 + index,
                "param_min_pullback_bars": 2 + index,
                "param_max_loss_per_trade_dollars": 100 + index,
                "param_max_daily_loss_dollars": 300 + index,
                "param_max_consecutive_losses": 3 + index,
                "param_max_drawdown_pct": 5 + index,
            },
        )
    rows = build_parameter_sensitivity_rows(ranked_rows)
    factor_row = next(item for item in rows if item["parameter_name"] == "supertrend_factor")
    assert "sharpe_range_across_buckets" in factor_row
    assert "correlation_with_objective" in factor_row

    output = write_parameter_sensitivity_csv(tmp_path, ranked_rows)
    with output.open("r", encoding="utf-8", newline="") as handle:
        written_rows = list(csv.DictReader(handle))
    assert written_rows
    assert set(written_rows[0].keys()) == {
        "parameter_name",
        "correlation_with_objective",
        "sharpe_range_across_buckets",
        "most_sensitive",
    }
