# MGC Backtesting and Optimization System

## What This Is

A local Windows-based research system for backtesting and parameter optimization of a Micro Gold Futures (MGC) trend-following pullback strategy using `nautilus_trader`. It ingests existing Databento historical files into a Nautilus catalog, runs deterministic backtests, and executes Optuna-based parameter searches through a small CLI with separate `ingest`, `backtest`, and `optimize` commands.

This is a structured Python project for one local user, not a notebook or loose-script workflow. The implementation must follow Nautilus Trader's event-driven architecture, where strategies extend the `Strategy` class and react to engine events rather than iterating vectorized bars in a pandas-style loop.

## Core Value

Reliable MGC data ingestion and trustworthy event-driven backtests that make optimization results credible enough to act on.

## Requirements

### Validated

(None yet - ship to validate)

### Active

- [ ] Load 5 years of Databento MGC bars, trades, and instrument definitions into a Nautilus Parquet catalog
- [ ] Run an event-driven Nautilus backtest for a rule-based MGC trend-following pullback strategy
- [ ] Optimize strategy parameters with Optuna and produce ranked results plus an equity curve for the best run

### Out of Scope

- Live trading and paper trading - v1 is backtesting and optimization only
- Multi-instrument support - v1 is MGC futures only
- Sub-minute or intrabar execution logic - v1 evaluates entries and exits on completed 1-minute bars only
- Dashboards or web UI - CLI-first local workflow is sufficient for v1
- Distributed optimization - local repeatable optimization is enough for v1
- Portfolio analytics - v1 focuses on single-strategy, single-instrument evaluation
- Machine learning models such as Lorentzian or MLMI - v1 is pure rule-based logic only
- Options or any other derivative products - MGC futures only
- External data sources beyond the existing Databento files in `C:\dev\mgc-data` - avoid scope expansion and data inconsistency
- Automated scheduling or task runners - manual CLI execution is the v1 workflow

## Context

The target environment is Windows 11 with PowerShell, Python 3.13.11, `uv`, and an existing virtual environment at `C:\dev\nautilustrader\.venv`. `nautilus_trader 1.225.0` is already installed and package installation should use `uv pip install`, never raw `pip`.

Historical data already exists at `C:\dev\mgc-data` and includes 5 years of 1-minute OHLCV bars, trades, and instrument definitions from Databento. The strategy thesis is a trend-following pullback system using Adaptive SuperTrend plus VWAP for trend direction, WaveTrend for pullback exhaustion, and delta imbalance plus absorption plus volume plus candle formations as entry triggers, with ATR trailing stops for exits.

The user does not write code and wants the entire system implemented through Codex. The project should be local-first and reusable via configuration files rather than hardcoded absolute paths, even though the immediate user is a single local Windows operator.

The local documentation folder `nt_docs/` is a required reference source before Nautilus-specific implementation decisions. Relevant planning and implementation should be grounded in `nt_docs/integrations/databento.md`, `nt_docs/how_to/data_catalog_databento.py`, `nt_docs/concepts/backtesting.md`, `nt_docs/getting_started/backtest_high_level.py`, `nt_docs/getting_started/backtest_low_level.py`, `nt_docs/concepts/strategies.md`, `nt_docs/api_reference/backtest.md`, and related persistence/adapter docs.

## Constraints

- **Platform**: Windows 11 native with PowerShell - implementation and commands must work in the user's local environment
- **Package Management**: Use `uv` and `uv pip install` only - aligns with the existing environment and user requirement
- **Runtime**: Python 3.13.11 with `nautilus_trader 1.225.0` already installed - compatibility matters for all package and API choices
- **Architecture**: Must follow Nautilus Trader's event-driven `Strategy` model - avoids invalid vectorized backtest design
- **Data Source**: Use only the existing Databento files already available locally - v1 assumes no extra downloads or alternate vendors
- **Execution Model**: Completed 1-minute bars only for signal evaluation - keeps v1 behavior deterministic and bounded
- **Cost Model**: Include approximately `$0.50` commission per side and `1` tick (`$0.10`) slippage per fill from day one - realism matters for trustworthy results
- **Interface**: Small CLI with `ingest`, `backtest`, and `optimize` commands - user wants clean explicit steps without rerunning unnecessary work
- **Outputs**: Results must include summary statistics, ranked optimization output, and saved equity-curve PNGs - these define "done" for v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Build a structured Python project with a CLI instead of notebooks or loose scripts | The user wants explicit reusable commands and maintainable code | - Pending |
| Prioritize ingestion before backtesting and optimization | Clean data is the foundation for everything else | - Pending |
| Use separate `ingest`, `backtest`, and `optimize` commands | Enables focused daily workflows and avoids unnecessary reruns | - Pending |
| Use Nautilus Trader's event-driven `Strategy` architecture | Matches the engine's actual design and avoids invalid vectorized implementations | - Pending |
| Include commissions and slippage from v1 | Backtest trust matters more than optimistic raw signal results | - Pending |
| Keep v1 to MGC futures, rule-based logic, and local Databento files only | Prevents scope creep while establishing a credible research baseline | - Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-08 after initialization*
