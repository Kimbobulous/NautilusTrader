from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import csv
import json
import shutil
from typing import Any

import optuna

from mgc_bt.backtest.artifacts import backtest_summary_payload
from mgc_bt.backtest.artifacts import persist_backtest_bundle
from mgc_bt.backtest.artifacts import render_run_config_toml
from mgc_bt.backtest.plotting import save_equity_curve_png
from mgc_bt.config import Settings
from mgc_bt.optimization.search_space import optimized_param_names
from mgc_bt.optimization.storage import optimization_root


def create_optimization_run_dir(settings: Settings) -> Path:
    run_dir = optimization_root(settings) / datetime.now(tz=UTC).strftime("%Y-%m-%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def ranked_trial_rows(study: optuna.study.Study) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trial in study.trials:
        if trial.state != optuna.trial.TrialState.COMPLETE:
            continue
        row = {
            "trial_number": trial.number,
            "objective_score": float(trial.value) if trial.value is not None else None,
            "sharpe_ratio": _float_or_none(trial.user_attrs.get("sharpe_ratio")),
            "total_pnl": _float_or_none(trial.user_attrs.get("total_pnl")),
            "win_rate": _float_or_none(trial.user_attrs.get("win_rate")),
            "max_drawdown_pct": _float_or_none(trial.user_attrs.get("max_drawdown_pct")),
            "total_trades": int(trial.user_attrs.get("total_trades", 0)),
        }
        for name in optimized_param_names():
            row[_param_column_name(name)] = trial.params.get(name)
        rows.append(row)

    rows.sort(
        key=lambda item: (
            -(item["objective_score"] or float("-inf")),
            -(item["sharpe_ratio"] or float("-inf")),
            item["max_drawdown_pct"] if item["max_drawdown_pct"] is not None else float("inf"),
        ),
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def failed_trial_rows(study: optuna.study.Study) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trial in study.trials:
        if trial.state != optuna.trial.TrialState.FAIL:
            continue
        rows.append(
            {
                "trial_number": trial.number,
                "params": trial.params,
                "error": trial.user_attrs.get("error", "Unknown error"),
            },
        )
    return rows


def write_ranked_results_csv(run_dir: Path, rows: list[dict[str, Any]]) -> Path:
    csv_path = run_dir / "ranked_results.csv"
    fieldnames = [
        "rank",
        "trial_number",
        "objective_score",
        "sharpe_ratio",
        "total_pnl",
        "win_rate",
        "max_drawdown_pct",
        "total_trades",
        *[_param_column_name(name) for name in optimized_param_names()],
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return csv_path


def write_failed_trials_json(run_dir: Path, failed_rows: list[dict[str, Any]]) -> Path:
    failed_path = run_dir / "failed_trials.json"
    failed_path.write_text(json.dumps(failed_rows, indent=2), encoding="utf-8")
    return failed_path


def write_optimization_summary_json(
    run_dir: Path,
    summary: dict[str, Any],
) -> Path:
    summary_path = run_dir / "optimization_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path


def write_optimization_run_config(
    settings: Settings,
    run_dir: Path,
    best_params: dict[str, Any],
) -> Path:
    config_path = run_dir / "run_config.toml"
    lines = [
        "[optimization]",
        f'study_name = "{settings.optimization.study_name}"',
        f'direction = "{settings.optimization.direction}"',
        f'results_subdir = "{settings.optimization.results_subdir}"',
        f'storage_filename = "{settings.optimization.storage_filename}"',
        f"seed = {settings.optimization.seed}",
        f"max_trials = {settings.optimization.max_trials}",
        f"max_runtime_seconds = {settings.optimization.max_runtime_seconds}",
        f"early_stop_window = {settings.optimization.early_stop_window}",
        f"early_stop_min_improvement = {settings.optimization.early_stop_min_improvement}",
        f'in_sample_start = "{settings.optimization.in_sample_start}"',
        f'in_sample_end = "{settings.optimization.in_sample_end}"',
        f'holdout_start = "{settings.optimization.holdout_start}"',
        f'holdout_end = "{settings.optimization.holdout_end}"',
        "",
        "[best_params]",
    ]
    for key, value in sorted(best_params.items()):
        lines.append(_toml_assignment(key, value))
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path


def refresh_latest_results(run_dir: Path) -> Path:
    latest_dir = run_dir.parent / "latest"
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    shutil.copytree(run_dir, latest_dir)
    return latest_dir


def write_best_run_bundle(settings: Settings, result: dict[str, Any], destination: Path) -> dict[str, Path]:
    return persist_backtest_bundle(settings=settings, result=result, run_dir=destination)


def write_top_trial_bundle(destination: Path, result: dict[str, Any]) -> dict[str, Path]:
    destination.mkdir(parents=True, exist_ok=True)
    summary_path = destination / "summary.json"
    plot_path = destination / "equity_curve.png"
    summary_path.write_text(json.dumps(backtest_summary_payload(result), indent=2), encoding="utf-8")
    save_equity_curve_png(result["equity_curve"], plot_path)
    return {"summary_path": summary_path, "plot_path": plot_path}


def write_holdout_files(destination: Path, result: dict[str, Any]) -> dict[str, Path]:
    destination.mkdir(parents=True, exist_ok=True)
    summary_path = destination / "holdout_results.json"
    plot_path = destination / "holdout_equity_curve.png"
    summary_path.write_text(json.dumps(backtest_summary_payload(result), indent=2), encoding="utf-8")
    save_equity_curve_png(result["equity_curve"], plot_path)
    return {"summary_path": summary_path, "plot_path": plot_path}


def write_best_run_config(settings: Settings, result: dict[str, Any], destination: Path) -> Path:
    config_path = destination / "run_config.toml"
    config_path.write_text(render_run_config_toml(settings, result), encoding="utf-8")
    return config_path


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _toml_assignment(key: str, value: Any) -> str:
    if isinstance(value, bool):
        return f"{key} = {'true' if value else 'false'}"
    if isinstance(value, int | float):
        return f"{key} = {value}"
    return f'{key} = "{value}"'


def _param_column_name(name: str) -> str:
    return f"param_{name}"
