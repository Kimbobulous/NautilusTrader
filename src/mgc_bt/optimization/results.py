from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import csv
import json
from typing import Any

import optuna

from mgc_bt.backtest.artifacts import backtest_summary_payload
from mgc_bt.backtest.artifacts import create_unique_timestamped_dir
from mgc_bt.backtest.artifacts import persist_backtest_bundle
from mgc_bt.backtest.artifacts import refresh_latest_dir
from mgc_bt.backtest.artifacts import render_run_config_toml
from mgc_bt.backtest.artifacts import write_manifest
from mgc_bt.backtest.analytics import write_backtest_analytics
from mgc_bt.backtest.plotting import save_equity_curve_png
from mgc_bt.config import Settings
from mgc_bt.optimization.analytics import write_optimization_trade_breakdowns
from mgc_bt.optimization.analytics import write_parameter_sensitivity_csv
from mgc_bt.optimization.search_space import optimized_param_names
from mgc_bt.optimization.storage import optimization_root
from mgc_bt.reporting import write_tearsheet


def create_optimization_run_dir(settings: Settings) -> Path:
    return create_unique_timestamped_dir(
        optimization_root(settings),
        datetime.now(tz=UTC).strftime("%Y-%m-%d_%H%M%S"),
    )


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
    *,
    analysis_flags: dict[str, bool] | None = None,
    final_test_window: dict[str, str] | None = None,
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
    ]
    if analysis_flags and any(analysis_flags.values()):
        lines.extend(
            [
                "",
                "[analysis_flags]",
                f"walk_forward_enabled = {'true' if analysis_flags['walk_forward_enabled'] else 'false'}",
                f"final_test_requested = {'true' if analysis_flags['final_test_requested'] else 'false'}",
                f"monte_carlo_enabled = {'true' if analysis_flags['monte_carlo_enabled'] else 'false'}",
                f"stability_enabled = {'true' if analysis_flags['stability_enabled'] else 'false'}",
            ],
        )
        if final_test_window is not None:
            lines.extend(
                [
                    "",
                    "[final_test_window]",
                    f'start = "{final_test_window["start"]}"',
                    f'end = "{final_test_window["end"]}"',
                ],
            )
    lines.extend(
        [
            "",
            "[best_params]",
        ],
    )
    for key, value in sorted(best_params.items()):
        lines.append(_toml_assignment(key, value))
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path


def refresh_latest_results(run_dir: Path) -> Path:
    latest_dir = refresh_latest_dir(run_dir, refresh_latest=True)
    if latest_dir is None:  # pragma: no cover - helper contract keeps this unreachable
        raise RuntimeError("Latest refresh unexpectedly returned None.")
    return latest_dir


def write_best_run_bundle(settings: Settings, result: dict[str, Any], destination: Path) -> dict[str, Path]:
    outputs = persist_backtest_bundle(settings=settings, result=result, run_dir=destination)
    write_backtest_analytics(result, destination)
    files = [path for path in destination.rglob("*") if path.is_file() and path.name != "manifest.json"]
    write_manifest(destination, files, latest_refreshed=None)
    return outputs


def write_top_trial_bundle(destination: Path, result: dict[str, Any]) -> dict[str, Path]:
    destination.mkdir(parents=True, exist_ok=True)
    summary_path = destination / "summary.json"
    plot_path = destination / "equity_curve.png"
    summary_path.write_text(json.dumps(backtest_summary_payload(result), indent=2), encoding="utf-8")
    save_equity_curve_png(result["equity_curve"], plot_path)
    manifest_path = write_manifest(destination, [summary_path, plot_path], latest_refreshed=None)
    return {"summary_path": summary_path, "plot_path": plot_path, "manifest_path": manifest_path}


def write_holdout_files(destination: Path, result: dict[str, Any]) -> dict[str, Path]:
    destination.mkdir(parents=True, exist_ok=True)
    summary_path = destination / "holdout_results.json"
    plot_path = destination / "holdout_equity_curve.png"
    summary_path.write_text(json.dumps(backtest_summary_payload(result), indent=2), encoding="utf-8")
    save_equity_curve_png(result["equity_curve"], plot_path)
    existing_files = [path for path in destination.iterdir() if path.is_file() and path.name != "manifest.json"]
    write_manifest(destination, existing_files, latest_refreshed=None)
    return {"summary_path": summary_path, "plot_path": plot_path}


