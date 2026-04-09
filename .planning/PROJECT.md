# MGC Backtesting and Optimization System

## What This Is

A local Windows-based research system for backtesting and parameter optimization of a Micro Gold Futures (MGC) trend-following pullback strategy using `nautilus_trader`. It ingests existing Databento historical files into a Nautilus catalog, runs deterministic backtests, and executes Optuna-based parameter searches through a small CLI with separate `ingest`, `backtest`, and `optimize` commands.

This is a structured Python project for one local user, not a notebook or loose-script workflow. The implementation must follow Nautilus Trader's event-driven architecture, where strategies extend the `Strategy` class and react to engine events rather than iterating vectorized bars in a pandas-style loop.

Always use `nautilus_trader`'s native infrastructure as the foundation. Extend and build on top of what `nautilus_trader` provides natively, never reimplement or work around it. When in doubt, check `nt_docs/` first to see if `nautilus_trader` already handles something before writing custom code.

## Core Value

Reliable MGC data ingestion and trustworthy event-driven backtests that make optimization results credible enough to act on.

## Current Milestone: v1.2 Strategy Validation and Live Research

**Goal:** Use the shipped platform for real research: validate whether the MGC pullback strategy has genuine alpha, refine it based on evidence, implement a second contrast strategy, and prove the platform works end to end on multiple strategies.

**Target features:**
- Full 5-year walk-forward optimization on MGC with tearsheet, Monte Carlo, stability, and ranked results
- Evidence-driven analysis and refinement of the MGC strategy using actual research outputs
- A second MGC strategy implemented on the reusable platform and compared side by side with the pullback strategy
- Final stress-test/documentation pass with a research report and platform lessons learned

## Requirements

### Validated

- [x] Load 5 years of Databento MGC bars, trades, and instrument definitions into a Nautilus Parquet catalog
  Validated in Phase 1: Catalog Foundation
- [x] Run a catalog-backed Nautilus backtest through a reusable Python runner and CLI, with saved metrics/trade/artifact outputs
  Validated in Phase 2: Backtest Runner
- [x] Optimize strategy and approved custom risk parameters with Optuna and persist ranked in-sample plus holdout-evaluation results
  Validated in Phase 4: Optimization Workflow
- [x] Run the local workflow with shared readiness checks, safer result persistence, and repeatable operator guidance
  Validated in Phase 5: Validation and Hardening
- [x] Add a research-integrity layer with walk-forward testing, Monte Carlo validation, parameter stability analysis, and a protected train/validate/test workflow
  Validated in Phase 6: Research Integrity Framework
- [x] Add a richer analytics and reporting layer with trade-audit detail, regime/session/calendar breakdowns, and drawdown recovery analysis
  Validated in Phase 7: Analytics and Audit Layer
- [x] Generate interactive self-contained Plotly tearsheets automatically after `backtest` and `optimize`
  Validated in Phase 8: Interactive Tearsheet Reporting
- [x] Refactor the platform for future strategy reuse through generic strategy foundations, reusable indicators, config-driven switching, and strategy comparison
  Validated in Phase 9: Reusable Strategy Platform

### Active

- [ ] Run a full 5-year walk-forward optimization on the current MGC pullback strategy and produce a complete statistical research artifact bundle
- [ ] Analyze the MGC optimization outputs, refine the strategy based on evidence, and revalidate the refinements with a follow-up optimization
- [ ] Implement a second MGC strategy on the reusable platform and compare it side by side against the pullback strategy
- [ ] Produce a final research report and platform validation pass covering both strategies and any end-to-end issues

## Current State

v1.1 is shipped. The repo now contains a complete local MGC research platform with:
- Databento catalog ingestion, reusable backtest runner, production MGC strategy, Optuna optimization, workflow hardening (v1.0)
- Walk-forward optimization, Monte Carlo analysis, parameter stability (Optuna fANOVA + scikit-learn), streaming trade audit, multi-dimension performance breakdowns, drawdown episode analysis, automatic Plotly HTML tearsheets, reusable strategy base class, standalone indicator primitives, config-driven strategy registry, and side-by-side `compare` command (v1.1)

**Test count:** 89 passing
**Golden fixture:** locked and must continue matching exactly

## Next Milestone Goals

- Execute real strategy research on the current MGC pullback system
- Use research outputs to decide whether refinement improves or harms the strategy
- Validate the reusable strategy platform by implementing and comparing a second strategy
- End with a research report and a clean, verified multi-strategy platform

### Out of Scope

- Live trading and paper trading - reserve for a future major milestone
- Multi-instrument support - still out of scope for v1.2
- New data sources - this milestone builds on the existing local Databento workflow only
- Infrastructure rewrites without a demonstrated bug - v1.2 is about using the shipped platform
- Any workaround that bypasses `BaseResearchStrategy`, the indicator library, or the strategy registry for new strategies
- Replacing the current core Nautilus backtest engine - extend the platform rather than rebuild it
- Sub-minute or intrabar execution logic - v1 evaluates entries and exits on completed 1-minute bars only
- Dashboards or web UI - CLI-first local workflow is sufficient for v1.2
- Distributed optimization - local repeatable optimization is enough for v1.2
- Portfolio analytics - v1.2 still focuses on single-strategy, single-instrument evaluation
- Machine learning models such as Lorentzian or MLMI - keep strategy research rule-based for this milestone
- Options or any other derivative products - MGC futures only
- External data sources beyond the existing Databento files in `C:\dev\mgc-data` - avoid scope expansion and data inconsistency
- Automated scheduling or task runners - manual CLI execution is the v1 workflow

## Context

The target environment is Windows 11 with PowerShell, Python 3.13.11, `uv`, and an existing virtual environment at `C:\dev\nautilustrader\.venv`. `nautilus_trader 1.225.0` is already installed and package installation should use `uv pip install`, never raw `pip`.

