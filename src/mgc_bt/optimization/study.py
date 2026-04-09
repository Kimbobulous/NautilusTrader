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
from mgc_bt.optimization.monte_carlo import run_monte_carlo_analysis
from mgc_bt.optimization.objective import TrialEvaluator
from mgc_bt.optimization.results import create_optimization_run_dir
from mgc_bt.optimization.results import failed_trial_rows
from mgc_bt.optimization.results import ranked_trial_rows
from mgc_bt.optimization.results import refresh_latest_results
from mgc_bt.optimization.results import write_monte_carlo_artifacts
from mgc_bt.optimization.results import write_stability_artifacts
from mgc_bt.optimization.results import write_walk_forward_artifacts
from mgc_bt.optimization.results import write_optimization_manifest
from mgc_bt.optimization.results import write_optimization_analytics
from mgc_bt.optimization.results import write_failed_trials_json
from mgc_bt.optimization.results import write_optimization_run_config
from mgc_bt.optimization.results import write_optimization_summary_json
from mgc_bt.optimization.results import write_ranked_results_csv
from mgc_bt.optimization.storage import optimization_storage_path
from mgc_bt.optimization.storage import optimization_storage_url
from mgc_bt.optimization.stability import run_stability_analysis
from mgc_bt.optimization.walk_forward import run_walk_forward_optimization


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
    walk_forward: bool = False,
    final_test: bool = False,
    monte_carlo: bool = False,
    stability: bool = False,
    skip_monte_carlo: bool = False,
    skip_stability: bool = False,
) -> dict[str, Any]:
    out = output or sys.stdout
    if final_test and not walk_forward:
        raise ValueError("--final-test requires --walk-forward so the protected six-month test window stays hidden from the default optimize flow.")
    if final_test:
        out.write("Warning: final test window will be evaluated and can no longer be treated as untouched.\n")
        out.flush()

    analysis_flags = _resolve_analysis_flags(
        walk_forward=walk_forward,
        final_test=final_test,
        monte_carlo=monte_carlo,
        stability=stability,
        skip_monte_carlo=skip_monte_carlo,
        skip_stability=skip_stability,
    )
    final_test_window = _final_test_window(settings)
    if walk_forward:
        return _run_walk_forward_branch(
            settings,
            study_name=study_name,
            max_trials=max_trials,
            refresh_latest=refresh_latest,
            output=out,
            final_test=final_test,
            analysis_flags=analysis_flags,
            final_test_window=final_test_window,
        )
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
        _attach_phase_six_metadata(summary, analysis_flags, final_test_window)
        summary_path = write_optimization_summary_json(run_dir, summary)
        run_config_path = write_optimization_run_config(
            settings,
            run_dir,
            {},
            analysis_flags=analysis_flags,
            final_test_window=final_test_window,
        )
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
            "analysis_flags": analysis_flags,
            "monte_carlo_status": _analysis_status(
                enabled=analysis_flags["monte_carlo_enabled"],
                skipped_by_flag=skip_monte_carlo,
            ),
            "stability_status": _analysis_status(
                enabled=analysis_flags["stability_enabled"],
                skipped_by_flag=skip_stability,
            ),
        }

    best_trial = study.best_trial
    best_params = dict(best_trial.params)
    in_sample_result = rerun_best_in_sample(settings, best_params, run_dir=(run_dir / "best_run").as_posix())
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
    _attach_phase_six_metadata(summary, analysis_flags, final_test_window)
    summary_path = write_optimization_summary_json(run_dir, summary)
    run_config_path = write_optimization_run_config(
        settings,
        run_dir,
        best_params,
        analysis_flags=analysis_flags,
        final_test_window=final_test_window,
    )
    monte_carlo_paths = None
    monte_carlo_status = _analysis_status(
        enabled=analysis_flags["monte_carlo_enabled"],
        skipped_by_flag=skip_monte_carlo,
    )
    if analysis_flags["monte_carlo_enabled"]:
        trade_log = _select_trade_log_for_monte_carlo(
            walk_forward_trade_log=None,
            holdout_result=holdout_result,
            in_sample_result=in_sample_result,
        )
        monte_carlo_result = run_monte_carlo_analysis(
            trade_log,
            simulations=settings.monte_carlo.simulations,
            seed=settings.optimization.seed + settings.monte_carlo.random_seed_offset,
            percentiles=settings.monte_carlo.percentile_points,
            confidence_level=settings.monte_carlo.confidence_level,
        )
        monte_carlo_paths = write_monte_carlo_artifacts(run_dir, monte_carlo_result)
    stability_paths = None
    stability_status = _analysis_status(
        enabled=analysis_flags["stability_enabled"],
        skipped_by_flag=skip_stability,
    )
    if analysis_flags["stability_enabled"]:
        stability_result = run_stability_analysis(
            settings=settings,
            study=study,
            best_params=best_params,
            evaluation_context={
                "mode": "holdout",
                "start": settings.optimization.holdout_start,
                "end": settings.optimization.holdout_end,
            },
        )
        stability_paths = write_stability_artifacts(run_dir, stability_result)
    optimization_analytics_files = []
    try:
        optimization_analytics_files = write_optimization_analytics(
            run_dir,
            ranked_rows=ranked_rows,
            best_run_result=in_sample_result,
        )
    except Exception as exc:
        out.write(f"Warning: optimization analytics generation failed: {exc}\n")
        out.flush()
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
        "analysis_flags": analysis_flags,
        "monte_carlo_summary_path": monte_carlo_paths["summary_path"] if monte_carlo_paths else None,
        "monte_carlo_status": monte_carlo_status,
        "stability_summary_path": stability_paths["summary_path"] if stability_paths else None,
        "stability_status": stability_status,
        "analytics_dir": run_dir / "analytics" if optimization_analytics_files else None,
    }


