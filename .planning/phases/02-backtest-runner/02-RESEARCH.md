# Phase 2: Backtest Runner - Research

**Date:** 2026-04-08
**Status:** Complete
**Scope:** Planning research for Phase 2 only

## Summary

Phase 2 should keep the backtest runner deliberately split into three steps:

1. Build catalog-backed Nautilus backtest configuration and contract-selection logic.
2. Expose a reusable Python runner that returns structured metrics and exports a trade log.
3. Add stable result-bundle management and equity-curve generation.

The local Nautilus backtesting docs point to a high-level, config-driven approach for production backtests using `BacktestNode` and `BacktestRunConfig`, while also documenting `BacktestEngine.reset()` as a good fit for repeated runs. For this project, the right Phase 2 shape is a reusable Python runner API that builds official Nautilus config objects and returns structured results, with the CLI wrapping that runner. That gives Phase 4 an in-process path later without forcing this phase into a loose ad hoc script.

One Phase 1 compatibility rule must stay visible here: the catalog was created under a mixed Databento decode contract on Nautilus 1.225.0. Definitions were written using legacy Cython objects for catalog compatibility, while bars and trades used `as_legacy_cython=False`. Any Phase 2 code that inspects or extends catalog assumptions needs to preserve that fact.

## Relevant Inputs

### Locked Phase Decisions

- Support both single-contract and default auto-roll modes
- Prefer open-interest rolling, with calendar fallback 5 business days before last trading day
- Treat MGC last trading day as the third-to-last business day of the delivery month for v1
- Use bar-close decision and next-bar execution
- Configure 1 tick slippage and `$0.50` per-side commission through Nautilus venue/fill settings
- Produce timestamped backtest result folders plus a refreshed `latest/`
- Expose `run_backtest(config, params) -> dict` as the core API
- Keep the catalog decode split visible: definitions legacy Cython, bars/trades `as_legacy_cython=False`

### Canonical Nautilus References Reviewed

- `nt_docs/concepts/backtesting.md`
- `nt_docs/getting_started/backtest_high_level.py`
- `nt_docs/getting_started/backtest_low_level.py`
- `nt_docs/api_reference/backtest.md`
- `nt_docs/concepts/strategies.md`
- `.planning/phases/01-catalog-foundation/01-02-SUMMARY.md`

## Findings

### 1. High-level config objects are the right production path

The local Nautilus docs recommend the high-level API for catalog-backed runs:

- `BacktestNode` is the production-oriented path for config-defined runs
- `BacktestRunConfig` groups venue, data, and strategy configuration cleanly
- Catalog-backed execution is a first-class use case, not a workaround

That aligns directly with the Phase 2 requirement to avoid building a vectorized simulator or shelling out into ad hoc scripts. The plan should therefore center on constructing official backtest config objects from project settings rather than hand-assembling everything inside the CLI.

### 2. Repeated runs still need a reusable Python boundary

The same docs note that `BacktestEngine.reset()` is useful for repeated runs against the same data, especially in parameter optimization settings. Even if Phase 2 uses the high-level config path for the user-facing backtest command, the internal code should still center on a callable Python function that:

- accepts loaded settings plus a parameter dictionary
- builds the Nautilus backtest configuration
- runs the backtest
- returns structured metrics as a Python dictionary

This is the clean bridge between a production-like `backtest` command in Phase 2 and Optuna trial execution in Phase 4.

### 3. Venue and fill modeling should stay native to Nautilus

`nt_docs/concepts/backtesting.md` is explicit that:

- execution behavior is driven by venue configuration and fill models
- L1/backtest execution can apply one-tick slippage through fill-model configuration
- matching-engine sequencing matters, so next-bar realism should not be faked by post-processing fills

Implication for planning:

- Phase 2 should use `BacktestVenueConfig` and an importable fill model configuration
- 1 tick slippage should be implemented through the fill model, not by editing fills after the run
- commission should be expressed through venue/account configuration rather than custom result math

The open question for implementation is the exact Nautilus 1.225.0 mechanism for next-bar execution with bar data. The plan should explicitly require verification of the official pattern from `nt_docs/concepts/backtesting.md` before code is written.

### 4. Auto-roll logic should be separated from the core runner

Phase 1 catalog validation showed many outright MGC contracts in the catalog rather than a single continuous instrument. That means Phase 2 needs explicit contract selection logic before a run config is built.

