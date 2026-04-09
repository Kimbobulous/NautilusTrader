# Requirements: MGC Backtesting and Optimization System

**Defined:** 2026-04-08
**Core Value:** Reliable MGC data ingestion and trustworthy event-driven backtests that make optimization results credible enough to act on.

## v1 Requirements

### Configuration and CLI

- [x] **CLI-01**: User can run separate `ingest`, `backtest`, and `optimize` commands without rerunning unrelated steps
- [x] **CLI-02**: User can configure data, catalog, and results paths through config files instead of source-code path edits
- [x] **CLI-03**: User can run the project locally on Windows PowerShell using the existing `uv` and `.venv` workflow

### Data Ingestion

- [x] **DATA-01**: User can load Databento instrument definition files into a Nautilus Parquet catalog before market data is written
- [x] **DATA-02**: User can load MGC 1-minute OHLCV bar data from existing local Databento files into the catalog
- [x] **DATA-03**: User can load MGC trade tick data from existing local Databento files into the catalog
- [x] **DATA-04**: User receives ingestion confirmation showing counts written for definitions, bars, and trades
- [x] **DATA-05**: User receives the catalog date range for the loaded MGC data
- [x] **DATA-06**: User receives data-quality warnings for missing files, empty loads, or obvious continuity issues

### Backtesting

- [x] **BT-01**: User can run a Nautilus event-driven backtest against catalog-backed MGC data using a `Strategy` implementation
- [x] **BT-02**: Strategy signals are evaluated on completed 1-minute bars only in v1
- [x] **BT-03**: Backtests include approximately `$0.50` commission per side
- [x] **BT-04**: Backtests include `1` tick (`$0.10`) slippage per fill
- [x] **BT-05**: User receives a trade log for each backtest run
- [x] **BT-06**: User receives summary metrics including total PnL, Sharpe ratio, win rate, max drawdown, and total trades
- [x] **BT-07**: User receives an equity curve saved as a PNG for each completed backtest run

### Strategy Logic

- [x] **STRAT-01**: Strategy uses Adaptive SuperTrend and VWAP to determine trend direction
- [x] **STRAT-02**: Strategy uses WaveTrend to detect pullback exhaustion
- [x] **STRAT-03**: Strategy uses delta imbalance, absorption, volume, and candle formation rules as entry triggers
- [x] **STRAT-04**: Strategy uses an ATR trailing stop for exits
- [x] **STRAT-05**: Strategy is implemented as a pure rule-based system with no machine-learning model training

### Optimization

- [ ] **OPT-01**: User can run parameter optimization with Optuna against the Nautilus backtest workflow
- [ ] **OPT-02**: Each tested parameter combination records Sharpe ratio, total PnL, win rate, max drawdown, and total trades
- [ ] **OPT-03**: User receives a ranked parameter table for all tested combinations in the optimization run
- [ ] **OPT-04**: User receives an equity curve PNG for the best parameter set from optimization
- [ ] **OPT-05**: Optimization outputs are saved into a results directory for later review

## v2 Requirements

### Advanced Execution

- **EXEC-01**: User can simulate intrabar or sub-minute execution behavior
- **EXEC-02**: User can extend trigger logic with richer microstructure handling beyond v1 bar-close evaluation

### Expanded Scope

- **SCOPE-01**: User can backtest instruments beyond MGC
- **SCOPE-02**: User can evaluate portfolio-level analytics across multiple strategies or instruments
- **SCOPE-03**: User can run distributed or parallel optimization infrastructure

## Out of Scope

| Feature | Reason |
|---------|--------|
| Live trading | v1 is research-only and must first prove ingestion and backtest trust |
| Paper trading | Same reason as live trading; not needed for v1 validation |
| Multi-instrument support | v1 is intentionally constrained to MGC futures only |
| Options or other derivatives | Product scope is MGC futures only |
| External data vendors beyond existing Databento files | Avoids scope and data-consistency drift |
| Machine-learning model training | v1 is explicitly pure rule-based logic |
| Dashboards or web UI | CLI-first workflow is sufficient for the initial release |
| Automated scheduling or task runners | Manual command execution is enough for local research |
| Distributed optimization | Adds complexity before single-machine workflow is proven |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01 | Phase 1 | Completed |
| CLI-02 | Phase 1 | Completed |
| CLI-03 | Phase 1 | Completed |
| DATA-01 | Phase 1 | Completed |
| DATA-02 | Phase 1 | Completed |
| DATA-03 | Phase 1 | Completed |
| DATA-04 | Phase 1 | Completed |
| DATA-05 | Phase 1 | Completed |
| DATA-06 | Phase 1 | Completed |
| BT-01 | Phase 2 | Completed |
| BT-02 | Phase 2 | Completed |
| BT-03 | Phase 2 | Completed |
| BT-04 | Phase 2 | Completed |
| BT-05 | Phase 2 | Completed |
| BT-06 | Phase 2 | Completed |
| BT-07 | Phase 2 | Completed |
| STRAT-01 | Phase 3 | Completed |
| STRAT-02 | Phase 3 | Completed |
| STRAT-03 | Phase 3 | Completed |
| STRAT-04 | Phase 3 | Completed |
| STRAT-05 | Phase 3 | Completed |
| OPT-01 | Phase 4 | Pending |
| OPT-02 | Phase 4 | Pending |
| OPT-03 | Phase 4 | Pending |
| OPT-04 | Phase 4 | Pending |
| OPT-05 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0

---
*Requirements defined: 2026-04-08*
*Last updated: 2026-04-09 after Phase 3 completion*