def _run_walk_forward_branch(
    settings: Settings,
    *,
    study_name: str | None,
    max_trials: int | None,
    refresh_latest: bool,
    output: TextIO,
    final_test: bool,
    analysis_flags: dict[str, bool],
    final_test_window: dict[str, str],
) -> dict[str, Any]:
    effective_study_name = study_name or settings.optimization.study_name
    effective_max_trials = max_trials or settings.optimization.max_trials
    storage_path = optimization_storage_path(settings)
    run_dir = create_optimization_run_dir(settings)
    started_at = time.perf_counter()
    walk_forward_run = run_walk_forward_optimization(
        settings,
        study_name=effective_study_name,
        max_trials=effective_max_trials,
        output=output,
        final_test=final_test,
    )
    aggregate = walk_forward_run["aggregate"]
    window_results = walk_forward_run["window_results"]
    walk_forward_summary = {
        "schema_version": 1,
        "run_type": "optimize",
        "analysis_type": "walk_forward",
        "completed_window_count": aggregate.completed_window_count,
        "skipped_window_count": aggregate.skipped_window_count,
        "inconclusive_window_count": aggregate.inconclusive_window_count,
        "aggregated_oos_sharpe": aggregate.aggregated_oos_sharpe,
        "aggregated_oos_total_pnl": aggregate.aggregated_oos_total_pnl,
        "aggregated_equity_curve": aggregate.aggregated_equity_curve,
        "selected_params": aggregate.selected_params,
        "status": aggregate.status,
        "final_test_executed": walk_forward_run["final_test_result"] is not None,
    }
    artifact_paths = write_walk_forward_artifacts(
        run_dir,
        walk_forward_summary,
        [_window_result_row(item) for item in window_results],
        final_test_result=walk_forward_run["final_test_result"],
    )
    write_failed_trials_json(run_dir, walk_forward_run["failed_trials"])
    summary = {
        "study_name": effective_study_name,
        "seed": settings.optimization.seed,
        "completed_trials": sum(item.training_completed_trials for item in window_results),
        "failed_trials": len(walk_forward_run["failed_trials"]),
        "runtime_seconds": round(time.perf_counter() - started_at, 4),
        "storage_path": storage_path.as_posix(),
        "best_params": aggregate.selected_params[-1] if aggregate.selected_params else {},
        "best_value": aggregate.aggregated_oos_sharpe,
        "walk_forward_summary_path": artifact_paths["summary_path"].as_posix(),
        "walk_forward_window_results_path": artifact_paths["window_results_path"].as_posix(),
        "walk_forward_counts": {
            "completed": aggregate.completed_window_count,
            "skipped": aggregate.skipped_window_count,
            "inconclusive": aggregate.inconclusive_window_count,
        },
        "overfit_warning": False,
    }
    monte_carlo_paths = None
    monte_carlo_status = _analysis_status(
        enabled=analysis_flags["monte_carlo_enabled"],
        skipped_by_flag=False,
    )
    if analysis_flags["monte_carlo_enabled"]:
        monte_carlo_result = run_monte_carlo_analysis(
            aggregate.aggregated_trade_log,
            simulations=settings.monte_carlo.simulations,
            seed=settings.optimization.seed + settings.monte_carlo.random_seed_offset,
            percentiles=settings.monte_carlo.percentile_points,
            confidence_level=settings.monte_carlo.confidence_level,
        )
        monte_carlo_paths = write_monte_carlo_artifacts(run_dir, monte_carlo_result)
    stability_paths = None
    stability_status = _analysis_status(
        enabled=analysis_flags["stability_enabled"],
        skipped_by_flag=False,
    )
    if analysis_flags["stability_enabled"]:
        stability_result = run_stability_analysis(
            settings=settings,
            study=_study_from_trials(walk_forward_run.get("training_trials", []), settings.optimization.direction),
            best_params=_strip_window_index(aggregate.selected_params[-1]) if aggregate.selected_params else {},
            evaluation_context={
                "mode": "walk_forward",
                "windows": [
                    {"start": item.test_start, "end": item.test_end}
                    for item in window_results
                    if item.status != "skipped"
                ],
                "min_test_trades": settings.walk_forward.min_test_trades,
            },
        )
        stability_paths = write_stability_artifacts(run_dir, stability_result)
    optimization_analytics_files = []
    try:
        if aggregate.selected_params:
            best_window_result = next(
                (item.test_result for item in window_results if not item.inconclusive and item.test_result is not None),
                None,
            )
        else:
            best_window_result = None
        optimization_analytics_files = write_optimization_analytics(
            run_dir,
            ranked_rows=[],
            best_run_result=best_window_result,
        )
    except Exception as exc:
        output.write(f"Warning: optimization analytics generation failed: {exc}\n")
        output.flush()
    _attach_phase_six_metadata(summary, analysis_flags, final_test_window)
    summary_path = write_optimization_summary_json(run_dir, summary)
    run_config_path = write_optimization_run_config(
        settings,
        run_dir,
        aggregate.selected_params[-1] if aggregate.selected_params else {},
        analysis_flags=analysis_flags,
        final_test_window=final_test_window,
    )
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
        "completed_trials": summary["completed_trials"],
        "failed_trials": len(walk_forward_run["failed_trials"]),
        "best_params": summary["best_params"],
        "best_value": aggregate.aggregated_oos_sharpe,
        "walk_forward_summary_path": artifact_paths["summary_path"],
        "walk_forward_counts": summary["walk_forward_counts"],
        "holdout_summary_path": artifact_paths.get("final_test_summary_path"),
        "holdout_plot_path": artifact_paths.get("final_test_plot_path"),
        "overfit_warning": False,
        "analysis_flags": analysis_flags,
        "monte_carlo_summary_path": monte_carlo_paths["summary_path"] if monte_carlo_paths else None,
        "monte_carlo_status": monte_carlo_status,
        "stability_summary_path": stability_paths["summary_path"] if stability_paths else None,
        "stability_status": stability_status,
        "analytics_dir": run_dir / "analytics" if optimization_analytics_files else None,
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


