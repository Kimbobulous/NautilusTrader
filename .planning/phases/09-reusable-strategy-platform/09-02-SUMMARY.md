# 09-02 Summary

Implemented config-driven strategy resolution without changing the `run_backtest(settings, params)` contract.

## What changed

- Added registry-first strategy resolution in `src/mgc_bt/backtest/strategy_registry.py`
- Extended typed settings with:
  - `backtest.strategy`
  - `backtest.strategy_class`
- Refactored `src/mgc_bt/backtest/configuration.py` to resolve `ImportableStrategyConfig` from registry/import overrides instead of hardcoded MGC paths
- Propagated selected strategy metadata through runner parameters and persisted `run_config.toml`
- Added registry/config regression coverage in `tests/test_strategy_registry.py`, `tests/test_config.py`, and `tests/test_cli.py`

## Verification

- `uv run pytest tests/test_config.py tests/test_strategy_registry.py tests/test_cli.py -q -k "strategy or registry or backtest"`
- `uv run python -m mgc_bt backtest --instrument-id MGCJ1.GLBX --start-date 2021-03-09T00:00:00+00:00 --end-date 2021-06-30T23:59:00+00:00`

## Outcome

The platform now selects strategies through configuration with a simple default (`mgc_production`) and an advanced import-path override, while preserving the existing runner and the traded MGC golden window.
