# Plan 02-02 Summary

## Outcome

Implemented the reusable Phase 2 backtest runner and locked the shared execution path:

- `src/mgc_bt/backtest/runner.py` now exposes `run_backtest(settings, params) -> dict`
- `src/mgc_bt/backtest/results.py` extracts:
  - summary metrics
  - closed-trade log records
  - equity-curve series
- `src/mgc_bt/cli.py` now routes `backtest` through the same shared runner instead of a separate code path
- Added `tests/test_backtest_runner.py` to cover both the real runner contract and CLI-to-runner wiring

## API Contract

The returned Python dict now includes:

- `mode`
- `instrument_id`
- `segment_instruments`
- `segment_count`
- `start_date`
- `end_date`
- `total_pnl`
- `sharpe_ratio`
- `win_rate`
- `max_drawdown`
- `max_drawdown_pct`
- `total_trades`
- `parameters`
- `segments`
- `trade_log`
- `equity_curve`

This gives Phase 4 an in-process backtest primitive without subprocess overhead.

## Important Notes

- The runner uses `BacktestNode` plus verified 1.225.0 config objects, not a custom simulator.
- The CLI `backtest` command is a thin wrapper over `run_backtest(...)`.
- The temporary Phase 2 harness strategy remains intentionally minimal and bar-driven so Phase 3 can replace it with the real production strategy logic cleanly.

## Verification

Automated:

- `uv run pytest tests/test_backtest_runner.py tests/test_cli.py -q`

Manual smoke:

- `uv run python -m mgc_bt backtest --instrument-id MGCJ1.GLBX --start-date 2021-03-08T00:00:00+00:00 --end-date 2021-03-08T01:00:00+00:00`

The smoke run confirmed the shared runner path returns summary metrics and prints them through the CLI.
