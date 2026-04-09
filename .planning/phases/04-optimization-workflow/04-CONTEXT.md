# Phase 4: Optimization Workflow - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4 adds a repeatable Optuna-based optimization workflow on top of the existing catalog-backed MGC backtest system. This phase owns the optimization search space, trial execution policy, live progress reporting, study persistence and resume behavior, ranked result outputs, and automatic export of best-run plus holdout-evaluation artifacts. It does not change the core strategy rules, alter the Phase 2 reusable runner contract, or expand beyond the existing local single-machine research workflow.

</domain>

<decisions>
## Implementation Decisions

### Optimization architecture
- **D-01:** Phase 4 must keep using the shared in-process backtest function `run_backtest(settings, params) -> dict` rather than subprocess execution.
- **D-02:** The optimization workflow should build on the existing machine-readable backtest artifact and summary contracts rather than invent a separate reporting system.
- **D-03:** Optimization must remain local and single-machine; distributed orchestration stays out of scope for v1.

### Objective function
- **D-04:** Sharpe ratio is the primary Optuna objective.
- **D-05:** Apply a hard penalty and return `-10` if `total_trades < 30`.
- **D-06:** Apply a hard penalty and return `-10` if `max_drawdown_pct > 25`.
- **D-07:** If neither penalty triggers, return raw Sharpe ratio as the objective score.
- **D-08:** The purpose of the hard penalties is to prevent degenerate low-trade or excessive-drawdown parameter sets from appearing optimal.

### Search space scope
- **D-09:** The Optuna search space includes strategy parameters plus custom risk parameters.
- **D-10:** Native Nautilus `RiskEngineConfig` limits are not part of the optimization search space because they are infrastructure guardrails, not strategy behavior.
- **D-11:** The custom risk parameters to optimize are `max_loss_per_trade_dollars`, `max_daily_loss_dollars`, `max_consecutive_losses`, and `max_drawdown_pct`.
- **D-12:** `max_daily_trades` remains fixed at `10` and is not optimized.

### Trial budget and stopping policy
- **D-13:** Optimization uses a hybrid stopping rule: stop when either maximum trials or maximum runtime is reached.
- **D-14:** Default limits are `200` trials or `4` hours, whichever comes first.
- **D-15:** Both limits must be configurable under `[optimization]` in `settings.toml`.
- **D-16:** Add early stopping if the best Sharpe has not improved by more than `0.05` over the last `50` trials.

### Sampler and reproducibility
- **D-17:** Use the Optuna TPE sampler from trial 1; do not add a random baseline stage.
- **D-18:** The optimization seed must be configurable in `settings.toml` with default `42`.
- **D-19:** Every optimization run must log and persist the seed so the run is exactly reproducible.

### Date regime and evaluation honesty
- **D-20:** Use an in-sample optimization window plus a completely separate out-of-sample holdout evaluation window.
- **D-21:** The intended default split is approximately the first 4 years in-sample and the last 1 year holdout.
- **D-22:** Every optimization trial runs on the full configured in-sample window using auto-roll.
- **D-23:** The holdout window must never be touched during optimization trial scoring.
- **D-24:** After optimization completes, automatically run the best parameter set on the holdout window.
- **D-25:** Holdout outputs must be clearly labeled so they are never confused with in-sample optimization results.
- **D-26:** The date windows must be configurable under `[optimization]` as `in_sample_start`, `in_sample_end`, `holdout_start`, and `holdout_end`.

### Study persistence and resume
- **D-27:** Optimization must support study resume.
- **D-28:** Persist the Optuna study in SQLite at `results/optimization/optuna_storage.db`.
- **D-29:** The `optimize` CLI must support a `--resume` flag for continuing an interrupted study.
- **D-30:** The study name must be configurable so multiple named studies can coexist.

### Failure handling
- **D-31:** Failed trials should be recorded and optimization should continue.
- **D-32:** Failed trials must capture both the parameter set and the error details in `failed_trials.json`.
- **D-33:** Optuna should mark those trials as failed rather than crashing the whole optimization session.

### Output structure
- **D-34:** Use a hybrid output structure with an aggregated ranked table always written.
- **D-35:** The canonical output folder is `results/optimization/YYYY-MM-DD_HHMMSS/`.
- **D-36:** Refresh `results/optimization/latest/` after each completed optimization run.
- **D-37:** The output folder must contain:
  - `ranked_results.csv`
  - `optimization_summary.json`
  - `best_run/`
  - `top_10/`
  - `failed_trials.json`
- **D-38:** `best_run/` gets the full artifact bundle:
  - `summary.json`
  - `trades.csv`
  - `equity_curve.png`
  - `run_config.toml`
  - `holdout_results.json`
  - `holdout_equity_curve.png`
- **D-39:** `top_10/` excludes the best run and uses a light bundle for the remaining top 10 candidates:
  - `summary.json`
  - `equity_curve.png`

### Ranked results contract
- **D-40:** `ranked_results.csv` must include both the optimization objective and raw backtest metrics.
- **D-41:** Rank rows by `objective_score` first, then `sharpe_ratio`, then lower `max_drawdown_pct`.
- **D-42:** Required columns are:
  - `rank`
  - `trial_number`
  - `objective_score`
  - `sharpe_ratio`
  - `total_pnl`
  - `win_rate`
  - `max_drawdown_pct`
  - `total_trades`
  - one column per optimized parameter