Historical data already exists at `C:\dev\mgc-data` and includes 5 years of 1-minute OHLCV bars, trades, and instrument definitions from Databento. The primary strategy thesis is a trend-following pullback system using Adaptive SuperTrend plus VWAP for trend direction, WaveTrend for pullback exhaustion, and delta imbalance plus absorption plus volume plus candle formations as entry triggers, with ATR trailing stops for exits.

The user does not write code and wants the entire system implemented through Codex. The project should remain local-first and reusable via configuration files rather than hardcoded absolute paths, even though the immediate user is a single local Windows operator.

The local documentation folder `nt_docs/` is a required reference source before Nautilus-specific implementation decisions. Relevant planning and implementation should be grounded in `nt_docs/integrations/databento.md`, `nt_docs/how_to/data_catalog_databento.py`, `nt_docs/concepts/backtesting.md`, `nt_docs/getting_started/backtest_high_level.py`, `nt_docs/getting_started/backtest_low_level.py`, `nt_docs/concepts/strategies.md`, `nt_docs/api_reference/backtest.md`, and related persistence/adapter docs.

This milestone is explicitly research-driven. Results must be reviewed after each phase before moving forward. The platform should only change when findings justify a bug fix or a strategy refinement that is itself part of the milestone.

## Constraints

- **Platform**: Windows 11 native with PowerShell - implementation and commands must work in the user's local environment
- **Package Management**: Use `uv` and `uv pip install` only - aligns with the existing environment and user requirement
- **Runtime**: Python 3.13.11 with `nautilus_trader 1.225.0` already installed - compatibility matters for all package and API choices
- **Architecture**: Must follow Nautilus Trader's event-driven `Strategy` model - avoids invalid vectorized backtest design
- **Platform Principle**: Always use Nautilus Trader native infrastructure first - custom code must extend native facilities instead of replacing them
- **Data Source**: Use only the existing Databento files already available locally - v1 assumes no extra downloads or alternate vendors
- **Execution Model**: Completed 1-minute bars only for signal evaluation - keeps v1 behavior deterministic and bounded
- **Workflow**: `uv run python -m mgc_bt ...` for all CLI runs and `uv pip install` only for packages
- **Compatibility**: Existing 89 tests must keep passing and the MGC golden fixture must continue matching exactly
- **Research Gate**: Stop after each phase and wait for explicit instruction before proceeding
- **Git Discipline**: Commit and push after every phase

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Build a structured Python project with a CLI instead of notebooks or loose scripts | The user wants explicit reusable commands and maintainable code | Phase 1 delivered the `mgc_bt` package, TOML config, and CLI shell |
| Prioritize ingestion before backtesting and optimization | Clean data is the foundation for everything else | Phase 1 delivered the catalog workflow before any backtest or optimization work |
| Use separate `ingest`, `backtest`, and `optimize` commands | Enables focused daily workflows and avoids unnecessary reruns | Phase 1 established the CLI contract and implemented `ingest` |
| Use Nautilus Trader's event-driven `Strategy` architecture | Matches the engine's actual design and avoids invalid vectorized implementations | Phase 1 kept the foundation catalog-first and ready for Nautilus-native backtesting |
| Include commissions and slippage from v1 | Backtest trust matters more than optimistic raw signal results | Phase 2 implements commission, one-tick slippage, and next-bar timing through Nautilus-native venue/fill/latency configuration |
| Keep v1 to MGC futures, rule-based logic, and local Databento files only | Prevents scope creep while establishing a credible research baseline | Phase 1 filters the catalog to outright MGC futures contracts and local Databento files only |
| Keep Phase 4 optimization on the shared catalog-backed runner instead of forcing a low-level `BacktestEngine.reset()` rewrite | Nautilus supports `reset()` for in-memory repeated runs, but the full bars-plus-trades dataset is better matched to the high-level catalog-backed `BacktestNode` path | Phase 4 documents and preserves the high-level runner for optimization while keeping the decision explicit |
| Add shared preflight validation and a `health` command instead of separate ad hoc setup checks | Local repeatability depends more on actionable readiness feedback than on extra features | Phase 5 centralizes command checks and exposes one readiness summary surface |
| Retain a shared Nautilus log guard across repeated backtest runs | Repeated in-process `BacktestNode` runs can destabilize logging on this install if the guard is dropped between runs | Phase 5 keeps the runner stable for optimization reruns and holdout execution |
| Treat v1.1 as a research-integrity and reporting expansion, not a strategy rewrite | The user wants professional confidence tooling around the existing platform, with no change to the current strategy logic | v1.1 focuses on validation, reporting, visualization, and platform reuse layers |
| Prioritize research correctness over visualization polish and reusability if tradeoffs arise | A beautiful tearsheet is less valuable than statistically trustworthy results | v1.1 planning should favor correct walk-forward, Monte Carlo, and holdout workflows first |
| Generate tearsheets automatically from the existing `backtest` and `optimize` commands | Reporting should be part of the normal workflow rather than a separate manual step | v1.1 attached tearsheet generation to existing command paths |
| Keep walk-forward analysis inside `optimize` via a flag instead of creating a separate command | The current CLI structure should stay focused and explicit | v1.1 extended `optimize` rather than branching the workflow surface |
| Extract indicators into a reusable library without changing current strategy behavior | Platform reuse matters, but preserving validated strategy logic matters more | v1.1 kept indicator refactors behavior-preserving |
| Treat v1.2 as a gated research milestone instead of a straight implementation milestone | The human wants to review actual results after each phase before choosing the next step | Each v1.2 phase must stop and wait for explicit approval before proceeding |

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
*Last updated: 2026-04-09 for v1.2 milestone setup*
