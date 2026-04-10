from __future__ import annotations

from pathlib import Path

import pytest

from mgc_bt.config import ConfigError
from mgc_bt.config import load_settings


def _write_settings_file(path: Path, content: str) -> Path:
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def test_optimization_settings_validate_ordering(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.toml"
    _write_settings_file(
        config_path,
        """
[paths]
project_root = "."
data_root = "data"
catalog_root = "catalog"
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
start_date = ""
end_date = ""
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
study_name = "bad-order"
direction = "maximize"
results_subdir = "optimization"
storage_filename = "optuna_storage.db"
seed = 42
max_trials = 5
max_runtime_seconds = 60
early_stop_window = 5
early_stop_min_improvement = 0.05
in_sample_start = "2025-01-01T00:00:00+00:00"
in_sample_end = "2026-01-01T00:00:00+00:00"
holdout_start = "2025-06-01T00:00:00+00:00"
holdout_end = "2026-06-01T00:00:00+00:00"

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
    with pytest.raises(ConfigError):
        load_settings(config_path)


def test_load_settings_wraps_malformed_toml_as_config_error(tmp_path: Path) -> None:
    config_path = _write_settings_file(
        tmp_path / "settings.toml",
        """
[paths
project_root = "."
""",
    )

    with pytest.raises(ConfigError, match="valid TOML"):
        load_settings(config_path)


def test_phase_six_defaults_load_from_project_settings() -> None:
    settings = load_settings("configs/settings.toml")

    assert settings.backtest.strategy == "mgc_production"
    assert settings.backtest.strategy_class is None
    assert settings.walk_forward.train_months == 12
    assert settings.walk_forward.validation_months == 3
    assert settings.walk_forward.test_months == 3
    assert settings.walk_forward.step_months == 3
    assert settings.walk_forward.validation_top_n == 5
    assert settings.walk_forward.min_training_bars == 50000
    assert settings.walk_forward.min_test_trades == 10
    assert settings.walk_forward.final_test_months == 6
    assert settings.walk_forward.runtime_warning_minutes == 30
    assert settings.monte_carlo.simulations == 1000
    assert settings.monte_carlo.confidence_level == 0.95
    assert settings.monte_carlo.percentile_points == (5, 25, 50, 75, 95)
    assert settings.monte_carlo.random_seed_offset == 10000


def test_phase_ten_production_windows_match_locked_research_contract() -> None:
    settings = load_settings("configs/settings.toml")

    assert settings.optimization.in_sample_start == "2021-03-09T00:00:00+00:00"
    assert settings.optimization.in_sample_end == "2024-12-31T23:59:00+00:00"
    assert settings.optimization.holdout_start == "2025-01-01T00:00:00+00:00"
    assert settings.optimization.holdout_end == "2025-12-31T23:59:00+00:00"
    assert settings.walk_forward.final_test_months == 6


def test_smoke_optimization_config_loads_with_locked_phase_ten_values() -> None:
    settings = load_settings("configs/smoke_optimization.toml")

    assert settings.optimization.study_name == "mgc-optuna-smoke"
    assert settings.optimization.storage_filename == "optuna_storage_smoke.db"
    assert settings.optimization.max_trials == 10
    assert settings.optimization.in_sample_start == "2021-03-09T00:00:00+00:00"
    assert settings.optimization.in_sample_end == "2024-12-31T23:59:00+00:00"
    assert settings.optimization.holdout_start == "2025-01-01T00:00:00+00:00"
    assert settings.optimization.holdout_end == "2025-12-31T23:59:00+00:00"
    assert settings.walk_forward.train_months == 12
    assert settings.walk_forward.validation_months == 3
    assert settings.walk_forward.test_months == 3
    assert settings.walk_forward.step_months == 6
    assert settings.walk_forward.final_test_months == 6


def test_phase_six_invalid_walk_forward_values_raise_config_error(tmp_path: Path) -> None:
    config_path = _write_settings_file(
        tmp_path / "settings.toml",
        """
[paths]
project_root = "."
data_root = "data"
catalog_root = "catalog"
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
start_date = ""
end_date = ""
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
train_months = 0
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

    with pytest.raises(ConfigError, match="Walk-forward train_months must be greater than zero."):
        load_settings(config_path)


def test_phase_six_invalid_monte_carlo_values_raise_config_error(tmp_path: Path) -> None:
    config_path = _write_settings_file(
        tmp_path / "settings.toml",
        """
[paths]
project_root = "."
data_root = "data"
catalog_root = "catalog"
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
start_date = ""
end_date = ""
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
confidence_level = 1.2
percentile_points = [5, 95, 75]
random_seed_offset = 10000
""",
    )

    with pytest.raises(ConfigError, match="Monte Carlo confidence_level must be between 0 and 1."):
        load_settings(config_path)


def test_load_settings_uses_phase_six_defaults_when_sections_missing(tmp_path: Path) -> None:
    config_path = _write_settings_file(
        tmp_path / "settings.toml",
        """
[paths]
project_root = "."
data_root = "data"
catalog_root = "catalog"
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
start_date = ""
end_date = ""
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
study_name = "study"
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
""",
    )

    settings = load_settings(config_path)

    assert settings.walk_forward.train_months == 12
    assert settings.walk_forward.final_test_months == 6
    assert settings.monte_carlo.simulations == 1000
    assert settings.monte_carlo.percentile_points == (5, 25, 50, 75, 95)


def test_backtest_strategy_class_must_use_import_path_format(tmp_path: Path) -> None:
    config_path = _write_settings_file(
        tmp_path / "settings.toml",
        """
[paths]
project_root = "."
data_root = "data"
catalog_root = "catalog"
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
strategy = "mgc_production"
strategy_class = "invalid.path"
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
start_date = ""
end_date = ""
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
study_name = "study"
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
""",
    )

    with pytest.raises(ConfigError, match="strategy_class must use the 'package.module:ClassName' format"):
        load_settings(config_path)
