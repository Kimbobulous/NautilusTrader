# Phase 4: Optimization Workflow - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 04-optimization-workflow
**Areas discussed:** Optimization objective, Search space scope, Trial budget and stopping policy, Sampler and reproducibility, Optimization output structure, Failure handling and resume, Optimization date regime, Trial execution scope, Ranked table columns and tie-breaking, Top 10 artifact depth

---

## Optimization objective

| Option | Description | Selected |
|--------|-------------|----------|
| Pure Sharpe | Optimize Sharpe ratio directly without extra penalties | |
| Sharpe with hard penalties | Sharpe remains primary, but degenerate low-trade or high-drawdown runs are penalized | ✓ |
| Multi-metric ranking | Combine several metrics into the primary objective | |

**User's choice:** Sharpe ratio with hard penalties. Return `-10` if `total_trades < 30` or if `max_drawdown_pct > 25`, otherwise return Sharpe ratio.
**Notes:** This is specifically to avoid degenerate solutions with only a few trades or unacceptable drawdown.

---

## Search space scope

| Option | Description | Selected |
|--------|-------------|----------|
| Strategy only | Optimize only strategy parameters | |
| Strategy + custom risk | Optimize strategy parameters plus custom session-level risk controls | ✓ |
| Strategy + custom risk + native risk engine | Also optimize native Nautilus risk-engine infrastructure guardrails | |

**User's choice:** Optimize strategy parameters plus custom risk parameters only.
**Notes:** Include `max_loss_per_trade_dollars`, `max_daily_loss_dollars`, `max_consecutive_losses`, and `max_drawdown_pct`. Keep `max_daily_trades` fixed at `10`. Do not optimize native `RiskEngineConfig` limits.

---

## Trial budget and stopping policy

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed trial count | Stop after a configured number of trials | |
| Time budget only | Stop after a configured runtime window | |
| Hybrid | Stop on max trials or max runtime, whichever comes first | ✓ |

**User's choice:** Hybrid stopping.
**Notes:** Default `200` trials or `4` hours. Add early stopping if best Sharpe has not improved by more than `0.05` in the last `50` trials. All must be configurable in `[optimization]`.

---

## Sampler and reproducibility

| Option | Description | Selected |
|--------|-------------|----------|
| TPE with fixed seed | Deterministic TPE-driven optimization from the start | ✓ |
| Random then TPE | Use a random baseline before switching to TPE | |
| Heavier optimizer | Use CMA-ES or a more advanced optimizer up front | |

**User's choice:** TPE with fixed seed.
**Notes:** Default seed `42`, configurable in settings, and every optimization run must persist the seed used.

---

## Optimization output structure

| Option | Description | Selected |
|--------|-------------|----------|
| Aggregated only | One ranked table plus summary metadata | |
| Per-trial bundles | Persist artifacts for every trial | |
| Hybrid | Aggregated ranking always, targeted artifact persistence for best/top/failures | ✓ |

**User's choice:** Hybrid output structure.
**Notes:** Required layout:
- `results/optimization/YYYY-MM-DD_HHMMSS/`
- `ranked_results.csv`
- `optimization_summary.json`
- `best_run/`
- `top_10/`
- `failed_trials.json`
- refresh `results/optimization/latest/`

---

## Failure handling and resume

| Option | Description | Selected |
|--------|-------------|----------|
| Continue on failures + resume | Log failed trials, continue optimization, and support persistent-study resume | ✓ |
| Fail fast | Stop the whole run on any trial error | |
| Continue without resume | Ignore failures but do not support study persistence | |

**User's choice:** Continue on failures and support resume.
**Notes:** Persist study in `results/optimization/optuna_storage.db`, support `--resume`, and keep study name configurable.

---

## Optimization date regime

| Option | Description | Selected |
|--------|-------------|----------|
| Full-range only | Optimize directly on the entire available range | |
| In-sample + holdout | Optimize on one window, then evaluate best params on a separate holdout window | ✓ |
| Walk-forward | Use rolling train/test windows | |

**User's choice:** In-sample plus automatic holdout evaluation.
**Notes:** Use approximately first 4 years in-sample and last 1 year holdout by default. Persist configurable `in_sample_start`, `in_sample_end`, `holdout_start`, and `holdout_end`. After optimization, automatically run holdout evaluation and save `holdout_results.json` and `holdout_equity_curve.png`.

---

## Trial execution scope

| Option | Description | Selected |
|--------|-------------|----------|
| Full configured in-sample range every trial | Every trial sees the same full in-sample range | ✓ |
| Shorter optimization window | Use a reduced window for faster trials | |
| Dual-mode | Support both full and shortened windows in Phase 4 | |

**User's choice:** Every trial uses the full configured in-sample date range.
**Notes:** Use auto-roll for every trial. No shortcut windows during optimization. The separate full rerun is the holdout evaluation after optimization.

---

## Ranked table columns and tie-breaking

| Option | Description | Selected |
|--------|-------------|----------|
| Objective score only | Rank and persist only the objective score and winner | |
| Sharpe only | Rank by Sharpe after penalties | |
| Objective + raw metrics | Persist both objective score and detailed metrics with explicit tie-breakers | ✓ |

**User's choice:** Include both objective score and raw metrics.
**Notes:** Rank by `objective_score`, then `sharpe_ratio`, then lower `max_drawdown_pct`. Required CSV columns are `rank`, `trial_number`, `objective_score`, `sharpe_ratio`, `total_pnl`, `win_rate`, `max_drawdown_pct`, `total_trades`, plus one column per optimized parameter.

---

## Top 10 artifact depth

| Option | Description | Selected |
|--------|-------------|----------|
| Light bundles for all top 10 | Summary plus equity curve only | |
| Full bundles for all top 10 | Persist full backtest outputs for each top trial | |
| Best full, top 10 light | Best run gets full bundle, remaining top 10 get light bundles | ✓ |

**User's choice:** Best run gets the full bundle, remaining top 10 get light bundles.
**Notes:** Best run must include `summary.json`, `trades.csv`, `equity_curve.png`, `run_config.toml`, `holdout_results.json`, and `holdout_equity_curve.png`. Top 10 excluding best get `summary.json` and `equity_curve.png`.

---

## Additional implementation notes

**User's choice:** Add live CLI progress and overfitting warning behavior.
**Notes:** The `optimize` command should print current trial number, best Sharpe so far, best params so far, and estimated time remaining. After completion, warn if holdout Sharpe is more than `0.3` below in-sample Sharpe.

## the agent's Discretion

- Exact module boundaries for optimization orchestration, persistence helpers, and CLI progress reporting
- The specific Optuna callback/hook design used to implement early stopping and ETA
- The precise summary schema beyond the locked required fields

## Deferred Ideas

- Walk-forward optimization
- Optimizing native Nautilus `RiskEngineConfig` infrastructure guardrails
- Distributed optimization
