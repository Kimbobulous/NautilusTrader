from __future__ import annotations

import pytest

from mgc_bt.backtest.strategy_registry import register_strategy
from mgc_bt.backtest.strategy_registry import resolve_strategy_registration


def test_registry_resolves_named_default() -> None:
    registration = resolve_strategy_registration(strategy="mgc_production", strategy_class=None)

    assert registration.name == "mgc_production"
    assert registration.strategy_path == "mgc_bt.backtest.strategy:MgcProductionStrategy"
    assert registration.config_path == "mgc_bt.backtest.strategy:MgcStrategyConfig"


def test_registry_resolves_explicit_strategy_override() -> None:
    registration = resolve_strategy_registration(
        strategy="mgc_production",
        strategy_class="mgc_bt.backtest.strategy_stub:Phase2HarnessStrategy",
    )

    assert registration.name == "Phase2HarnessStrategy"
    assert registration.strategy_path == "mgc_bt.backtest.strategy_stub:Phase2HarnessStrategy"
    assert registration.config_path == "mgc_bt.backtest.strategy_stub:Phase2HarnessConfig"


def test_registry_supports_new_registered_strategy_without_runner_changes() -> None:
    register_strategy(
        "phase2_harness",
        "mgc_bt.backtest.strategy_stub:Phase2HarnessStrategy",
        "mgc_bt.backtest.strategy_stub:Phase2HarnessConfig",
    )

    registration = resolve_strategy_registration(strategy="phase2_harness", strategy_class=None)

    assert registration.name == "phase2_harness"
    assert registration.strategy_path.endswith("Phase2HarnessStrategy")
    assert registration.config_path.endswith("Phase2HarnessConfig")


def test_registry_rejects_unknown_strategy_name() -> None:
    with pytest.raises(ValueError, match="Unknown strategy 'does_not_exist'"):
        resolve_strategy_registration(strategy="does_not_exist", strategy_class=None)
