from __future__ import annotations

from typing import Any

import optuna
from optuna.importance import FanovaImportanceEvaluator

from mgc_bt.config import Settings
from mgc_bt.optimization.objective import evaluate_params
from mgc_bt.optimization.search_space import optimized_param_names
from mgc_bt.optimization.search_space import parameter_spec

HEATMAP_OFFSETS = [-20, -10, 0, 10, 20]
NEIGHBOR_OFFSETS = [-20, -10, 10, 20]


def run_stability_analysis(
    *,
    settings: Settings,
    study: optuna.study.Study,
    best_params: dict[str, Any],
    evaluation_context: dict[str, Any],
) -> dict[str, Any]:
    completed_trials = [trial for trial in study.trials if trial.state == optuna.trial.TrialState.COMPLETE]
    if len(completed_trials) < 2:
        return _skipped_result("insufficient_completed_trials")

    importances = optuna.importance.get_param_importances(
        study,
        evaluator=FanovaImportanceEvaluator(),
    )
    top_parameters = [name for name in importances.keys() if name in best_params][:2]
    if len(top_parameters) < 2:
        return _skipped_result("insufficient_completed_trials")

    heatmap_rows = _heatmap_rows(
        settings=settings,
        best_params=best_params,
        top_parameters=top_parameters,
        evaluation_context=evaluation_context,
    )
    neighborhood = _neighborhood_robustness(
        settings=settings,
        best_params=best_params,
        evaluation_context=evaluation_context,
    )
    return {
        "schema_version": 1,
        "run_type": "optimize",
        "analysis_type": "stability",
        "status": "completed",
        "top_parameters": top_parameters,
        "param_importance": importances,
        "heatmap_rows": heatmap_rows,
        "neighborhood": neighborhood,
        "robustness_score": neighborhood["robustness_score"],
        "robust": neighborhood["robust"],
    }


def _heatmap_rows(
    *,
    settings: Settings,
    best_params: dict[str, Any],
    top_parameters: list[str],
    evaluation_context: dict[str, Any],
) -> list[dict[str, Any]]:
    first, second = top_parameters
    rows: list[dict[str, Any]] = []
    for first_offset in HEATMAP_OFFSETS:
        for second_offset in HEATMAP_OFFSETS:
            candidate = dict(best_params)
            candidate[first] = _perturb_param(first, best_params[first], first_offset)
            candidate[second] = _perturb_param(second, best_params[second], second_offset)
            result = _evaluate_context(settings, candidate, evaluation_context)
            rows.append(
                {
                    "parameter_x": first,
                    "parameter_y": second,
                    "offset_x_pct": first_offset,
                    "offset_y_pct": second_offset,
                    "value_x": candidate[first],
                    "value_y": candidate[second],
                    "sharpe_ratio": result["sharpe_ratio"],
                    "total_pnl": result["total_pnl"],
                    "max_drawdown_pct": result["max_drawdown_pct"],
                },
            )
    return rows


def _neighborhood_robustness(
    *,
    settings: Settings,
    best_params: dict[str, Any],
    evaluation_context: dict[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    passing = 0
    total = 0
    for name in optimized_param_names():
        if name not in best_params:
            continue
        for offset in NEIGHBOR_OFFSETS:
            candidate = dict(best_params)
            candidate[name] = _perturb_param(name, best_params[name], offset)
            result = _evaluate_context(settings, candidate, evaluation_context)
            sharpe_ratio = float(result.get("sharpe_ratio") or 0.0)
            passed = sharpe_ratio > 0.5
            total += 1
            passing += int(passed)
            rows.append(
                {
                    "parameter": name,
                    "offset_pct": offset,
                    "value": candidate[name],
                    "sharpe_ratio": sharpe_ratio,
                    "passed": passed,
                },
            )
    robustness_score = round((passing / total) * 100.0, 4) if total else 0.0
    return {
        "neighbors": rows,
        "passing_neighbors": passing,
        "total_neighbors": total,
        "robustness_score": robustness_score,
        "robust": robustness_score >= 70.0,
    }


def _evaluate_context(
    settings: Settings,
    params: dict[str, Any],
    evaluation_context: dict[str, Any],
) -> dict[str, Any]:
    mode = evaluation_context["mode"]
    if mode == "holdout":
        return evaluate_params(
            settings,
            params,
            start_date=evaluation_context["start"],
            end_date=evaluation_context["end"],
            evaluation_window="stability_holdout",
        )
    if mode == "walk_forward":
        results = []
        for window in evaluation_context["windows"]:
            result = evaluate_params(
                settings,
                params,
                start_date=window["start"],
                end_date=window["end"],
                evaluation_window="stability_walk_forward",
            )
            if int(result.get("total_trades", 0)) < evaluation_context["min_test_trades"]:
                continue
            results.append(result)
        return _aggregate_context_results(results)
    raise ValueError(f"Unsupported stability evaluation mode: {mode}")


def _aggregate_context_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {"sharpe_ratio": 0.0, "total_pnl": 0.0, "max_drawdown_pct": 0.0}
    weight_sum = sum(max(len(result.get("equity_curve", [])), 1) for result in results)
    weighted_sharpe = sum(
        float(result.get("sharpe_ratio") or 0.0) * max(len(result.get("equity_curve", [])), 1)
        for result in results
    ) / weight_sum
    return {
        "sharpe_ratio": round(weighted_sharpe, 6),
        "total_pnl": round(sum(float(result.get("total_pnl") or 0.0) for result in results), 6),
        "max_drawdown_pct": max(float(result.get("max_drawdown_pct") or 0.0) for result in results),
    }


def _perturb_param(name: str, baseline: Any, offset_pct: int) -> Any:
    spec = parameter_spec(name)
    raw_value = float(baseline) * (1.0 + (offset_pct / 100.0))
    clamped = min(max(raw_value, spec["low"]), spec["high"])
    if spec["type"] == "int":
        return int(round(clamped))
    return round(float(clamped), 6)


def _skipped_result(reason: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_type": "optimize",
        "analysis_type": "stability",
        "status": "skipped",
        "skipped_reason": reason,
        "top_parameters": [],
        "param_importance": {},
        "heatmap_rows": [],
        "neighborhood": {
            "neighbors": [],
            "passing_neighbors": 0,
            "total_neighbors": 0,
            "robustness_score": 0.0,
            "robust": False,
        },
        "robustness_score": 0.0,
        "robust": False,
    }
