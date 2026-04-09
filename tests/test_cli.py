from __future__ import annotations

from pathlib import Path

import pytest

from mgc_bt.cli import build_parser, main
from mgc_bt.config import load_settings
from mgc_bt.validation.preflight import PreflightIssue
from mgc_bt.validation.preflight import PreflightReport


def _write_settings_file(path: Path, content: str) -> Path:
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def test_parser_registers_expected_subcommands() -> None:
    parser = build_parser()
    namespace = parser.parse_args(["--config", "configs/settings.toml", "ingest"])
    assert namespace.command == "ingest"
    assert namespace.config == "configs/settings.toml"

    backtest_args = parser.parse_args(["backtest", "--instrument-id", "MGCM4.GLBX"])
    assert backtest_args.command == "backtest"
    assert backtest_args.instrument_id == "MGCM4.GLBX"

    optimize_args = parser.parse_args(
        [
            "optimize",
            "--walk-forward",
            "--final-test",
            "--monte-carlo",
            "--stability",
            "--skip-monte-carlo",
            "--skip-stability",
        ],
    )
    assert optimize_args.walk_forward is True
    assert optimize_args.final_test is True
    assert optimize_args.monte_carlo is True
    assert optimize_args.stability is True
    assert optimize_args.skip_monte_carlo is True
    assert optimize_args.skip_stability is True

    health_args = parser.parse_args(["health"])
    assert health_args.command == "health"


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
    assert settings.walk_forward.train_months == 12
    assert settings.walk_forward.final_test_months == 6
    assert settings.monte_carlo.simulations == 1000
    assert settings.monte_carlo.percentile_points == (5, 25, 50, 75, 95)


def test_cli_errors_when_config_missing() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--config", "configs/missing.toml", "ingest"])

    assert excinfo.value.code == 2


