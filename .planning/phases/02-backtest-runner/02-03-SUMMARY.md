# Plan 02-03 Summary

## Outcome

Completed the Phase 2 result-bundle contract:

- Added `src/mgc_bt/backtest/artifacts.py` to persist:
  - `summary.json`
  - `trades.csv`
  - `run_config.toml`
- Added `src/mgc_bt/backtest/plotting.py` to generate `equity_curve.png`
- Updated the CLI to write a timestamped canonical run folder and refresh `results/backtests/latest/`
- Added `tests/test_backtest_artifacts.py` to lock artifact presence, summary schema, and latest refresh behavior

## Result Bundle

Each completed CLI backtest now writes:

- `results/backtests/YYYY-MM-DD_HHMMSS/summary.json`
- `results/backtests/YYYY-MM-DD_HHMMSS/trades.csv`
- `results/backtests/YYYY-MM-DD_HHMMSS/run_config.toml`
- `results/backtests/YYYY-MM-DD_HHMMSS/equity_curve.png`

Then refreshes:

- `results/backtests/latest/`

## Verification

Automated:

- `uv run pytest tests/test_backtest_runner.py tests/test_backtest_artifacts.py tests/test_cli.py -q`
- `uv run pytest -q`

Manual smoke:

- Single-contract:
  - `uv run python -m mgc_bt backtest --instrument-id MGCJ1.GLBX --start-date 2021-03-08T00:00:00+00:00 --end-date 2021-03-08T01:00:00+00:00`
- Default auto-roll:
  - `uv run python -m mgc_bt backtest --start-date 2024-01-02T00:00:00+00:00 --end-date 2024-01-05T00:00:00+00:00`

The artifact bundle now exists under `results/backtests/latest/` with all four required files.
