# Phase 7: Analytics and Audit Layer - Research

**Date:** 2026-04-09
**Phase:** 07 - Analytics and Audit Layer
**Status:** Complete

## Research Goal

Determine the safest way to add Phase 7 analytics and audit outputs on top of the existing backtest and optimization platform without changing strategy behavior, duplicating Nautilus-native reporting, or blocking core result persistence.

## Current Reusable Assets

### Native Nautilus reporting already in use
- The current backtest runner already follows Nautilus-native post-run reporting via:
  - `engine.trader.generate_order_fills_report()`
  - `engine.trader.generate_positions_report()`
  - `engine.trader.generate_account_report(venue=...)`
- This is consistent with local docs in:
  - `nt_docs/concepts/reports.md`
  - `nt_docs/concepts/backtesting.md`
  - `nt_docs/getting_started/backtest_low_level.py`
- Phase 7 should build analytics from those reports and the already-normalized result payloads, not introduce a parallel execution-reporting path.

### Canonical backtest result pipeline
- `src/mgc_bt/backtest/runner.py` is the single backtest execution entry point and already normalizes parameters, runs Nautilus, generates native reports, and converts them into project-level summaries.
- `src/mgc_bt/backtest/results.py` is already the canonical transformation layer from Nautilus reports into:
  - `trade_log`
  - `equity_curve`
  - headline metrics like Sharpe, win rate, and drawdown
- `src/mgc_bt/backtest/artifacts.py` already owns result-folder layout, manifest generation, `latest/` refresh, and `summary.json` / `trades.csv` / `equity_curve.png` writing.

### Existing optimization output pipeline
- `src/mgc_bt/optimization/results.py` already owns optimization-folder artifact writing and is the natural home for:
  - parameter sensitivity output
  - optimization-side analytics bundles derived from the best-run trade set
- `src/mgc_bt/optimization/study.py` already attaches optional Phase 6 analysis after optimization and returns a machine-readable summary payload to the CLI.
- Phase 6 outputs already exist under:
  - `walk_forward/`
  - `monte_carlo/`
  - `stability/`
- Phase 7 should complement those outputs, not recompute them.

### Existing strategy explainability hooks
- `src/mgc_bt/backtest/strategy.py` already has useful internal decision structure:
  - explicit `PULLBACK_ARMED` state
  - core trigger booleans
  - optional confirmation logic
  - explicit entry/exit reasons such as `entry:long`, `atr_stop_long`, `hard_flip_short`, and `risk_halt`
- This is the cleanest insertion point for a detailed audit log because the necessary signal state exists before orders are submitted.

## Architectural Findings

### Best module boundary for Phase 7

The cleanest shape is a dedicated analytics layer that sits after canonical result generation, plus a small audit capture hook inside the strategy runtime:

- `backtest/strategy.py`
  - capture signal-state audit rows while bars are processed
  - attach executed-trade enrichments such as session and volatility cluster at entry
- New analytics module(s), likely under `src/mgc_bt/analytics/` or `src/mgc_bt/backtest/analytics.py`
  - trade breakdown aggregation
  - drawdown episode extraction
  - underwater curve derivation
  - CSV writing helpers for analytics bundles
- `backtest/artifacts.py`
  - invoke analytics generation after the core backtest bundle is safely written
  - extend `manifest.json`
- `optimization/results.py` or a small optimization analytics helper
  - derive `parameter_sensitivity.csv` from `ranked_results.csv` or trial rows
  - write best-run trade breakdown analytics under optimization `analytics/`

This keeps core execution and analytics separate:
- execution stays in `runner.py`
- canonical summary remains in `backtest/results.py`
- post-processing analytics live in an attachable, failure-tolerant layer

### Why analytics should not be computed only from `summary.json`

The current `summary.json` is top-line only. Phase 7 needs:
- episode-level drawdown transitions
- per-bar signal-state audit rows
- per-trade entry context like session and volatility regime
- parameter-level bucketed trial analysis

That means Phase 7 must work from richer inputs than the existing summary:
- backtest trade log
- equity curve
- strategy runtime state during signal evaluation
- Optuna trial metadata / ranked results

### Filesystem-first contract is already the right choice

The user’s Phase 7 and Phase 8 requirements align with the current project direction:
- analytics should be generated once
- saved under `analytics/`
- later tearsheets should consume the saved artifacts without rerunning the backtest

The existing artifact system already supports this pattern well via timestamped run folders and manifests.

## Key Risks and Pitfalls

### 1. Audit logging is not available today
- The current strategy returns `StrategyDecision` objects but does not persist full signal snapshots.
- There is no existing audit event store or sink in `MgcSignalEngine`.
- Phase 7 will need a non-invasive audit collector that records:
  - armed-state bar context
  - trigger booleans
  - rejection reasons
  - trade lifecycle enrichment

Risk:
- If audit capture is bolted on too late in the artifact pipeline, required per-bar context will already be lost.

Implication for planning:
- One plan should focus specifically on introducing a stable audit data model and capture path inside strategy/runtime code.

### 2. Large five-year audit logs can become memory-heavy
- The existing code often uses pandas DataFrames for final report shaping.
- The user explicitly does not want a giant in-memory dataframe for `audit_log.csv`.

Risk:
- Building all audit rows in a huge dataframe before writing could become the largest memory cost in the entire system.

Implication for planning:
- Audit persistence should use streaming CSV writing or chunked record writing.
- The strategy/runtime side may still store structured rows in memory for shorter runs, but Phase 7 should bias toward streaming-friendly interfaces.

### 3. Backtest analytics must not block core output
- Current backtest and optimization artifact writing assumes the main result bundle is authoritative.
- The user locked a non-blocking requirement: analytics can warn and fail, but the run still succeeds.

