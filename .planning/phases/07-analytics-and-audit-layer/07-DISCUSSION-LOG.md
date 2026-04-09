# Phase 7: Analytics and Audit Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 07-analytics-and-audit-layer
**Areas discussed:** Trade audit log shape, performance breakdown definitions, drawdown analysis contract, parameter sensitivity methodology, output structure

---

## Trade audit log shape

| Option | Description | Selected |
|--------|-------------|----------|
| Executed trades only | Log only filled trades and exits | |
| Full signal audit | Log every considered setup plus executed trades | x |
| Minimal explainability | Log high-level reasons but not indicator state | |

**User's choice:** Full signal audit.
**Notes:** For every `PULLBACK_ARMED` bar, persist timestamp, bar OHLCV, indicator state, trigger booleans, optional confirmation count, and whether an entry fired or was rejected. For executed trades, also capture entry/exit timestamps and prices, direction, PnL, exit reason, MFE, MAE, bars held, volatility cluster at entry, and session at entry. Save as `analytics/audit_log.csv`. Because five-year runs will be large, write efficiently rather than building a giant dataframe in memory.

---

## Performance breakdown definitions

| Option | Description | Selected |
|--------|-------------|----------|
| Coarse breakdowns | Month/year only | |
| Standard trading slices | Session, regime, month, year | |
| Full breakdown suite | Session, regime, month, year, weekday, and hour | x |

**User's choice:** Full breakdown suite.
**Notes:** Session buckets are locked as `rth`, `asian`, `london`, and `globex_overnight` with UTC ranges. Volatility regime uses the Adaptive SuperTrend cluster at trade entry (`1/2/3`). Every breakdown must compute trade count, win rate, total PnL, average PnL per trade, Sharpe ratio, and max drawdown. Save each breakdown as a separate CSV under `analytics/breakdowns/`.

---

## Drawdown analysis contract

| Option | Description | Selected |
|--------|-------------|----------|
| Summary only | Persist only max drawdown and a few top-line stats | |
| Episode table only | Persist episode detail without merged summary metrics | |
| Full drawdown package | Persist episodes, summary metrics, and underwater curve | x |

**User's choice:** Full drawdown package.
**Notes:** Each drawdown episode must include episode/recovery timing, duration in bars and days, drawdown depth in percent and dollars, and whether recovery completed before the run ended. Save episodes to `analytics/drawdown_episodes.csv`, underwater series to `analytics/underwater_curve.csv`, and merge summary metrics into the existing `summary.json`.

---

## Parameter sensitivity methodology

| Option | Description | Selected |
|--------|-------------|----------|
| New backtests around the winner | Re-run nearby parameter points to estimate sensitivity | |
| Trial-result reuse | Use existing Optuna results only | x |
| Model-based approximation | Fit a surrogate model over the search space | |

**User's choice:** Use existing Optuna trial results only.
**Notes:** For each parameter, bucket completed trials into five equal-width bins, compute the range of mean Sharpe across bins, and compute Pearson correlation with objective score. Save `parameter_name`, `correlation_with_objective`, `sharpe_range_across_buckets`, and `most_sensitive` in `analytics/parameter_sensitivity.csv`, with `most_sensitive` assigned to the top three parameters by Sharpe-range sensitivity.

---

## Output structure

| Option | Description | Selected |
|--------|-------------|----------|
| Separate analytics command | Generate analytics later as a detached workflow | |
| Inline analytics bundle | Generate analytics automatically under each run folder | x |
| Mixed manual/automatic | Auto-generate some files and leave others to manual export | |

**User's choice:** Inline analytics bundle.
**Notes:** All Phase 7 analytics live under `analytics/` inside the existing timestamped backtest or optimization result folder. Backtests get the full audit, drawdown, underwater, and breakdown bundle. Optimization runs get `parameter_sensitivity.csv` plus the same breakdown structure using best-run trades. Phase 8 tearsheets must consume these filesystem artifacts directly. Analytics generation should warn and continue on failure, and all generated files must be listed in `manifest.json`.

---

## the agent's Discretion

- Exact internal code organization for analytics capture and aggregation
- Exact row shape used to mix armed-state audit rows with executed-trade rows in one CSV
- Exact non-blocking warning wording for analytics generation failures

## Deferred Ideas

None.
