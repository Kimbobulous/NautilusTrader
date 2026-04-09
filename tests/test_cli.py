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
    assert settings.risk.native_max_order_submit_rate == "100/00:00:01"
    assert settings.risk.max_daily_trades == 10
    assert settings.risk.max_drawdown_pct == 5.0
    assert settings.optimization.seed == 42
    assert settings.optimization.max_trials == 200
    assert settings.optimization.in_sample_start == "2021-03-08T00:00:00+00:00"


def test_cli_errors_when_config_missing() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--config", "configs/missing.toml", "ingest"])

    assert excinfo.value.code == 2


def test_cli_optimize_uses_shared_study_runner(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_run_optimization(settings, *, resume=False, study_name=None, max_trials=None, output=None):
        captured["resume"] = resume
        captured["study_name"] = study_name
        captured["max_trials"] = max_trials
        return {
            "study_name": study_name or settings.optimization.study_name,
            "seed": settings.optimization.seed,
            "completed_trials": 2,
            "failed_trials": 1,
            "best_value": 1.75,
            "best_params": {"supertrend_factor": 2.5},
            "run_dir": "results/optimization/2026-04-09_000000",
            "latest_dir": "results/optimization/latest",
            "storage_path": "results/optimization/optuna_storage.db",
            "best_run_dir": "results/optimization/2026-04-09_000000/best_run",
            "holdout_summary_path": "results/optimization/2026-04-09_000000/best_run/holdout_results.json",
            "overfit_warning": True,
        }

    monkeypatch.setattr("mgc_bt.optimization.study.run_optimization", fake_run_optimization)
    exit_code = main(["optimize", "--resume", "--study-name", "custom-study", "--max-trials", "5"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert captured["resume"] is True
    assert captured["study_name"] == "custom-study"
    assert captured["max_trials"] == 5
    assert "Study: custom-study" in stdout
    assert "Warning: holdout Sharpe is more than 0.3 below in-sample Sharpe." in stdout
