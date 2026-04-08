# Research: Feature Scope

**Date:** 2026-04-08
**Project:** MGC Backtesting and Optimization System

## Table Stakes For This Domain

### Data Ingestion

- Decode local Databento DBN files into Nautilus-native objects
- Load instrument definitions before market data
- Persist bars and trade ticks into a Parquet catalog
- Report row/object counts and data date ranges
- Detect missing files, empty loads, and obvious continuity gaps

### Backtesting

- Configure a simulated venue with explicit commissions and slippage
- Run a Nautilus `Strategy` against catalog-backed 1-minute bar data
- Produce trade-level and portfolio-level summary metrics
- Save an equity curve artifact for later review

### Optimization

- Sweep strategy parameters repeatably
- Record each trial's Sharpe, total PnL, win rate, max drawdown, and trade count
- Rank trials and persist a results table
- Re-run the best configuration and save an equity curve PNG

### CLI and Project Structure

- Separate `ingest`, `backtest`, and `optimize` commands
- Config-driven paths and settings rather than hardcoded machine paths
- Reusable Python modules rather than one-off notebooks or ad hoc scripts

## Project-Specific Differentiators

### Strategy Logic

- Adaptive SuperTrend plus VWAP for trend alignment
- WaveTrend for pullback exhaustion
- Delta imbalance, absorption, volume, and candle-pattern confirmation for entries
- ATR trailing stop for exits

### Output Expectations

- `ingest`: confirmation, date range, counts, and quality warnings
- `backtest`: trade log, summary metrics, and equity-curve PNG
- `optimize`: ranked parameter table plus best-run equity-curve PNG

## Recommended v2+ Deferrals

- Live or paper trading
- Multi-instrument or portfolio orchestration
- Intrabar execution logic
- UI/dashboard work
- Distributed optimization
- Machine-learning augmentation

---
*Research feature summary for requirements definition*
