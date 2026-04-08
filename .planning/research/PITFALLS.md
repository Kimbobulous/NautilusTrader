# Research: Pitfalls and Warnings

**Date:** 2026-04-08
**Project:** MGC Backtesting and Optimization System

## Pitfall 1: Loading market data before instrument definitions

- Warning signs: catalog queries return no instrument, backtests fail instrument lookup, or data writes appear successful but downstream reads are broken
- Prevention strategy: always decode and write Databento DEFINITION files before OHLCV or TRADES data
- Phase to address: Phase 1

## Pitfall 2: Building the strategy in a vectorized style instead of Nautilus event handlers

- Warning signs: design depends on looping over DataFrames, precomputed signals outside the engine, or bypassing `Strategy` lifecycle hooks
- Prevention strategy: implement the system as a Nautilus `Strategy` using `on_start`, `on_bar`, and other official hooks
- Phase to address: Phases 2-3

## Pitfall 3: Mixing incomplete execution realism with optimization

- Warning signs: optimization looks great before costs, but performance collapses once slippage and commissions are added
- Prevention strategy: bake in v1 commission and slippage assumptions before optimization starts
- Phase to address: Phase 2

## Pitfall 4: Hardcoding local paths into source code

- Warning signs: scripts only run on one machine or path edits are required before every run
- Prevention strategy: store data, catalog, and results paths in config files and pass config paths through the CLI
- Phase to address: Phase 1

## Pitfall 5: Letting optimization outrun backtest correctness

- Warning signs: many trials run quickly, but metrics are not reproducible or artifact outputs differ between reruns
- Prevention strategy: finish catalog validation, single-run backtest correctness, and reporting before implementing Optuna orchestration
- Phase to address: Phases 2-4

## Pitfall 6: Over-scoping entry logic in v1

- Warning signs: too many indicators, pattern rules, or microstructure nuances stall the first working system
- Prevention strategy: implement the explicitly scoped rule set with completed 1-minute bar logic and defer extra sophistication to later milestones
- Phase to address: Phase 3

## Pitfall 7: Producing optimization results without reproducible artifacts

- Warning signs: best parameters are shown but no saved table, no trade log, or no best-run equity curve is available after the run
- Prevention strategy: make artifact writing a must-have for both single backtests and optimization runs
- Phase to address: Phase 4

---
*Pitfall research for roadmap creation*
