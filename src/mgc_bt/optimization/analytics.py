from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import csv
import math
import statistics
from typing import Any

from mgc_bt.backtest.analytics import write_trade_breakdowns
from mgc_bt.optimization.search_space import optimized_param_names


def build_parameter_sensitivity_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sensitivities: list[dict[str, Any]] = []
    for name in optimized_param_names():
        column = f"param_{name}"
        values = [
            (float(row[column]), float(row["objective_score"]))
            for row in rows
            if row.get(column) not in (None, "") and row.get("objective_score") not in (None, "")
        ]
        if not values:
            sensitivities.append(
                {
                    "parameter_name": name,
                    "correlation_with_objective": 0.0,
                    "sharpe_range_across_buckets": 0.0,
                    "most_sensitive": False,
                },
            )
            continue
        sharpe_range = _bucket_sharpe_range(values, rows, column)
        correlation = _pearson([item[0] for item in values], [item[1] for item in values])
        sensitivities.append(
            {
                "parameter_name": name,
                "correlation_with_objective": round(correlation, 6),
                "sharpe_range_across_buckets": round(sharpe_range, 6),
                "most_sensitive": False,
            },
        )
    top_names = {
        row["parameter_name"]
        for row in sorted(
            sensitivities,
            key=lambda item: item["sharpe_range_across_buckets"],
            reverse=True,
        )[:3]
    }
    for row in sensitivities:
        row["most_sensitive"] = row["parameter_name"] in top_names
    return sensitivities


def write_parameter_sensitivity_csv(run_dir: Path, ranked_rows: list[dict[str, Any]]) -> Path:
    analytics_dir = run_dir / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    output_path = analytics_dir / "parameter_sensitivity.csv"
    rows = build_parameter_sensitivity_rows(ranked_rows)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "parameter_name",
            "correlation_with_objective",
            "sharpe_range_across_buckets",
            "most_sensitive",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return output_path


def write_optimization_trade_breakdowns(run_dir: Path, trades: list[dict[str, Any]]) -> list[Path]:
    analytics_dir = run_dir / "analytics"
    breakdowns_dir = analytics_dir / "breakdowns"
    breakdowns_dir.mkdir(parents=True, exist_ok=True)
    return write_trade_breakdowns(trades, breakdowns_dir)


def _bucket_sharpe_range(
    values: list[tuple[float, float]],
    rows: list[dict[str, Any]],
    column: str,
) -> float:
    parameter_values = [item[0] for item in values]
    minimum = min(parameter_values)
    maximum = max(parameter_values)
    if math.isclose(minimum, maximum):
        return 0.0
    width = (maximum - minimum) / 5.0
    bucket_scores: list[list[float]] = [[] for _ in range(5)]
    for row in rows:
        if row.get(column) in (None, "") or row.get("sharpe_ratio") in (None, ""):
            continue
        value = float(row[column])
        idx = min(int((value - minimum) / width), 4)
        bucket_scores[idx].append(float(row["sharpe_ratio"]))
    means = [statistics.mean(bucket) for bucket in bucket_scores if bucket]
    if not means:
        return 0.0
    return max(means) - min(means)


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or len(ys) < 2:
        return 0.0
    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=False))
    denominator_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denominator_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denominator_x == 0 or denominator_y == 0:
        return 0.0
    return numerator / (denominator_x * denominator_y)
