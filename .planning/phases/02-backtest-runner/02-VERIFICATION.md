---
status: passed
phase: 02-backtest-runner
verified: 2026-04-08
---

# Phase 2 Verification

## Goal Check

Phase 2 goal was to deliver a trustworthy Nautilus backtest runner with configured venue assumptions, cost model, and saved artifacts for a single parameter set.

Verdict: passed.

## Must-Haves

- [x] User can run `backtest` against the existing catalog without re-ingesting data
- [x] Backtest execution applies configured commission and slippage assumptions through Nautilus-native configuration
- [x] Completed runs produce summary metrics, trade logs, and an equity-curve PNG
- [x] The runner is built on Nautilus backtest configuration objects rather than a custom vectorized simulator
- [x] The backtest core is callable as `run_backtest(settings, params) -> dict`
- [x] Catalog continuity note is preserved:
  - definitions were ingested with legacy Cython decoding
  - bars/trades were ingested with `as_legacy_cython=False`

## Automated Checks

- `uv run pytest tests/test_cli.py tests/test_backtest_contracts.py -q`
- `uv run pytest tests/test_backtest_runner.py tests/test_cli.py -q`
- `uv run pytest tests/test_backtest_runner.py tests/test_backtest_artifacts.py tests/test_cli.py -q`
- `uv run pytest -q`

All passed.

## Manual Checks

- Single-contract smoke run passed:
  - `uv run python -m mgc_bt backtest --instrument-id MGCJ1.GLBX --start-date 2021-03-08T00:00:00+00:00 --end-date 2021-03-08T01:00:00+00:00`
- Default auto-roll smoke run passed:
  - `uv run python -m mgc_bt backtest --start-date 2024-01-02T00:00:00+00:00 --end-date 2024-01-05T00:00:00+00:00`
- `results/backtests/latest/` contains:
  - `summary.json`
  - `trades.csv`
  - `run_config.toml`
  - `equity_curve.png`

## Notes

- The next-bar execution requirement is achieved natively through a venue latency model set to one bar interval for 1-minute data.
- Phase 2 still uses a deliberate harness strategy for plumbing verification. Phase 3 owns the production MGC strategy logic.
