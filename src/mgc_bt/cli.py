from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from mgc_bt.config import ConfigError, Settings, load_settings
from mgc_bt.validation import preflight_backtest
from mgc_bt.validation import preflight_ingest
from mgc_bt.validation import preflight_optimize
from mgc_bt.validation import render_health_report
from mgc_bt.validation import render_preflight_failure
from mgc_bt.validation import render_preflight_warnings


class CLIError(RuntimeError):
    """Raised when the CLI cannot continue."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mgc_bt",
        description="MGC futures research CLI for ingest, backtest, optimize, and environment health checks.",
    )
    parser.add_argument(
        "--config",
        default="configs/settings.toml",
        help="Path to the project TOML settings file.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("ingest", help="Load local Databento files into the Nautilus catalog after preflight checks.")
    backtest_parser = subparsers.add_parser("backtest", help="Run a catalog-backed Nautilus backtest with preflight validation.")
    backtest_parser.add_argument("--instrument-id", help="Run a single-contract backtest for this specific instrument ID.")
    backtest_parser.add_argument("--start-date", help="Override the configured UTC start date for the run.")
    backtest_parser.add_argument("--end-date", help="Override the configured UTC end date for the run.")
    backtest_parser.add_argument(
        "--force",
        action="store_true",
        help="Refresh results/backtests/latest with this run. Without --force, the canonical run folder is written but latest is left untouched.",
    )
    optimize_parser = subparsers.add_parser("optimize", help="Run Optuna optimization with preflight validation and optional resume.")
    optimize_parser.add_argument("--resume", action="store_true", help="Resume an existing named Optuna study instead of starting a new one.")
    optimize_parser.add_argument("--study-name", help="Override the configured Optuna study name.")
    optimize_parser.add_argument("--max-trials", type=int, help="Override the configured maximum trial count.")
    optimize_parser.add_argument("--walk-forward", action="store_true", help="Run rolling train/validate/test optimization windows on the existing optimize command.")
    optimize_parser.add_argument("--final-test", action="store_true", help="Evaluate the protected final six-month test window after a walk-forward run.")
    optimize_parser.add_argument("--monte-carlo", action="store_true", help="Run Monte Carlo analysis after optimization.")
    optimize_parser.add_argument("--stability", action="store_true", help="Run parameter stability analysis after optimization.")
    optimize_parser.add_argument("--skip-monte-carlo", action="store_true", help="Skip Monte Carlo analysis when walk-forward would otherwise enable it automatically.")
    optimize_parser.add_argument("--skip-stability", action="store_true", help="Skip stability analysis when walk-forward would otherwise enable it automatically.")
    optimize_parser.add_argument(
        "--force",
        action="store_true",
        help="Refresh results/optimization/latest with this run. Without --force, the canonical run folder is written but latest is left untouched.",
    )
    subparsers.add_parser("health", help="Run all ingest, backtest, and optimize preflight checks and summarize local readiness.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    incoming_argv = list(argv) if argv is not None else sys.argv[1:]
    normalized_argv = _normalize_global_options(incoming_argv)
    args = parser.parse_args(normalized_argv)

    try:
        settings = load_settings(Path(args.config))
        if args.command == "ingest":
            from mgc_bt.ingest.service import render_ingest_cli_output, run_ingest

            report = preflight_ingest(settings)
            _raise_on_preflight_failures(report)
            _print_preflight_warnings(report)
            result = run_ingest(settings)
            print(render_ingest_cli_output(result))
            return 0
        if args.command == "backtest":
            from mgc_bt.backtest.artifacts import write_backtest_artifacts
            from mgc_bt.backtest.runner import run_backtest

            params = {
                "instrument_id": getattr(args, "instrument_id", None),
                "start_date": getattr(args, "start_date", None),
                "end_date": getattr(args, "end_date", None),
            }
            report = preflight_backtest(settings, params)
            _raise_on_preflight_failures(report)
            _print_preflight_warnings(report)
            result = run_backtest(
                settings,
                params,
            )
            artifact_paths = write_backtest_artifacts(settings, result, refresh_latest=bool(getattr(args, "force", False)))
            print(_render_backtest_summary(result, artifact_paths))
            return 0
        if args.command == "optimize":
            from mgc_bt.optimization.study import run_optimization

            if bool(getattr(args, "final_test", False)) and not bool(getattr(args, "walk_forward", False)):
                raise CLIError(
                    "--final-test requires --walk-forward so the protected six-month test window stays hidden from the default optimize flow.",
                )
            report = preflight_optimize(
                settings,
                resume=bool(getattr(args, "resume", False)),
                study_name=getattr(args, "study_name", None),
            )
            _raise_on_preflight_failures(report)
            _print_preflight_warnings(report)
            result = run_optimization(
                settings,
                resume=bool(getattr(args, "resume", False)),
                study_name=getattr(args, "study_name", None),
                max_trials=getattr(args, "max_trials", None),
                refresh_latest=bool(getattr(args, "force", False)),
                walk_forward=bool(getattr(args, "walk_forward", False)),
                final_test=bool(getattr(args, "final_test", False)),
                monte_carlo=bool(getattr(args, "monte_carlo", False)),
                stability=bool(getattr(args, "stability", False)),
                skip_monte_carlo=bool(getattr(args, "skip_monte_carlo", False)),
                skip_stability=bool(getattr(args, "skip_stability", False)),
            )
            print(_render_optimization_summary(result))
            return 0
        if args.command == "health":
            ingest_report = preflight_ingest(settings)
            backtest_report = preflight_backtest(settings, {})
            optimize_report = preflight_optimize(
                settings,
                resume=False,
                study_name=settings.optimization.study_name,
            )
            print(render_health_report(ingest_report, backtest_report, optimize_report))
            return 0

        raise CLIError(f"The '{args.command}' command is not implemented yet.")
    except (CLIError, ConfigError) as exc:
        parser.exit(status=2, message=f"error: {exc}\n")


def _normalize_global_options(argv: list[str] | None) -> list[str] | None:
    if argv is None or "--config" not in argv:
        return argv

    index = argv.index("--config")
    if index + 1 >= len(argv):
        return argv

    option = argv[index : index + 2]
    remaining = argv[:index] + argv[index + 2 :]
    return option + remaining


def _render_backtest_summary(result: dict[str, object], artifact_paths: dict[str, Path] | None = None) -> str:
    lines = [
        f"Mode: {result['mode']}",
        f"Instrument: {result['instrument_id']}",
        f"Date range: {result['start_date']} -> {result['end_date']}",
        f"Total PnL: {result['total_pnl']}",
        f"Sharpe ratio: {result['sharpe_ratio']}",
        f"Win rate: {result['win_rate']}",
        f"Max drawdown: {result['max_drawdown']}",
        f"Total trades: {result['total_trades']}",
    ]
    if artifact_paths is not None:
        lines.append(f"Run directory: {artifact_paths['run_dir']}")
        if artifact_paths.get("latest_dir") is not None:
            lines.append(f"Latest directory: {artifact_paths['latest_dir']}")
        else:
            lines.append("Latest directory: unchanged (use --force to refresh latest)")
    return "\n".join(lines)


def _render_optimization_summary(result: dict[str, object]) -> str:
    lines = [
        f"Study: {result['study_name']}",
        f"Seed: {result['seed']}",
        f"Completed trials: {result['completed_trials']}",
        f"Failed trials: {result['failed_trials']}",
        f"Best objective: {result['best_value']}",
        f"Best params: {result['best_params']}",
        f"Run directory: {result['run_dir']}",
        f"Storage path: {result['storage_path']}",
    ]
    if result.get("latest_dir") is not None:
        lines.append(f"Latest directory: {result['latest_dir']}")
    else:
        lines.append("Latest directory: unchanged (use --force to refresh latest)")
    if result.get("best_run_dir") is not None:
        lines.append(f"Best run directory: {result['best_run_dir']}")
    if result.get("holdout_summary_path") is not None:
        lines.append(f"Holdout results: {result['holdout_summary_path']}")
    if result.get("overfit_warning"):
        lines.append("Warning: holdout Sharpe is more than 0.3 below in-sample Sharpe.")
    if result.get("walk_forward_summary_path") is not None:
        lines.append(f"Walk-forward summary: {result['walk_forward_summary_path']}")
    if result.get("walk_forward_counts") is not None:
        counts = result["walk_forward_counts"]
        lines.append(
            "Walk-forward windows: "
            f"completed={counts['completed']}, skipped={counts['skipped']}, inconclusive={counts['inconclusive']}",
        )
    return "\n".join(lines)


def _raise_on_preflight_failures(report) -> None:
    if not report.ok:
        raise CLIError(render_preflight_failure(report))


def _print_preflight_warnings(report) -> None:
    rendered = render_preflight_warnings(report)
    if rendered:
        print(rendered)