def write_best_run_config(settings: Settings, result: dict[str, Any], destination: Path) -> Path:
    config_path = destination / "run_config.toml"
    config_path.write_text(render_run_config_toml(settings, result), encoding="utf-8")
    existing_files = [path for path in destination.iterdir() if path.is_file() and path.name != "manifest.json"]
    write_manifest(destination, existing_files, latest_refreshed=None)
    return config_path


def write_optimization_manifest(run_dir: Path, *, latest_refreshed: bool) -> Path:
    files = [path for path in run_dir.rglob("*") if path.is_file() and path.name != "manifest.json"]
    return write_manifest(run_dir, files, latest_refreshed=latest_refreshed)


def write_optimization_tearsheet(run_dir: Path) -> Path:
    return write_tearsheet(run_dir)


def write_optimization_analytics(
    run_dir: Path,
    *,
    ranked_rows: list[dict[str, Any]],
    best_run_result: dict[str, Any] | None,
) -> list[Path]:
    outputs = [write_parameter_sensitivity_csv(run_dir, ranked_rows)]
    if best_run_result is not None:
        outputs.extend(write_optimization_trade_breakdowns(run_dir, best_run_result.get("analytics_trade_log") or best_run_result.get("trade_log") or []))
    return outputs


def write_walk_forward_artifacts(
    run_dir: Path,
    aggregate_summary: dict[str, Any],
    window_rows: list[dict[str, Any]],
    *,
    final_test_result: dict[str, Any] | None = None,
) -> dict[str, Path]:
    walk_root = run_dir / "walk_forward"
    walk_root.mkdir(parents=True, exist_ok=True)

    window_results_path = walk_root / "window_results.csv"
    window_fieldnames = [
        "window_index",
        "train_start",
        "train_end",
        "validation_start",
        "validation_end",
        "test_start",
        "test_end",
        "status",
        "skipped_reason",
        "inconclusive",
        "training_bar_count",
        "training_completed_trials",
        "training_sharpe",
        "validation_sharpe",
        "validation_max_drawdown_pct",
        "validation_total_pnl",
        "test_sharpe",
        "test_total_pnl",
        "test_total_trades",
        "test_bar_count",
    ]
    with window_results_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=window_fieldnames)
        writer.writeheader()
        for row in window_rows:
            writer.writerow({key: row.get(key) for key in window_fieldnames})

    summary_path = walk_root / "aggregated_summary.json"
    summary_path.write_text(json.dumps(aggregate_summary, indent=2), encoding="utf-8")

    equity_curve_path = walk_root / "equity_curve.png"
    save_equity_curve_png(aggregate_summary["aggregated_equity_curve"], equity_curve_path)

    params_path = walk_root / "params_over_time.csv"
    param_fieldnames = ["window_index", *optimized_param_names()]
    with params_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=param_fieldnames)
        writer.writeheader()
        for row in aggregate_summary.get("selected_params", []):
            writer.writerow({key: row.get(key) for key in param_fieldnames})

    outputs = {
        "walk_root": walk_root,
        "window_results_path": window_results_path,
        "summary_path": summary_path,
        "equity_curve_path": equity_curve_path,
        "params_over_time_path": params_path,
    }

    if final_test_result is not None:
        final_test_summary = walk_root / "final_test_summary.json"
        final_test_plot = walk_root / "final_test_equity_curve.png"
        final_test_summary.write_text(
            json.dumps(backtest_summary_payload(final_test_result), indent=2),
            encoding="utf-8",
        )
        save_equity_curve_png(final_test_result["equity_curve"], final_test_plot)
        outputs["final_test_summary_path"] = final_test_summary
        outputs["final_test_plot_path"] = final_test_plot

    return outputs


