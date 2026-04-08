# Plan 02-01 Summary

## Outcome

Built the Phase 2 backtest foundation:

- Expanded `configs/settings.toml` and `src/mgc_bt/config.py` with stable backtest settings for mode selection, venue identity, roll fallback behavior, and bounded run dates.
- Added `mgc_bt.backtest` package scaffolding with:
  - `contracts.py` for single-contract and auto-roll window resolution
  - `configuration.py` for native Nautilus venue/data/run config assembly
  - `strategy_stub.py` for a minimal runner-enablement strategy
  - initial `runner.py` and `results.py` plumbing
- Updated the CLI so `backtest` accepts `--instrument-id`, `--start-date`, and `--end-date`.
- Added focused coverage in `tests/test_backtest_contracts.py` and updated CLI tests.

## Version Check

Verified the installed `nautilus_trader 1.225.0` surface before implementing config assembly:

- `BacktestRunConfig` is the top-level run object for the high-level API
- `BacktestEngineConfig` is nested under it
- `BacktestVenueConfig` remains the venue config type
- `BacktestNode.run()` returns `list[BacktestResult]`

This was confirmed from:

- `nt_docs/api_reference/backtest.md`
- `nt_docs/concepts/backtesting.md`
- direct package introspection in the local `.venv`

## Important Execution Findings

- The catalog instruments are venue-native CME/Globex contracts, so the venue config must target `GLBX`, not a generic `SIM`.
- Bar-close decisions with genuine next-bar fills are achievable natively in Nautilus by using a venue latency model with `base_latency_nanos = 60_000_000_000` for 1-minute bars.
- One-tick slippage is configured through Nautilus fill modeling, and per-side commission is configured through Nautilus fee modeling.
- The Phase 1 catalog compatibility rule remains in force anywhere catalog continuity is referenced:
  - Databento definitions were ingested with legacy Cython decoding
  - Databento bars and trades were ingested with `as_legacy_cython=False`

## Verification

Automated:

- `uv run pytest tests/test_cli.py tests/test_backtest_contracts.py -q`

Manual smoke:

- `uv run python -m mgc_bt backtest --instrument-id MGCJ1.GLBX --start-date 2021-03-08T00:00:00+00:00 --end-date 2021-03-08T01:00:00+00:00`

Smoke output confirmed:

- single-contract mode works
- the bounded backtest runs against the real catalog
- the CLI prints structured summary metrics
