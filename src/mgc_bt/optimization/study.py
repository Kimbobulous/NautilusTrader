from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import sys
import time
from typing import Any, TextIO

import optuna

from mgc_bt.config import Settings
from mgc_bt.optimization.export import export_best_run
from mgc_bt.optimization.export import export_top_10
from mgc_bt.optimization.export import rerun_best_in_sample
from mgc_bt.optimization.export import rerun_holdout
from mgc_bt.optimization.objective import TrialEvaluator
from mgc_bt.optimization.results import create_optimization_run_dir
from mgc_bt.optimization.results import failed_trial_rows
from mgc_bt.optimization.results import ranked_trial_rows
from mgc_bt.optimization.results import refresh_latest_results
from mgc_bt.optimization.results import write_optimization_manifest
from mgc_bt.optimization.results import write_failed_trials_json
from mgc_bt.optimization.results import write_optimization_run_config
from mgc_bt.optimization.results import write_optimization_summary_json
from mgc_bt.optimization.results import write_ranked_results_csv
from mgc_bt.optimization.storage import optimization_storage_path
from mgc_bt.optimization.storage import optimization_storage_url


@dataclass
class OptimizationRuntime:
    output: TextIO
    start_time: float
    max_trials: int
    max_runtime_seconds: int


def run_optimization(
    settings: Settings,
    *,
    resume: bool = False,
    study_name: str | None = None,
    max_trials: int | None = None,
    refresh_latest: bool = True,
    output: TextIO | None = None,
) -> dict[str, Any]:
    out = output or sys.stdout
    effective_study_name = study_name or settings.optimization.study_name
    effective_max_trials = max_trials or settings.optimization.max_trials
    storage_path = optimization_storage_path(settings)
    storage_url = optimization_storage_url(settings)
    sampler = optuna.samplers.TPESampler(seed=settings.optimization.seed)
    study = optuna.create_study(
        study_name=effective_study_name,
        direction=settings.optimization.direction,
        sampler=sampler,
        storage=storage_url,
        load_if_exists=resume,
    )

    runtime = OptimizationRuntime(
        output=out,
        start_time=time.perf_counter(),
        max_trials=effective_max_trials,
        max_runtime_seconds=settings.optimization.max_runtime_seconds,
    )
    evaluator = TrialEvaluator(settings)
    callbacks = [
        _progress_callback(runtime),
        _early_stop_callback(
            window=settings.optimization.early_stop_window,
            min_improvement=settings.optimization.early_stop_min_improvement,
            output=out,
        ),
    ]
    study.optimize(
        evaluator,
        n_trials=effective_max_trials,
        timeout=settings.optimization.max_runtime_seconds,
        callbacks=callbacks,
        catch=(Exception,),
    )

    run_dir = create_optimization_run_dir(settings)
    ranked_rows = ranked_trial_rows(study)
    failed_rows = failed_trial_rows(study)
    write_ranked_results_csv(run_dir, ranked_rows)
    write_failed_trials_json(run_dir, failed_rows)

    if not ranked_rows:
        summary = {
            "study_name": effective_study_name,
            "seed": settings.optimization.seed,
            "completed_trials": 0,
            "failed_trials": len(failed_rows),
            "runtime_seconds": round(time.perf_counter() - runtime.start_time, 4),
            "storage_path": storage_path.as_posix(),
            "best_params": {},
            "best_value": None,
        }
        summary_path = write_optimization_summary_json(run_dir, summary)
        run_config_path = write_optimization_run_config(settings, run_dir, {})
        write_optimization_manifest(run_dir, latest_refreshed=refresh_latest)
        latest_dir = refresh_latest_results(run_dir) if refresh_latest else None
        return {
            "run_dir": run_dir,
            "latest_dir": latest_dir,
            "summary_path": summary_path,
            "run_config_path": run_config_path,
            "storage_path": storage_path,
            "study_name": effective_study_name,
            "seed": settings.optimization.seed,
            "completed_trials": 0,
            "failed_trials": len(failed_rows),
            "best_params": {},
            "best_value": None,
            "overfit_warning": False,
        }

    best_trial = study.best_trial
    best_params = dict(best_trial.params)
    in_sample_result = rerun_best_in_sample(settings, best_params)
    holdout_result = rerun_holdout(settings, best_params)
    best_bundle = export_best_run(settings, run_dir, in_sample_result, holdout_result)
    top_10_outputs = export_top_10(
        settings,
        run_dir,
        sorted(
            (trial for trial in study.trials if trial.state == optuna.trial.TrialState.COMPLETE),
            key=lambda trial: (
                -(float(trial.value) if trial.value is not None else float("-inf")),
                -(float(trial.user_attrs.get("sharpe_ratio") or float("-inf"))),
                float(trial.user_attrs.get("max_drawdown_pct") or float("inf")),
            ),
        ),
        best_trial.number,
    )
    overfit_warning = _is_overfit_warning(in_sample_result, holdout_result)

    summary = {
        "study_name": effective_study_name,
        "seed": settings.optimization.seed,
        "completed_trials": len(ranked_rows),
        "failed_trials": len(failed_rows),
        "runtime_seconds": round(time.perf_counter() - runtime.start_time, 4),
        "storage_path": storage_path.as_posix(),
        "best_params": best_params,
        "best_value": float(best_trial.value) if best_trial.value is not None else None,
        "best_trial_number": best_trial.number,
        "in_sample_window": {
            "start": settings.optimization.in_sample_start,
            "end": settings.optimization.in_sample_end,
        },
        "holdout_window": {
            "start": settings.optimization.holdout_start,
            "end": settings.optimization.holdout_end,
        },
        "best_metrics": {
            "sharpe_ratio": in_sample_result.get("sharpe_ratio"),
            "total_pnl": in_sample_result.get("total_pnl"),
            "win_rate": in_sample_result.get("win_rate"),
            "max_drawdown_pct": in_sample_result.get("max_drawdown_pct"),
            "total_trades": in_sample_result.get("total_trades"),
        },
        "holdout_metrics": {
            "sharpe_ratio": holdout_result.get("sharpe_ratio"),
            "total_pnl": holdout_result.get("total_pnl"),
            "win_rate": holdout_result.get("win_rate"),
            "max_drawdown_pct": holdout_result.get("max_drawdown_pct"),
            "total_trades": holdout_result.get("total_trades"),
        },
        "overfit_warning": overfit_warning,
    }
    summary_path = write_optimization_summary_json(run_dir, summary)
    run_config_path = write_optimization_run_config(settings, run_dir, best_params)
    write_optimization_manifest(run_dir, latest_refreshed=refresh_latest)
    latest_dir = refresh_latest_results(run_dir) if refresh_latest else None
    return {
        "run_dir": run_dir,
        "latest_dir": latest_dir,
        "summary_path": summary_path,
        "run_config_path": run_config_path,
        "storage_path": storage_path,
        "study_name": effective_study_name,
        "seed": settings.optimization.seed,
        "completed_trials": len(ranked_rows),
        "failed_trials": len(failed_rows),
        "best_params": best_params,
        "best_value": float(best_trial.value) if best_trial.value is not None else None,
        "best_trial_number": best_trial.number,
        "best_run_dir": best_bundle["directory"],
        "holdout_summary_path": best_bundle["holdout_summary_path"],
        "holdout_plot_path": best_bundle["holdout_plot_path"],
        "top_10_count": len(top_10_outputs),
        "overfit_warning": overfit_warning,
        "in_sample_result": in_sample_result,
        "holdout_result": holdout_result,
    }