The right separation is:

- one module that resolves candidate contracts and roll boundaries
- one module that turns those selections into Nautilus data/backtest config
- one runner that executes and returns metrics

This keeps roll logic testable without coupling it to plotting or result export.

### 5. Phase 2 should not smuggle in Phase 3 strategy logic

The strategy docs remain clear: actual signal generation belongs inside a `Strategy` subclass and its lifecycle hooks. But the roadmap also intentionally separates Phase 2 from full strategy implementation.

Planning implication:

- Phase 2 should build the runner around a strategy config/import boundary
- if a smoke-test strategy is needed to verify the runner path, it should be minimal and explicitly temporary
- the real trend, pullback, entry, and exit rules stay deferred to Phase 3

### 6. Result artifacts should be built for machine consumption first

The user explicitly wants Phase 4 to consume `summary.json` programmatically. That means Phase 2 should avoid text-only reporting and define a stable result schema now.

Recommended artifact contract:

- `summary.json` as the source of truth for run metrics and parameters
- `trades.csv` as the full trade ledger
- `equity_curve.png` as the human-readable visual
- `run_config.toml` as the exact persisted settings snapshot

The CLI can still print a concise summary, but the artifact format must be primary.

## Recommended Plan Shape

### Plan 02-01: Build catalog-backed backtest configuration and venue setup

This plan should:

- extend the project config model with backtest-specific sections needed for venue setup, run windows, and contract mode
- implement contract resolution and roll-rule helpers
- build Nautilus `BacktestVenueConfig`, data config, and run config objects
- keep the Phase 1 catalog decode rule visible in docs and code comments where relevant

### Plan 02-02: Implement the reusable runner and structured result extraction

This plan should:

- add `run_backtest(config, params) -> dict`
- wire the CLI `backtest` command to that function
- extract summary metrics and trade logs into structured Python objects
- keep any temporary strategy harness clearly distinct from Phase 3 logic

### Plan 02-03: Add artifact persistence and equity-curve generation

This plan should:

- create timestamped run directories
- refresh `latest/`
- write `summary.json`, `trades.csv`, `run_config.toml`
- generate `equity_curve.png`

## Design Recommendations

### Config evolution

Phase 2 should extend the existing `[backtest]` section rather than introduce a new config file. Likely additions:

- run window keys such as `start_date` and `end_date`
- mode keys such as `default_mode`
- venue keys such as starting balance, account type, and venue name
- roll keys such as `roll_preference` and `calendar_roll_business_days`
- artifact toggles and output folder naming behavior

This preserves the stable TOML contract established in Phase 1.

### Internal module boundaries

Phase 2 likely fits best with:

- `src/mgc_bt/backtest/contracts.py` for contract resolution and roll scheduling
- `src/mgc_bt/backtest/configuration.py` for Nautilus config object assembly
- `src/mgc_bt/backtest/runner.py` for `run_backtest(...)`
- `src/mgc_bt/backtest/results.py` for metric extraction and trade-log shaping
- `src/mgc_bt/backtest/reporting.py` or `src/mgc_bt/backtest/artifacts.py` for summary persistence and plots

### Verification strategy

Phase 2 tests should stay mostly deterministic and local:

- unit tests for roll-date and contract-mode logic
- unit tests for result-bundle paths and summary schema
- smoke tests for CLI-to-runner wiring

If a real end-to-end backtest run is included in verification, it should be a bounded smoke run rather than a full five-year execution.

## Risks To Explicitly Plan Around

### Risk 1: Catalog continuity gets lost

Future work can easily forget the Phase 1 decoding split and assume the catalog can be regenerated or extended with a single Databento decode mode. Phase 2 docs and catalog-touching code should explicitly carry forward the verified compatibility rule.

### Risk 2: Roll logic becomes invisible or irreproducible

If contract selection is hidden inside the runner, later optimization results will be harder to interpret. Roll rules should be surfaced in config and included in persisted run config artifacts.

### Risk 3: Phase 2 accidentally absorbs strategy implementation

The runner needs something executable, but Phase 3 owns actual trading logic. Planning should resist filling Phase 2 with production strategy rules just to make the runner "feel complete."

## Recommendation

Proceed with three sequential plans exactly as the roadmap currently states. The right order is configuration and venue setup first, reusable result-bearing runner second, and artifacts/plotting last.
