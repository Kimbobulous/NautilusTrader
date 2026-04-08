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
    subparsers.add_parser("backtest", help="Run a catalog-backed Nautilus backtest.")
    subparsers.add_parser("optimize", help="Run Optuna parameter optimization.")
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
