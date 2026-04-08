# Research: Technical Stack

**Date:** 2026-04-08
**Project:** MGC Backtesting and Optimization System

## Recommended Core Stack

- Python 3.13.11 for the local application runtime
- `nautilus_trader==1.225.0` as the event-driven backtest engine and data/catalog framework
- `uv` for environment and package management, with `uv pip install` only
- `DatabentoDataLoader` plus `ParquetDataCatalog` for decoding local DBN files into Nautilus-native catalog data
- Optuna for parameter search orchestration
- Pandas and PyArrow-compatible catalog tooling as needed through Nautilus workflows
- Matplotlib for saved PNG equity curves
- Typer or `argparse` for a small explicit CLI with `ingest`, `backtest`, and `optimize` commands
- YAML or TOML config files for paths, venue settings, and parameter ranges

## Nautilus-Specific Guidance

- Prefer `BacktestNode` plus `BacktestRunConfig` for the backtest and optimization workflow because the local docs mark the high-level API as the recommended production path for catalog-backed runs.
- Use `ParquetDataCatalog` as the persistent storage boundary between ingestion and repeated backtest/optimization runs.
- Keep strategy logic inside a class extending `Strategy`, using lifecycle hooks such as `on_start` and `on_bar`.
- Evaluate signals on completed 1-minute bars only in v1, matching the scoped execution realism.

## Data Pipeline Shape

1. Read Databento DEFINITION DBN files first.
2. Write instruments to the catalog first.
3. Decode and write OHLCV 1-minute bars and trade ticks for MGC into the catalog.
4. Validate date range, counts, and obvious quality issues before allowing downstream backtests.
5. Reuse catalog-backed data for both backtest and optimization runs.

## Key Libraries By Responsibility

- Ingestion: `nautilus_trader.adapters.databento.loaders.DatabentoDataLoader`
- Catalog: `nautilus_trader.persistence.catalog.ParquetDataCatalog`
- Backtest orchestration: `nautilus_trader.backtest.node.BacktestNode`, `BacktestRunConfig`, `BacktestDataConfig`, `BacktestVenueConfig`, `BacktestEngineConfig`
- Strategy implementation: `nautilus_trader.trading.strategy.Strategy`
- Optimization: `optuna`
- Reporting: `matplotlib`, CSV/Parquet result exports

## Recommendation

Build the project as a conventional Python package with:
- `src/` package layout
- `configs/` for user-editable settings
- `results/` for run outputs
- CLI entry points that delegate into reusable services rather than embedding logic in command handlers

---
*Research stack summary for roadmap creation*
