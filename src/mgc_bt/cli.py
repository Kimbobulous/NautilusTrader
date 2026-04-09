from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from mgc_bt.config import ConfigError, Settings, load_settings


class CLIError(RuntimeError):
    """Raised when the CLI cannot continue."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mgc_bt",
        description="MGC futures research CLI.",
    )
    parser.add_argument(
        "--config",
        default="configs/settings.toml",
        help="Path to the project TOML settings file.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("ingest", help="Load Databento data into the Nautilus catalog.")
    backtest_parser = subparsers.add_parser("backtest", help="Run a catalog-backed Nautilus backtest.")
    backtest_parser.add_argument("--instrument-id", help="Run a single-contract backtest for this specific instrument.")
    backtest_parser.add_argument("--start-date", help="Override the configured UTC start date for the run.")
    backtest_parser.add_argument("--end-date", help="Override the configured UTC end date for the run.")
    optimize_parser = subparsers.add_parser("optimize", help="Run Optuna parameter optimization.")
    optimize_parser.add_argument("--resume", action="store_true", help="Resume an existing named Optuna study.")
    optimize_parser.add_argument("--study-name", help="Override the configured Optuna study name.")
    optimize_parser.add_argument("--max-trials", type=int, help="Override the configured maximum trial count.")
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

            result = run_ingest(settings)
            print(render_ingest_cli_output(result))
            return 0
        if args.command == "backtest":
            from mgc_bt.backtest.artifacts import write_backtest_artifacts
            from mgc_bt.backtest.runner import run_backtest

            result = run_backtest(
                settings,
                {
                    "instrument_id": getattr(args, "instrument_id", None),
                    "start_date": getattr(args, "start_date", None),
                    "end_date": getattr(args, "end_date", None),
                },
            )
            artifact_paths = write_backtest_artifacts(settings, result)
            print(_render_backtest_summary(result, artifact_paths))
            return 0
        if args.command == "optimize":
            from mgc_bt.optimization.study import run_optimization

            result = run_optimization(
                settings,
                resume=bool(getattr(args, "resume", False)),
                study_name=getattr(args, "study_name", None),
                max_trials=getattr(args, "max_trials", None),
            )
            print(_render_optimization_summary(result))
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
        lines.append(f"Latest directory: {artifact_paths['latest_dir']}")
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
        f"Latest directory: {result['latest_dir']}",
        f"Storage path: {result['storage_path']}",
    ]
    if result.get("best_run_dir") is not None:
        lines.append(f"Best run directory: {result['best_run_dir']}")
    if result.get("holdout_summary_path") is not None:
        lines.append(f"Holdout results: {result['holdout_summary_path']}")
    if result.get("overfit_warning"):
        lines.append("Warning: holdout Sharpe is more than 0.3 below in-sample Sharpe.")
    return "\n".join(lines)