### Summary and holdout outputs
- **D-43:** `optimization_summary.json` must include at minimum:
  - seed
  - number of completed trials
  - best params
  - runtime
- **D-44:** After optimization, automatically run a full backtest with the best in-sample parameters and export the full best-run bundle.
- **D-45:** Automatically run a holdout evaluation with the best parameters and persist:
  - `holdout_results.json`
  - `holdout_equity_curve.png`
- **D-46:** All optimization parameters must be included in the persisted `run_config.toml` so any result can be rerun manually.

### CLI behavior
- **D-47:** The `optimize` command must print live progress to the terminal.
- **D-48:** The live progress summary should show:
  - current trial number
  - best Sharpe so far
  - best params so far
  - estimated time remaining
- **D-49:** After optimization completes, warn in CLI output if holdout Sharpe is more than `0.3` below in-sample Sharpe.
- **D-50:** That warning is an explicit overfitting signal and should be surfaced immediately to the user.

### Carry-forward architecture constraints
- **D-51:** Phase 4 must preserve the catalog decode split whenever catalog-backed assumptions matter:
  - definitions use legacy Cython decoding
  - bars/trades use `as_legacy_cython=False`
- **D-52:** Phase 4 should continue using Nautilus native infrastructure as the foundation, extending it rather than reimplementing it.

### the agent's Discretion
- Exact module boundaries under `src/mgc_bt/optimization/` or equivalent
- Whether progress reporting is callback-based, wrapper-based, or uses Optuna hooks
- The exact JSON schema details inside `optimization_summary.json` and `failed_trials.json` beyond the locked required fields
- The exact mechanism used to produce ETA, as long as the CLI displays one

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing backtest and artifact contracts
- `.planning/phases/02-backtest-runner/02-CONTEXT.md` - Locked reusable runner and artifact expectations Phase 4 must build on
- `.planning/phases/02-backtest-runner/02-VERIFICATION.md` - Verified Phase 2 runner behavior and artifact bundle contract
- `.planning/phases/03-strategy-logic/03-CONTEXT.md` - Locked strategy and optimization-facing parameter names
- `.planning/phases/03-strategy-logic/03-05-PLAN.md` - Confirms risk parameters were intentionally preserved for Phase 4 reuse
- `.planning/phases/03-strategy-logic/03-05-SUMMARY.md` - Confirms native Nautilus risk plus custom risk split that Phase 4 must respect

### Nautilus backtest and execution references
- `nt_docs/concepts/backtesting.md` - Includes the current high-level backtest model and explicitly notes `BacktestEngine.reset()` as a parameter-optimization-friendly pattern
- `nt_docs/api_reference/backtest.md` - Current Nautilus 1.225.0 backtest API reference for config and result surfaces
- `nt_docs/concepts/execution.md` - Confirms native `RiskEngine` responsibilities so Phase 4 does not optimize infrastructure guardrails incorrectly
- `nt_docs/api_reference/risk.md` - Risk module reference supporting the Phase 3 native/custom risk split carried into optimization

### Project planning context
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `AGENTS.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mgc_bt/backtest/runner.py` - Existing in-process backtest primitive already returns structured dict results suitable for Optuna objective evaluation
- `src/mgc_bt/backtest/configuration.py` - Existing shared parameter-to-strategy wiring, including both strategy and custom risk parameters
- `src/mgc_bt/backtest/artifacts.py` - Existing timestamped artifact bundle logic and `latest/` refresh pattern to extend for optimization outputs
- `src/mgc_bt/cli.py` - Existing CLI shell already has an `optimize` command placeholder
- `src/mgc_bt/config.py` and `configs/settings.toml` - Existing TOML-backed typed config system ready to absorb optimization runtime and date-window settings

### Established Patterns
- The codebase already favors a thin CLI over reusable Python functions rather than separate subprocess workflows
- Backtest results are already represented as structured Python dictionaries and machine-readable files
- Parameter names were intentionally locked in Phase 3 to avoid refactors in Phase 4
- Native Nautilus infrastructure should remain the foundation; custom orchestration belongs around it, not instead of it

### Integration Points
- `src/mgc_bt/backtest/runner.py` is the core execution path every trial should call
- `src/mgc_bt/backtest/artifacts.py` is the obvious reference point for best-run and top-10 artifact persistence
- `src/mgc_bt/cli.py` is where `optimize` CLI arguments such as `--resume` will surface
- `results/` is already the established root for persisted outputs and should gain an `optimization/` subtree
- `tests/` currently covers ingestion, runner, artifacts, CLI, risk, indicators, and strategy behavior, giving Phase 4 clear places to add optimization-specific tests

</code_context>

<specifics>
## Specific Ideas

- The optimization workflow should feel like a first-class research command, not a script wrapped around console scraping.
- Holdout evaluation must be visibly separate from in-sample optimization so overfitting signals are hard to miss.
- The ranked table should be useful for manual review, not just for selecting the single best trial.
- Failed trials are expected in broad search spaces and should be treated as logged outcomes, not fatal errors.

</specifics>

<deferred>
## Deferred Ideas

- Walk-forward optimization is deferred; v1 uses a single in-sample plus holdout split.
- Native Nautilus infrastructure guardrails such as `RiskEngineConfig` limits are not optimization targets in Phase 4.
- Distributed or multi-machine optimization remains out of scope for v1.

</deferred>

---

*Phase: 04-optimization-workflow*
*Context gathered: 2026-04-09*
