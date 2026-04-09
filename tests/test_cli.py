from __future__ import annotations

from pathlib import Path

import pytest

from mgc_bt.cli import build_parser, main
from mgc_bt.config import load_settings


def test_parser_registers_expected_subcommands() -> None:
    parser = build_parser()
    namespace = parser.parse_args(["--config", "configs/settings.toml", "ingest"])
    assert namespace.command == "ingest"
    assert namespace.config == "configs/settings.toml"

    backtest_args = parser.parse_args(["backtest", "--instrument-id", "MGCM4.GLBX"])
    assert backtest_args.command == "backtest"
    assert backtest_args.instrument_id == "MGCM4.GLBX"


def test_settings_loader_uses_expected_sections() -> None:
    settings = load_settings("configs/settings.toml")
    assert settings.paths.data_root == Path("C:/dev/mgc-data")
    assert settings.paths.catalog_root == Path.cwd() / "catalog"
    assert settings.ingestion.bar_schema == "ohlcv-1m"
    assert settings.backtest.default_mode == "auto_roll"
    assert settings.backtest.calendar_roll_business_days == 5
    assert settings.backtest.supertrend_atr_length == 10
    assert settings.backtest.min_pullback_bars == 3


def test_cli_errors_when_config_missing() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--config", "configs/missing.toml", "ingest"])

    assert excinfo.value.code == 2


def test_cli_errors_for_unimplemented_commands() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["optimize"])

    assert excinfo.value.code == 2
