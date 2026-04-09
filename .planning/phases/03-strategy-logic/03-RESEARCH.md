# Phase 3: Strategy Logic - Research

**Date:** 2026-04-08
**Phase:** 03 - Strategy Logic
**Goal:** Implement the full rule-based MGC strategy using Nautilus `Strategy` lifecycle methods and completed 1-minute bar evaluation.

## Research Question

What do we need to know to plan the production MGC strategy cleanly on top of the Phase 2 runner without breaking the existing backtest contract?

## Key Findings

### 1. Nautilus strategy integration should stay event-driven and lifecycle-driven

- `nt_docs/concepts/strategies.md` confirms the correct pattern is a `Strategy` subclass with state initialized in `__init__`, subscriptions in `on_start`, and market-data handling in `on_bar` and `on_trade_tick`.
- The production Phase 3 strategy should replace the temporary harness currently referenced by `src/mgc_bt/backtest/configuration.py`, not create a second execution path.
- Existing Phase 2 runner contracts should remain intact:
  - `run_backtest(settings, params) -> dict`
  - CLI as wrapper over the shared runner
  - artifact generation stays outside the strategy

### 2. The strategy can use both bars and trades without changing the Phase 2 architecture

- Installed Nautilus 1.225.0 exposes `TradeTick.aggressor_side`, which is enough for the locked v1 delta approximation.
- The strategy should subscribe to:
  - 1-minute bars for completed-bar evaluation
  - trade ticks for per-bar delta accumulation
- The cleanest production shape is:
  - `on_trade_tick`: accumulate buy/sell volume into the active minute bucket
  - `on_bar`: finalize that minute’s delta, update rolling indicators, evaluate state machine, manage entries/exits

### 3. Indicator registration is optional here; explicit rolling Python state is the better fit

- Nautilus supports `register_indicator_for_bars(...)`, but the Phase 3 requirements lock the implementation to pure Python rolling indicator classes with incremental state and tests.
- Custom classes with `update(bar)` and properties are a better fit than trying to bend Nautilus built-in indicators into the exact locked behavior for:
  - Adaptive SuperTrend with K-Means-trained ATR centroids
  - Session-reset VWAP with configurable UTC reset hour
  - WaveTrend plus Z-score plus divergence tracking
  - Pullback pivots, volume/range averages, absorption heuristics, and candle-pattern rules

### 4. The main execution risk is timestamp alignment between trades and completed bars

- `nt_docs/concepts/backtesting.md` emphasizes that timestamp semantics matter for event ordering and bar/trade processing.
- The strategy should avoid recomputing delta by querying the catalog inside `on_bar`; that would blur the event model and add avoidable coupling.
- A safer implementation plan is to keep an in-memory per-minute trade accumulator keyed by the bar-close bucket so `on_bar` only consumes already-observed trade state.
- This keeps the strategy deterministic under the existing Phase 2 next-bar execution model.

### 5. The exit model belongs in the strategy, not the venue config

- Phase 2 already solved next-bar execution timing, slippage, and commissions through Nautilus-native config.
- Phase 3 only needs to own strategy exits:
  - ATR trailing stop ratchet
  - hard opposite-trend flip when both SuperTrend and VWAP reverse
- This keeps the venue model stable and avoids mixing strategy risk logic with simulation plumbing.

### 6. The current codebase already gives Phase 3 clean integration points

- `src/mgc_bt/backtest/configuration.py` currently points to the harness strategy and is the natural switch-point to the production strategy config/class.
- `src/mgc_bt/backtest/runner.py` and `results.py` do not need architectural changes; they just need the production strategy to generate real trade behavior.
- `configs/settings.toml` and `src/mgc_bt/config.py` are ready to accept the optimization-facing parameter names now, which prevents Phase 4 refactors.

## Planning Implications

### Recommended module boundaries

- `src/mgc_bt/backtest/strategy.py`
  - production `Strategy` subclass
  - config class using the locked Optuna-facing parameter names
- `src/mgc_bt/backtest/indicators/`
  - `atr.py`
  - `supertrend.py`
  - `vwap.py`
  - `wavetrend.py`
  - `rolling_stats.py`
  - optional shared utilities for rolling windows and pivots
- `src/mgc_bt/backtest/state.py`
  - state-machine enum
  - pullback/trade-state dataclasses if helpful
- `tests/`
  - indicator unit tests with synthetic bar data
  - state-machine or strategy flow tests
  - one end-to-end strategy sequence test

### Recommended plan sequence

1. Build strategy config, indicator primitives, and explicit state containers.
2. Implement trend gate and pullback arming on completed bars.
3. Implement delta accumulation plus entry confirmation logic.
4. Implement ATR exit logic, production strategy integration into the runner, and end-to-end validation.

### Important carry-forward constraint

Any Phase 3 work that reasons about catalog-backed assumptions must preserve the verified Databento decode split:

- definitions were ingested with legacy Cython decoding
- bars and trades were ingested with `as_legacy_cython=False`

This mostly matters for documentation, assumptions, and any future catalog-touching helper code. The strategy itself should stay event-driven and consume data from Nautilus callbacks, not re-decode source data.

## Risks and Mitigations

### Risk: indicator warm-up and readiness mismatch

- Mitigation: centralize readiness checks behind one `is_ready` gate and keep warm-up accounting explicit in tests.

### Risk: inside-bar breakout confirmation leaks across bars incorrectly

- Mitigation: track pending inside-bar breakout state explicitly and test the “next bar only” confirmation rule.

### Risk: delta bucket alignment differs from bar boundaries

- Mitigation: accumulate trades by UTC minute bucket and consume exactly one finalized bucket per completed `on_bar`.

### Risk: Phase 3 scope drifts into Phase 4 optimization concerns

- Mitigation: adopt the exact parameter names now, but do not implement optimization control flow or Optuna integration in this phase.

## Validation Architecture

Phase 3 can be validated with fast local pytest coverage and one bounded end-to-end strategy path:

- unit tests for every custom indicator class using synthetic bar data
- focused strategy/state tests for:
  - readiness gating
  - pivot confirmation
  - pullback arming/reset logic
  - optional confirmation combinations
  - ATR stop ratcheting
  - hard opposite-trend-flip exit
- one bounded end-to-end backtest-oriented test proving the production strategy can run through the existing Phase 2 runner path

Recommended validation split:

- **Quick command:** run strategy and indicator tests only
- **Full suite:** run all tests
- **Manual smoke:** one short real backtest against a bounded MGC contract window after Phase 3 execution

## Recommendation

Plan Phase 3 as four sequential plans:

1. Strategy config, indicator/state scaffolding, and indicator unit tests
2. Trend gate plus pullback qualification logic
3. Delta/candle/absorption/WaveTrend entry confirmations
4. ATR exit logic, production strategy integration into the runner, and end-to-end validation

## RESEARCH COMPLETE