def write_monte_carlo_artifacts(run_dir: Path, analysis: dict[str, Any]) -> dict[str, Path]:
    monte_carlo_root = run_dir / "monte_carlo"
    monte_carlo_root.mkdir(parents=True, exist_ok=True)

    permutation_path = monte_carlo_root / "permutation_summary.json"
    permutation_path.write_text(json.dumps(analysis["permutation"], indent=2), encoding="utf-8")

    bootstrap_path = monte_carlo_root / "bootstrap_summary.json"
    bootstrap_path.write_text(json.dumps(analysis["bootstrap"], indent=2), encoding="utf-8")

    confidence_path = monte_carlo_root / "equity_confidence_bands.csv"
    confidence_rows = analysis.get("confidence_bands", [])
    fieldnames = list(confidence_rows[0].keys()) if confidence_rows else ["trade_index"]
    with confidence_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in confidence_rows:
            writer.writerow(row)

    summary_path = monte_carlo_root / "monte_carlo_summary.json"
    summary_payload = {
        "schema_version": 1,
        "run_type": "optimize",
        "analysis_type": "monte_carlo",
        "method": "combined",
        "simulations": analysis.get("simulations"),
        "sample_size": analysis.get("sample_size"),
        "p_value": analysis.get("permutation", {}).get("p_value"),
        "percentiles": analysis.get("percentiles"),
        "pass_95": analysis.get("permutation", {}).get("pass_95"),
        "status": analysis.get("status"),
    }
    if analysis.get("skipped_reason") is not None:
        summary_payload["skipped_reason"] = analysis["skipped_reason"]
    summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    return {
        "root": monte_carlo_root,
        "permutation_path": permutation_path,
        "bootstrap_path": bootstrap_path,
        "confidence_path": confidence_path,
        "summary_path": summary_path,
    }


def write_stability_artifacts(run_dir: Path, analysis: dict[str, Any]) -> dict[str, Path]:
    stability_root = run_dir / "stability"
    stability_root.mkdir(parents=True, exist_ok=True)

    importance_path = stability_root / "param_importance.json"
    importance_payload = {
        "schema_version": 1,
        "run_type": "optimize",
        "analysis_type": "stability",
        "top_parameters": analysis.get("top_parameters", []),
        "param_importance": analysis.get("param_importance", {}),
        "robustness_score": analysis.get("robustness_score", 0.0),
        "robust": analysis.get("robust", False),
        "status": analysis.get("status"),
    }
    if analysis.get("skipped_reason") is not None:
        importance_payload["skipped_reason"] = analysis["skipped_reason"]
    importance_path.write_text(json.dumps(importance_payload, indent=2), encoding="utf-8")

    heatmap_path = stability_root / "top_pair_heatmap.csv"
    heatmap_rows = analysis.get("heatmap_rows", [])
    heatmap_fields = list(heatmap_rows[0].keys()) if heatmap_rows else [
        "parameter_x",
        "parameter_y",
        "offset_x_pct",
        "offset_y_pct",
        "value_x",
        "value_y",
        "sharpe_ratio",
        "total_pnl",
        "max_drawdown_pct",
    ]
    with heatmap_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=heatmap_fields)
        writer.writeheader()
        for row in heatmap_rows:
            writer.writerow(row)

    neighborhood_path = stability_root / "neighborhood_robustness.json"
    neighborhood_payload = {
        "schema_version": 1,
        "run_type": "optimize",
        "analysis_type": "stability",
        "top_parameters": analysis.get("top_parameters", []),
        "robustness_score": analysis.get("robustness_score", 0.0),
        "robust": analysis.get("robust", False),
        "status": analysis.get("status"),
        **analysis.get("neighborhood", {}),
    }
    if analysis.get("skipped_reason") is not None:
        neighborhood_payload["skipped_reason"] = analysis["skipped_reason"]
    neighborhood_path.write_text(json.dumps(neighborhood_payload, indent=2), encoding="utf-8")

    summary_path = stability_root / "stability_summary.json"
    summary_payload = {
        "schema_version": 1,
        "run_type": "optimize",
        "analysis_type": "stability",
        "top_parameters": analysis.get("top_parameters", []),
        "robustness_score": analysis.get("robustness_score", 0.0),
        "robust": analysis.get("robust", False),
        "status": analysis.get("status"),
    }
    if analysis.get("skipped_reason") is not None:
        summary_payload["skipped_reason"] = analysis["skipped_reason"]
    summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    return {
        "root": stability_root,
        "importance_path": importance_path,
        "heatmap_path": heatmap_path,
        "neighborhood_path": neighborhood_path,
        "summary_path": summary_path,
    }


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
