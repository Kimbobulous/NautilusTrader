from __future__ import annotations

from typing import Any

import optuna

from mgc_bt.backtest.runner import run_backtest
from mgc_bt.config import Settings
from mgc_bt.optimization.results import write_best_run_bundle
from mgc_bt.optimization.results import write_best_run_config
from mgc_bt.optimization.results import write_holdout_files
from mgc_bt.optimization.results import write_top_trial_bundle


def rerun_best_in_sample(settings: Settings, best_params: dict[str, Any], *, run_dir: str | None = None) -> dict[str, Any]:
    run_params = dict(best_params)
    run_params.update(
        {
            "instrument_id": None,
            "start_date": settings.optimization.in_sample_start,
            "end_date": settings.optimization.in_sample_end,
        },
    )
    if run_dir is not None:
        run_params["_run_dir"] = run_dir
    return run_backtest(settings, run_params)


def rerun_holdout(settings: Settings, best_params: dict[str, Any]) -> dict[str, Any]:
    run_params = dict(best_params)
    run_params.update(
        {
            "instrument_id": None,
            "start_date": settings.optimization.holdout_start,
            "end_date": settings.optimization.holdout_end,
        },
    )
    return run_backtest(settings, run_params)


def export_best_run(settings: Settings, run_dir, in_sample_result: dict[str, Any], holdout_result: dict[str, Any]) -> dict[str, Any]:
    best_dir = run_dir / "best_run"
    bundle_paths = write_best_run_bundle(settings, in_sample_result, best_dir)
    config_path = write_best_run_config(settings, in_sample_result, best_dir)
    holdout_paths = write_holdout_files(best_dir, holdout_result)
    return {
        "directory": best_dir,
        **bundle_paths,
        "config_path": config_path,
        "holdout_summary_path": holdout_paths["summary_path"],
        "holdout_plot_path": holdout_paths["plot_path"],
    }


def export_top_10(settings: Settings, run_dir, ranked_trials: list[optuna.trial.FrozenTrial], best_trial_number: int) -> list[dict[str, Any]]:
    top_root = run_dir / "top_10"
    top_root.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, Any]] = []
    exported = 0
    for trial in ranked_trials:
        if trial.number == best_trial_number:
            continue
        if exported >= 10:
            break
        result = rerun_best_in_sample(settings, trial.params)
        trial_dir = top_root / f"rank_{exported + 2:02d}_trial_{trial.number:04d}"
        bundle_paths = write_top_trial_bundle(trial_dir, result)
        outputs.append({"directory": trial_dir, **bundle_paths, "trial_number": trial.number})
        exported += 1
    return outputs
