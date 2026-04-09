from __future__ import annotations

from typing import Any

import numpy as np


def run_monte_carlo_analysis(
    trade_log: list[dict[str, Any]],
    *,
    simulations: int,
    seed: int,
    percentiles: tuple[int, ...] | list[int],
    confidence_level: float,
) -> dict[str, Any]:
    sample_size = len(trade_log)
    if sample_size < 2:
        return {
            "schema_version": 1,
            "run_type": "optimize",
            "analysis_type": "monte_carlo",
            "status": "skipped",
            "skipped_reason": "insufficient_trades",
            "simulations": simulations,
            "sample_size": sample_size,
            "percentiles": list(percentiles),
        }

    pnls = np.array([float(item.get("realized_pnl", 0.0)) for item in trade_log], dtype=float)
    rng = np.random.default_rng(seed)
    percentile_points = [int(value) for value in percentiles]

    actual_sharpe = _sequence_sharpe(pnls)
    permutation_sharpes: list[float] = []
    permutation_pnls: list[float] = []
    for _ in range(simulations):
        permuted = rng.permutation(pnls)
        permutation_sharpes.append(_sequence_sharpe(permuted))
        permutation_pnls.append(float(permuted.sum()))
    permutation_p_value = _p_value(permutation_sharpes, actual_sharpe)

    bootstrap_sharpes: list[float] = []
    bootstrap_pnls: list[float] = []
    bootstrap_paths: list[np.ndarray] = []
    for _ in range(simulations):
        indices = rng.integers(0, sample_size, size=sample_size)
        sample = pnls[indices]
        bootstrap_sharpes.append(_sequence_sharpe(sample))
        bootstrap_pnls.append(float(sample.sum()))
        bootstrap_paths.append(np.cumsum(sample))
    bootstrap_p_value = float(sum(value <= 0.0 for value in bootstrap_sharpes) / len(bootstrap_sharpes))

    lower_tail = max(int(round((1.0 - confidence_level) * 100)), 0)
    permutation_summary = _method_summary(
        method="permutation",
        simulations=simulations,
        sample_size=sample_size,
        sharpe_values=permutation_sharpes,
        pnl_values=permutation_pnls,
        percentile_points=percentile_points,
        p_value=permutation_p_value,
        pass_95=permutation_p_value <= (1.0 - confidence_level),
    )
    bootstrap_summary = _method_summary(
        method="bootstrap",
        simulations=simulations,
        sample_size=sample_size,
        sharpe_values=bootstrap_sharpes,
        pnl_values=bootstrap_pnls,
        percentile_points=percentile_points,
        p_value=bootstrap_p_value,
        pass_95=bootstrap_p_value <= (1.0 - confidence_level),
    )
    confidence_bands = _confidence_bands(bootstrap_paths, percentile_points)
    return {
        "schema_version": 1,
        "run_type": "optimize",
        "analysis_type": "monte_carlo",
        "status": "completed",
        "simulations": simulations,
        "sample_size": sample_size,
        "confidence_level": confidence_level,
        "percentiles": percentile_points,
        "lower_tail_percentile": lower_tail,
        "permutation": permutation_summary,
        "bootstrap": bootstrap_summary,
        "confidence_bands": confidence_bands,
    }


def _method_summary(
    *,
    method: str,
    simulations: int,
    sample_size: int,
    sharpe_values: list[float],
    pnl_values: list[float],
    percentile_points: list[int],
    p_value: float,
    pass_95: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_type": "optimize",
        "analysis_type": "monte_carlo",
        "method": method,
        "status": "completed",
        "simulations": simulations,
        "sample_size": sample_size,
        "p_value": round(float(p_value), 6),
        "percentiles": {
            "sharpe_ratio": {str(point): round(float(np.percentile(sharpe_values, point)), 6) for point in percentile_points},
            "final_pnl": {str(point): round(float(np.percentile(pnl_values, point)), 6) for point in percentile_points},
        },
        "pass_95": bool(pass_95),
    }


def _confidence_bands(paths: list[np.ndarray], percentile_points: list[int]) -> list[dict[str, Any]]:
    matrix = np.vstack(paths)
    rows: list[dict[str, Any]] = []
    for index in range(matrix.shape[1]):
        row: dict[str, Any] = {"trade_index": index + 1}
        for point in percentile_points:
            row[f"p{point}"] = round(float(np.percentile(matrix[:, index], point)), 6)
        rows.append(row)
    return rows


def _p_value(distribution: list[float], actual_value: float) -> float:
    if not distribution:
        return 1.0
    return float(sum(value >= actual_value for value in distribution) / len(distribution))


def _sequence_sharpe(values: np.ndarray) -> float:
    if values.size < 2:
        return 0.0
    equity = np.cumsum(values)
    returns = np.diff(equity)
    std = float(np.std(returns, ddof=1)) if returns.size > 1 else 0.0
    if std == 0.0:
        return 0.0
    return float(np.mean(returns) / std)