Risk:
- If analytics are written inline before the core manifest and summary are finalized, a Phase 7 bug could make normal backtests fail.

Implication for planning:
- Core bundle first, analytics second, manifest update last.
- Analytics attachment should be wrapped in warning-producing error handling.

### 4. Session breakdown totals must reconcile with headline metrics
- Phase 7 wants multiple breakdown views:
  - session
  - volatility regime
  - month
  - year
  - weekday
  - hour
- If these are computed from different trade subsets or mixed timestamps, totals can drift from the canonical trade log.

Implication for planning:
- All breakdowns should derive from one normalized trade-level analytics frame built from canonical `trade_log` plus enriched metadata.

### 5. Parameter sensitivity should not duplicate Phase 6 stability analysis
- Phase 6 stability currently re-evaluates parameter neighborhoods and uses Optuna importance.
- Phase 7 sensitivity is explicitly lighter-weight and must use existing optimization results only.

Implication for planning:
- Keep Phase 7 parameter sensitivity separate from `stability.py`.
- It is best implemented as a new post-processing analysis over completed trial results / ranked CSV rows.

## Important Mismatches Between Desired Outputs and Current Structures

### Trade log is currently too thin for Phase 7
Current `trade_log` in `src/mgc_bt/backtest/results.py` includes:
- instrument ID
- entry side
- quantity
- open/close timestamps
- average open/close prices
- realized PnL
- realized return
- commissions
- slippage

Missing for Phase 7:
- direction normalized as long/short
- exit reason
- bars held
- max favorable excursion
- max adverse excursion
- session at entry
- volatility cluster at entry

Implication:
- Trade enrichment must happen either in the strategy/runtime path or in an additional lifecycle summary structure that survives to artifact writing.

### Drawdown summary today is only headline depth
Current backtest summary computes:
- `max_drawdown`
- `max_drawdown_pct`

Missing for Phase 7:
- drawdown episodes
- recovery durations
- percentage of time in drawdown
- underwater series

Implication:
- `backtest/results.py` is the right place to add reusable drawdown helpers because it already owns canonical equity-curve derivation.

### Optimization currently has no analytics/ directory
- Optimization folders today already contain study outputs and research-integrity outputs, but not the Phase 7 `analytics/` subtree.

Implication:
- Phase 7 needs to define a shared analytics directory contract that both backtest and optimization writers follow.

## Native Nautilus-First Considerations

### What Nautilus should keep owning
- execution simulation
- order lifecycle and fill handling
- native account/fill/position reports
- backtest result generation

### What should remain custom in this project
- strategy-specific signal audit rows
- project-specific performance breakdown CSVs
- drawdown episode summaries persisted in this repo’s artifact layout
- parameter sensitivity over Optuna trial results

Conclusion:
- Phase 7 should extend Nautilus outputs, not attempt to replace `ReportProvider` or native reporting helpers.

## Testing Implications

### Existing tests that Phase 7 will likely extend
- `tests/test_backtest_artifacts.py`
  - should grow assertions for `analytics/` files and manifest inclusion
- `tests/test_optimization_results.py`
  - should grow assertions for optimization-side `analytics/parameter_sensitivity.csv` and best-run breakdowns
- `tests/test_cli.py`
  - should verify that analytics failures warn without causing command failure

### New tests likely needed
- audit log generation tests
  - verify expected columns
  - verify armed-state rejection rows are present
  - verify trade rows include required enrichments
- drawdown analytics tests
  - verify episode segmentation and recovery calculations on synthetic equity series
- breakdown aggregation tests
  - verify buckets and metric reconciliation
- parameter sensitivity tests
  - verify bucketed Sharpe-range and Pearson correlation outputs from synthetic ranked trial rows
- non-blocking analytics failure tests
  - verify a simulated analytics exception still produces the core result bundle

### Regression risk to protect
- Existing backtest and optimization artifact contracts are already covered by tests.
- Phase 7 should extend those contracts additively, not mutate existing filenames or summary fields in a breaking way.

## Validation Architecture

Phase 7 should use a two-level validation strategy:

### Level 1: Fast task-level checks
- targeted pytest runs for analytics helper units after each task
- file-existence and manifest assertions for newly added outputs
- synthetic small-result fixtures for drawdown and sensitivity math

### Level 2: End-to-end artifact checks
- a bounded backtest fixture should verify:
  - core bundle still writes
  - `analytics/` is created
  - `audit_log.csv`, `drawdown_episodes.csv`, `underwater_curve.csv`, and breakdown CSVs exist
  - `manifest.json` includes analytics files
- a bounded optimization fixture should verify:
  - `analytics/parameter_sensitivity.csv` exists
  - best-run trade breakdown analytics exist
  - no regression in Phase 6 outputs

### Critical validation rule
- Analytics generation failures must be tested explicitly as non-blocking behavior.
- This is a contract requirement, not just a nice-to-have.

## Planning Guidance

Phase 7 should likely split into plans around these seams:
1. Audit capture and trade enrichment
2. Backtest analytics generation and drawdown/breakdown persistence
3. Optimization-side parameter sensitivity and best-run analytics attachment
4. Non-blocking integration, manifests, and regression coverage

That split fits the actual codebase well because these responsibilities touch different layers and have different regression risks.

## Recommendation

Plan Phase 7 around additive analytics modules and a lightweight strategy audit capture layer. Keep:
- `runner.py` unchanged as the core execution boundary
- `backtest/results.py` as the canonical metric source
- `backtest/artifacts.py` and `optimization/results.py` as the attachment points for analytics bundles

Do not make Phase 7 a broad refactor of result structures. The safest route is to enrich existing outputs and write new analytics artifacts alongside them.

## RESEARCH COMPLETE
