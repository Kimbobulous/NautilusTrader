---
status: passed
phase: 03-strategy-logic
verified: 2026-04-09
---

# Phase 3 Verification

## Goal Check

Phase 3 goal was to implement the full rule-based MGC strategy using Nautilus `Strategy` lifecycle methods and completed 1-minute bar evaluation.

Verdict: passed.

## Must-Haves

- [x] Strategy extends Nautilus `Strategy` and initializes through official lifecycle hooks
- [x] Trend, pullback, entry trigger, and ATR trailing-stop logic all run inside the event-driven backtest workflow
- [x] Signals are evaluated on completed 1-minute bars only
- [x] The implementation remains purely rule-based with no machine-learning training path
- [x] The shared backtest core remains callable as `run_backtest(settings, params) -> dict`
- [x] Trade delta uses the installed `TradeTick.aggressor_side` enum values:
  - `AggressorSide.BUYER`
  - `AggressorSide.SELLER`
- [x] Catalog continuity note is preserved:
  - definitions were ingested with legacy Cython decoding
  - bars/trades were ingested with `as_legacy_cython=False`

## Automated Checks

- `uv run pytest tests/test_strategy_indicators.py tests/test_strategy_logic.py -q`
- `uv run pytest tests/test_backtest_runner.py tests/test_cli.py tests/test_databento_discovery.py tests/test_strategy_indicators.py tests/test_strategy_logic.py -q`
- `uv run pytest tests/test_backtest_runner.py tests/test_strategy_logic.py -q`
- `uv run pytest -q`

All passed.

## Manual Checks

- Bounded production-strategy smoke run passed:
  - `uv run python -m mgc_bt backtest --instrument-id MGCJ1.GLBX --start-date 2021-03-08T00:00:00+00:00 --end-date 2021-03-08T06:00:00+00:00`
- `results/backtests/latest/` was refreshed with:
  - `summary.json`
  - `trades.csv`
  - `run_config.toml`
  - `equity_curve.png`

## Notes

- Phase 3 replaced the temporary harness strategy from Phase 2 with the real stateful MGC strategy.
- A small reporting bug surfaced during manual smoke validation: no-trade windows could collapse the reported summary date range to a single timestamp because the account report emitted only an initial equity point. The phase now reports the resolved contract window instead.
- The bounded smoke window produced zero trades, which is acceptable for a wiring validation because the objective was to verify production strategy execution, artifact generation, and metadata integrity rather than profitability.
