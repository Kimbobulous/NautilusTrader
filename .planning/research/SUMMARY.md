# Research Summary

**Date:** 2026-04-08
**Project:** MGC Backtesting and Optimization System

## Key Findings

**Stack:** Use a structured Python project on Windows with `uv`, `nautilus_trader==1.225.0`, `ParquetDataCatalog`, `BacktestNode`, and Optuna. Keep configuration externalized and results artifact-driven.

**Table Stakes:** The v1 system needs a clean ingestion path from local Databento DBN files into a Nautilus catalog, a trustworthy event-driven backtest with slippage and commission applied, and repeatable optimization that saves ranked metrics plus best-run equity curves.

**Watch Out For:** Nautilus strategy code must follow the `Strategy` lifecycle, Databento instrument definitions must be loaded before market data, and optimization should not begin before single-run backtest correctness is proven.

## Planning Implications

- Phase 1 should establish the project skeleton, configuration model, Databento file ingestion, and catalog validation.
- Phase 2 should wire the Nautilus backtest runner with venue assumptions, reporting outputs, and deterministic single-run execution.
- Phase 3 should implement the rule-based MGC strategy inside Nautilus event handlers on completed 1-minute bars.
- Phase 4 should add Optuna orchestration, ranked outputs, and best-run rerendering/reporting.
- Remaining phases should harden quality, validation, and usability rather than expand scope.

## Recommended Principle

Treat ingestion and backtest trust as non-negotiable foundations. Optimization is only valuable after the engine wiring, cost model, and artifact outputs are demonstrably correct.

---
*Research complete: 2026-04-08*