def test_cli_optimize_uses_shared_study_runner(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_run_optimization(
        settings,
        *,
        resume=False,
        study_name=None,
        max_trials=None,
        refresh_latest=True,
        output=None,
        walk_forward=False,
        final_test=False,
        monte_carlo=False,
        stability=False,
        skip_monte_carlo=False,
        skip_stability=False,
    ):
        captured["resume"] = resume
        captured["study_name"] = study_name
        captured["max_trials"] = max_trials
        captured["refresh_latest"] = refresh_latest
        captured["walk_forward"] = walk_forward
        captured["final_test"] = final_test
        captured["monte_carlo"] = monte_carlo
        captured["stability"] = stability
        captured["skip_monte_carlo"] = skip_monte_carlo
        captured["skip_stability"] = skip_stability
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
    monkeypatch.setattr("mgc_bt.validation.preflight._study_exists", lambda *args, **kwargs: True)
    exit_code = main(["optimize", "--resume", "--study-name", "custom-study", "--max-trials", "5"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert captured["resume"] is True
    assert captured["study_name"] == "custom-study"
    assert captured["max_trials"] == 5
    assert captured["refresh_latest"] is False
    assert captured["walk_forward"] is False
    assert captured["monte_carlo"] is False
    assert captured["stability"] is False
    assert "Study: custom-study" in stdout
    assert "Warning: holdout Sharpe is more than 0.3 below in-sample Sharpe." in stdout


def test_cli_rejects_final_test_without_walk_forward() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["optimize", "--final-test"])

    assert excinfo.value.code == 2


def test_cli_optimize_can_opt_in_phase_six_analyses(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_run_optimization(settings, **kwargs):
        captured.update(kwargs)
        return {
            "study_name": settings.optimization.study_name,
            "seed": settings.optimization.seed,
            "completed_trials": 1,
            "failed_trials": 0,
            "best_value": 1.0,
            "best_params": {},
            "run_dir": "results/optimization/2026-04-09_000000",
            "latest_dir": None,
            "storage_path": "results/optimization/optuna_storage.db",
        }

    monkeypatch.setattr("mgc_bt.optimization.study.run_optimization", fake_run_optimization)
    exit_code = main(["optimize", "--monte-carlo", "--stability"])
    capsys.readouterr()

    assert exit_code == 0
    assert captured["walk_forward"] is False
    assert captured["monte_carlo"] is True
    assert captured["stability"] is True
    assert captured["skip_monte_carlo"] is False
    assert captured["skip_stability"] is False


def test_cli_backtest_reports_missing_catalog_with_actionable_error(tmp_path: Path) -> None:
    config_path = _write_settings_file(
        tmp_path / "settings.toml",
        """
[paths]
project_root = "."
data_root = "data"
catalog_root = "missing-catalog"
results_root = "results"

[ingestion]
dataset = "GLBX.MDP3"
symbol = "MGC"
bar_schema = "ohlcv-1m"
trade_schema = "trades"
definition_schema = "definition"
load_definitions = true
load_bars = true
load_trades = true
load_mbp1 = false
definitions_glob = "definitions/*.definition.dbn.zst"
bars_glob = "ohcl-1m/*.ohlcv-1m.dbn.zst"
trades_glob = "Trades/*.trades.dbn.zst"
mbp1_glob = "MBP-1_03.09.2021-11.09.2023/*.mbp-1.dbn.zst"

[backtest]
default_mode = "auto_roll"
venue_name = "GLBX"
oms_type = "NETTING"
account_type = "MARGIN"
base_currency = "USD"
starting_balance = "50000 USD"
default_leverage = 1.0
trade_size = "1"
results_subdir = "backtests"
roll_preference = "open_interest"
calendar_roll_business_days = 5
start_date = "2021-03-08T00:00:00+00:00"
end_date = "2021-03-08T06:00:00+00:00"
commission_per_side = 0.5
slippage_ticks = 1
supertrend_atr_length = 10
supertrend_factor = 3.0
supertrend_training_period = 100
vwap_reset_hour_utc = 0
wavetrend_n1 = 10
wavetrend_n2 = 21
wavetrend_ob_level = 2.0
delta_imbalance_threshold = 0.3
absorption_volume_multiplier = 1.5
absorption_range_multiplier = 0.7
volume_lookback = 20
atr_trail_length = 14
atr_trail_multiplier = 2.0
min_pullback_bars = 3

[risk]
native_max_order_submit_rate = "100/00:00:01"
native_max_order_modify_rate = "100/00:00:01"
native_max_notional_per_order = {}
max_loss_per_trade_dollars = 150.0
max_daily_trades = 10
max_daily_loss_dollars = 300.0
max_consecutive_losses = 4
max_drawdown_pct = 5.0

[optimization]
study_name = "test-study"
direction = "maximize"
results_subdir = "optimization"
storage_filename = "optuna_storage.db"
seed = 42
max_trials = 5
max_runtime_seconds = 60
early_stop_window = 5
early_stop_min_improvement = 0.05
in_sample_start = "2021-03-08T00:00:00+00:00"
in_sample_end = "2025-03-08T00:00:00+00:00"
holdout_start = "2025-03-08T00:00:00+00:00"
holdout_end = "2026-03-08T00:00:00+00:00"

[walk_forward]
train_months = 12
validation_months = 3
test_months = 3
step_months = 3
validation_top_n = 5
min_training_bars = 50000
min_test_trades = 10
final_test_months = 6
runtime_warning_minutes = 30

[monte_carlo]
simulations = 1000
confidence_level = 0.95
percentile_points = [5, 25, 50, 75, 95]
random_seed_offset = 10000
""",
    )

    with pytest.raises(SystemExit) as excinfo:
        main(["--config", str(config_path), "backtest"])

    assert excinfo.value.code == 2


def test_cli_optimize_resume_requires_existing_study(monkeypatch) -> None:
    monkeypatch.setattr("mgc_bt.validation.preflight._study_exists", lambda *args, **kwargs: False)

    with pytest.raises(SystemExit) as excinfo:
        main(["optimize", "--resume", "--study-name", "missing-study"])

    assert excinfo.value.code == 2


def test_cli_health_summarizes_ready_missing_and_attention(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "mgc_bt.cli.preflight_ingest",
        lambda settings: PreflightReport(
            "ingest",
            failures=[],
            warnings=[PreflightIssue("warning", "Catalog path already contains data.", "Existing data will be replaced.")],
        ),
    )
    monkeypatch.setattr(
        "mgc_bt.cli.preflight_backtest",
        lambda settings, params: PreflightReport(
            "backtest",
            failures=[PreflightIssue("error", "Catalog data was not found.", "Run ingest first.")],
            warnings=[],
        ),
    )
    monkeypatch.setattr(
        "mgc_bt.cli.preflight_optimize",
        lambda settings, resume, study_name: PreflightReport("optimize", failures=[], warnings=[]),
    )

    exit_code = main(["health"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert "ingest: ATTENTION" in stdout
    assert "backtest: MISSING" in stdout
    assert "optimize: READY" in stdout
