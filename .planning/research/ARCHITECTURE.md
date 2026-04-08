# Research: Target Architecture

**Date:** 2026-04-08
**Project:** MGC Backtesting and Optimization System

## Recommended System Shape

**Overall pattern:** Config-driven local research application with a clean CLI front end, catalog-backed data layer, event-driven Nautilus strategy layer, and a separate optimization orchestration layer.

## Component Boundaries

### CLI Layer

- Exposes `ingest`, `backtest`, and `optimize`
- Parses config path and run options
- Delegates to application services rather than holding business logic

### Configuration Layer

- Loads paths, venue settings, slippage/commission assumptions, and parameter ranges
- Keeps local machine details outside the code path
- Allows porting the project to another Windows machine without source edits

### Ingestion Layer

- Scans local Databento files
- Decodes DEFINITION, OHLCV_1M, and TRADES DBN files with `DatabentoDataLoader`
- Writes Nautilus-native objects into `ParquetDataCatalog`
- Runs integrity/quality checks and emits warnings

### Strategy Layer

- Implements the MGC pullback strategy as a Nautilus `Strategy`
- Uses `on_start` for initialization and subscriptions/hydration
- Uses `on_bar` for completed 1-minute signal evaluation in v1
- Maintains internal state for trend, pullback, trigger, and trailing stop logic

### Backtest Layer

- Builds `BacktestVenueConfig`, `BacktestDataConfig`, and `BacktestRunConfig`
- Executes catalog-backed runs via `BacktestNode`
- Produces raw and summarized outputs for one parameter set

### Optimization Layer

- Wraps repeated backtests inside an Optuna study
- Stores per-trial metrics and parameter values
- Selects the best trial, reruns it if needed, and exports the best-run equity curve

### Reporting Layer

- Writes trade logs and metric summaries to the results directory
- Creates ranked optimization tables
- Saves equity curve PNGs

## Data Flow

1. Local DBN files are read from configured data paths.
2. Instrument definitions are decoded and written to the catalog first.
3. Bars and trade ticks are decoded and written to the catalog.
4. The backtest command pulls catalog data into a `BacktestNode` run configuration.
5. The Nautilus strategy reacts to bar events and submits/cancels/manages orders through the engine.
6. Metrics and trade artifacts are collected and written to the results directory.
7. The optimization command repeats the backtest flow across parameter trials and ranks the outputs.

## Suggested Build Order

1. Configuration and project skeleton
2. Databento file discovery and catalog ingestion
3. Catalog validation and data-quality reporting
4. Minimal backtest runner wired to Nautilus
5. Strategy implementation on completed 1-minute bars
6. Reporting and equity curve export
7. Optuna study orchestration and ranked result export

---
*Architecture research for roadmap creation*