def _resolve_analysis_flags(
    *,
    walk_forward: bool,
    final_test: bool,
    monte_carlo: bool,
    stability: bool,
    skip_monte_carlo: bool,
    skip_stability: bool,
) -> dict[str, bool]:
    monte_carlo_enabled = (walk_forward and not skip_monte_carlo) or (monte_carlo and not skip_monte_carlo)
    stability_enabled = (walk_forward and not skip_stability) or (stability and not skip_stability)
    return {
        "walk_forward_enabled": walk_forward,
        "final_test_requested": final_test,
        "monte_carlo_enabled": monte_carlo_enabled,
        "stability_enabled": stability_enabled,
    }


def _final_test_window(settings: Settings) -> dict[str, str]:
    from pandas import DateOffset
    from pandas import Timestamp

    holdout_end = Timestamp(settings.optimization.holdout_end, tz="UTC")
    final_start = holdout_end - DateOffset(months=settings.walk_forward.final_test_months)
    return {
        "start": final_start.isoformat(),
        "end": holdout_end.isoformat(),
    }


def _attach_phase_six_metadata(
    summary: dict[str, Any],
    analysis_flags: dict[str, bool],
    final_test_window: dict[str, str],
) -> None:
    if not any(analysis_flags.values()):
        return
    summary["analysis_flags"] = analysis_flags
    summary.update(analysis_flags)
    summary["final_test_window"] = final_test_window


def _window_result_row(result: Any) -> dict[str, Any]:
    return {
        "window_index": result.window_index,
        "train_start": result.train_start,
        "train_end": result.train_end,
        "validation_start": result.validation_start,
        "validation_end": result.validation_end,
        "test_start": result.test_start,
        "test_end": result.test_end,
        "status": result.status,
        "skipped_reason": result.skipped_reason,
        "inconclusive": result.inconclusive,
        "training_bar_count": result.training_bar_count,
        "training_completed_trials": result.training_completed_trials,
        "training_sharpe": result.training_sharpe,
        "validation_sharpe": result.validation_sharpe,
        "validation_max_drawdown_pct": result.validation_max_drawdown_pct,
        "validation_total_pnl": result.validation_total_pnl,
        "test_sharpe": result.test_sharpe,
        "test_total_pnl": result.test_total_pnl,
        "test_total_trades": result.test_total_trades,
        "test_bar_count": result.test_bar_count,
        "selected_params": result.selected_params,
    }


def _analysis_status(*, enabled: bool, skipped_by_flag: bool) -> str:
    if skipped_by_flag:
        return "skipped_by_flag"
    if enabled:
        return "completed"
    return "not_requested"


def _select_trade_log_for_monte_carlo(
    *,
    walk_forward_trade_log: list[dict[str, Any]] | None,
    holdout_result: dict[str, Any] | None,
    in_sample_result: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if walk_forward_trade_log:
        return walk_forward_trade_log
    if holdout_result is not None and holdout_result.get("trade_log"):
        return list(holdout_result["trade_log"])
    if in_sample_result is not None and in_sample_result.get("trade_log"):
        return list(in_sample_result["trade_log"])
    return []


def _study_from_trials(
    trials: list[optuna.trial.FrozenTrial],
    direction: str,
) -> optuna.study.Study:
    study = optuna.create_study(direction=direction)
    for trial in trials:
        study.add_trial(trial)
    return study


def _strip_window_index(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if key != "window_index"}
