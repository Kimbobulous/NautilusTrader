# Roadmap: MGC Backtesting and Optimization System

## Overview

This roadmap builds the system in dependency order: first establish a clean local project and Databento-to-Nautilus ingestion path, then prove trustworthy single-run backtesting, then implement the rule-based MGC strategy, and finally add repeatable Optuna optimization with saved research artifacts. Final hardening focuses on quality checks and operator usability without expanding beyond the strict v1 scope.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions if needed later

- [x] **Phase 1: Catalog Foundation** - Build the project skeleton, config system, CLI shell, and validated Databento catalog ingestion (completed 2026-04-08)
- [x] **Phase 2: Backtest Runner** - Wire Nautilus backtest execution, venue assumptions, and reporting outputs (completed 2026-04-08)
- [x] **Phase 3: Strategy Logic** - Implement the MGC trend-following pullback strategy inside Nautilus event handlers (completed 2026-04-09)
- [x] **Phase 4: Optimization Workflow** - Add Optuna parameter search with ranked outputs and best-run artifacts (completed 2026-04-09)
- [x] **Phase 5: Validation and Hardening** - Add regression checks, data validations, and operator-facing safeguards for reliable local use (completed 2026-04-09)

## Phase Details

### Phase 1: Catalog Foundation
**Goal**: Deliver a structured Python project with config-driven local paths, a working CLI surface, and validated ingestion of Databento definitions, bars, and trades into a Nautilus Parquet catalog.
**Depends on**: Nothing (first phase)
**Requirements**: [CLI-01, CLI-02, CLI-03, DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06]
**Success Criteria** (what must be TRUE):
  1. User can run `ingest` locally and write MGC definitions, bars, and trades into a Nautilus catalog.
  2. Ingestion output reports counts, loaded date range, and any data quality warnings.
  3. No source-code path edits are needed to change data, catalog, or results locations.
  4. The project runs through a structured package and CLI rather than ad hoc scripts.
**Plans**: 3 plans

Plans:
- [x] 01-01: Scaffold the Python package, CLI entry points, and config model
- [x] 01-02: Implement Databento file discovery and Nautilus catalog ingestion
- [x] 01-03: Add catalog validation and ingestion reporting

### Phase 2: Backtest Runner
**Goal**: Deliver a trustworthy Nautilus backtest runner with configured venue assumptions, cost model, and saved artifacts for a single parameter set.
**Depends on**: Phase 1
**Requirements**: [BT-01, BT-02, BT-03, BT-04, BT-05, BT-06, BT-07]
**Success Criteria** (what must be TRUE):
  1. User can run `backtest` against the catalog without re-ingesting data.
  2. Backtest execution applies the configured commission and slippage assumptions.
  3. A completed run produces a trade log, summary metrics, and an equity curve PNG.
  4. The runner is built on Nautilus backtest configuration objects rather than a custom vectorized simulator.
**Plans**: 3 plans

Plans:
- [x] 02-01: Build the Nautilus backtest configuration and venue setup
- [x] 02-02: Implement result extraction, summary metrics, and trade-log export
- [x] 02-03: Add equity-curve generation and results directory management

### Phase 3: Strategy Logic
**Goal**: Implement the full rule-based MGC strategy using Nautilus `Strategy` lifecycle methods and completed 1-minute bar evaluation.
**Depends on**: Phase 2
**Requirements**: [STRAT-01, STRAT-02, STRAT-03, STRAT-04, STRAT-05]
**Success Criteria** (what must be TRUE):
  1. Strategy extends Nautilus `Strategy` and initializes through official lifecycle hooks.
  2. Trend, pullback, entry trigger, and ATR trailing-stop logic all run inside the event-driven backtest workflow.
  3. Signals are evaluated on completed 1-minute bars only, matching the scoped v1 realism.
  4. The implementation remains purely rule-based with no machine-learning training path.
**Plans**: 5 plans

Plans:
- [x] 03-01: Implement strategy config and internal indicator/state model
- [x] 03-02: Implement trend and pullback qualification logic
- [x] 03-03: Implement entry-trigger confirmation logic
- [x] 03-04: Implement ATR trailing-stop exits and strategy reporting hooks
- [x] 03-05: Add a standalone risk-management layer and wire it into the production strategy

### Phase 4: Optimization Workflow
**Goal**: Deliver a repeatable Optuna workflow that tests parameter combinations, ranks results, and saves best-run artifacts.
**Depends on**: Phase 3
**Requirements**: [OPT-01, OPT-02, OPT-03, OPT-04, OPT-05]
**Success Criteria** (what must be TRUE):
  1. User can run `optimize` against the catalog-backed backtest workflow.
  2. Each trial records parameters and key metrics including Sharpe, PnL, win rate, max drawdown, and trade count.
  3. Optimization outputs include a ranked parameter table saved to the results directory.
  4. The best parameter set produces a saved equity curve PNG and reproducible artifact bundle.
  5. The Optuna search space can vary both strategy parameters and the persisted `[risk]` limits without changing the runner architecture.
**Plans**: 3 plans

Plans:
- [x] 04-01: Define Optuna search space and trial execution wrapper
- [x] 04-02: Persist ranked optimization results and per-trial metrics
- [x] 04-03: Re-run and export the best configuration artifacts

### Phase 5: Validation and Hardening
**Goal**: Make the local workflow reliable through validation, regression protection, and safer operator feedback without expanding scope.
**Depends on**: Phase 4
**Requirements**: [CLI-01, DATA-06, BT-06, OPT-05]
**Success Criteria** (what must be TRUE):
  1. Core ingestion, backtest, and optimization flows have regression protection and validation checks.
  2. Common user mistakes produce clear actionable errors instead of silent failures.
  3. Results and configuration handling are stable enough for repeated local research use.
**Plans**: 3 plans

Plans:
- [x] 05-01: Add automated tests for core non-strategy workflow components
- [x] 05-02: Add stronger validation and error reporting for configuration and data assumptions
- [x] 05-03: Polish local usability and documentation for repeatable operation

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Catalog Foundation | 3/3 | Complete    | 2026-04-08 |
| 2. Backtest Runner | 3/3 | Complete    | 2026-04-08 |
| 3. Strategy Logic | 5/5 | Complete    | 2026-04-09 |
| 4. Optimization Workflow | 3/3 | Complete    | 2026-04-09 |
| 5. Validation and Hardening | 3/3 | Complete    | 2026-04-09 |