def _progress_callback(runtime: OptimizationRuntime):
    def callback(study: optuna.study.Study, trial: optuna.trial.FrozenTrial) -> None:
        elapsed = time.perf_counter() - runtime.start_time
        completed = len(
            [
                item
                for item in study.trials
                if item.state in (optuna.trial.TrialState.COMPLETE, optuna.trial.TrialState.FAIL)
            ],
        )
        eta_seconds = _estimate_eta_seconds(
            elapsed=elapsed,
            completed=max(completed, 1),
            max_trials=runtime.max_trials,
            max_runtime_seconds=runtime.max_runtime_seconds,
        )
        best_trial = _best_trial_or_none(study)
        best_value = best_trial.value if best_trial is not None else None
        best_params = best_trial.params if best_trial is not None else {}
        runtime.output.write(
            "Trial "
            f"{trial.number + 1}/{runtime.max_trials} | "
            f"Best Sharpe: {_format_metric(best_value)} | "
            f"Best params: {best_params} | "
            f"ETA: {_format_duration(eta_seconds)}\n",
        )
        runtime.output.flush()

    return callback


def _early_stop_callback(window: int, min_improvement: float, output: TextIO):
    def callback(study: optuna.study.Study, trial: optuna.trial.FrozenTrial) -> None:
        completed = sorted(
            [item for item in study.trials if item.state == optuna.trial.TrialState.COMPLETE],
            key=lambda item: item.number,
        )
        if len(completed) < window:
            return
        best_history: list[float] = []
        running_best = float("-inf")
        for item in completed:
            running_best = max(running_best, float(item.value))
            best_history.append(running_best)
        improvement = best_history[-1] - best_history[-window]
        if improvement <= min_improvement:
            output.write(
                "Early stopping triggered: best objective improved by "
                f"{improvement:.4f} over the last {window} completed trials.\n",
            )
            output.flush()
            study.stop()

    return callback


def _estimate_eta_seconds(
    *,
    elapsed: float,
    completed: int,
    max_trials: int,
    max_runtime_seconds: int,
) -> float:
    average = elapsed / max(completed, 1)
    remaining_trials = max(max_trials - completed, 0)
    trial_eta = average * remaining_trials
    time_cap_remaining = max(max_runtime_seconds - elapsed, 0.0)
    if time_cap_remaining <= 0:
        return 0.0
    return min(trial_eta, time_cap_remaining)


def _format_duration(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _format_metric(value: Any) -> str:
    if value is None:
        return "n/a"
    numeric = float(value)
    if math.isnan(numeric):
        return "n/a"
    return f"{numeric:.4f}"


def _is_overfit_warning(in_sample_result: dict[str, Any], holdout_result: dict[str, Any]) -> bool:
    in_sample_sharpe = in_sample_result.get("sharpe_ratio")
    holdout_sharpe = holdout_result.get("sharpe_ratio")
    if in_sample_sharpe is None or holdout_sharpe is None:
        return False
    return float(in_sample_sharpe) - float(holdout_sharpe) > 0.3


def _best_trial_or_none(study: optuna.study.Study) -> optuna.trial.FrozenTrial | None:
    try:
        return study.best_trial
    except ValueError:
        return None
