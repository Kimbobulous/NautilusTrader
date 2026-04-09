# Plan 03-05 Summary

## Outcome

Completed a dedicated Phase 3 risk-management layer:

- Enabled Nautilus native `RiskEngineConfig` in the shared backtest configuration path
- Added standalone risk controls in `src/mgc_bt/backtest/risk.py`
- Added a new `[risk]` config section in `configs/settings.toml`
- Loaded typed risk settings in `src/mgc_bt/config.py`
- Wired risk parameters through the shared runner/configuration/artifact path for future Optuna reuse
- Integrated the strategy with `risk.can_enter(...)` before order submission and `risk.should_exit(...)` on every in-trade bar
- Added standalone risk coverage in `tests/test_risk.py`

## Key Notes

- Native Nautilus infrastructure now owns built-in pre-trade validation such as instrument precision, quantity checks, and configured notional/rate limits
- The public decision surface is centered on the two required methods:
  - `can_enter(direction, stop_distance, account_equity)`
  - `should_exit(position, current_bar, account_equity)`
- Risk state is independent from the strategy state machine and maintains only session-level counters, drawdown tracking, loss streak logic, and per-trade dollar-risk validation
- Phase 4 can now include risk limits in the Optuna search space without reshaping the backtest architecture

## Verification

Automated:

- `uv run pytest tests/test_risk.py tests/test_strategy_logic.py tests/test_strategy_indicators.py -q`
- `uv run pytest tests/test_cli.py tests/test_backtest_runner.py tests/test_backtest_artifacts.py tests/test_databento_discovery.py -q`

The risk layer is now part of the production strategy path while remaining independently testable.
