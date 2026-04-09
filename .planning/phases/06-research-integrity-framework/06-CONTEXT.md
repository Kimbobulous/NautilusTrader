# Phase 6: Research Integrity Framework - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 6 extends the existing optimization pipeline with statistically trustworthy validation workflows. It must add walk-forward optimization, a proper train/validate/test contract, Monte Carlo analysis, and parameter-stability analysis on top of the current `optimize` flow without changing the current strategy behavior or breaking the existing non-walk-forward optimization path.

</domain>

<decisions>
## Implementation Decisions

### Walk-forward design
- **D-01:** Walk-forward uses fixed time windows rather than fixed folds.
- **D-02:** Default walk-forward windows are: 12-month training, 3-month validation, 3-month test, with a 3-month step size.
- **D-03:** Each walk-forward window re-optimizes on the training slice, selects the best parameter set on validation, then records out-of-sample performance on the test slice.
- **D-04:** Any walk-forward window with fewer than `50,000` training bars is skipped rather than forced through.
- **D-05:** Any test window with fewer than `10` out-of-sample trades is flagged as inconclusive and must not be counted as a loss.
- **D-06:** The aggregate walk-forward result is based on concatenated out-of-sample behavior, and aggregated Sharpe must be computed as a time-weighted average across test windows rather than as a simple arithmetic mean.

### Three-way split and final test contract
- **D-07:** Existing `optimize` behavior without flags stays intact and continues using the current in-sample/holdout contract.
- **D-08:** Adding `--walk-forward` activates the new train/validate/test workflow; it is an extension of `optimize`, not a new command.
- **D-09:** The three-way split means training data is used for Optuna optimization, validation data is used to select among candidate parameter sets, and the final test set is never touched during parameter selection.
- **D-10:** The final protected test set is the last 6 months of available data.
- **D-11:** Final test evaluation is hidden by default and only runs when explicitly requested with `--final-test`, with a clear warning before execution.

### Monte Carlo methodology
- **D-12:** Phase 6 must implement two Monte Carlo methods:
  - trade-sequence permutation: shuffle realized trade order 1000 times by default and recompute equity and Sharpe
  - bootstrap resampling: resample trades with replacement 1000 times by default to create synthetic equity curves
- **D-13:** Monte Carlo outputs must include a p-value for whether results beat random permutation, percentile bands at 5th/25th/50th/75th/95th percentiles for Sharpe and final PnL, a fan-chart-ready confidence output, and a simple pass/fail verdict at the 95% confidence level.
- **D-14:** Monte Carlo simulation count is configurable under `[monte_carlo]` in `settings.toml`, with default `1000`.

### Parameter stability analysis
- **D-15:** Phase 6 must produce two stability outputs.
- **D-16:** Output 1 is a 2D heatmap around the optimal region using the two most important parameters as determined by Optuna's built-in parameter importance (`fanova`) unless Nautilus already provides a clearly better native facility.
- **D-17:** Output 2 is a neighborhood robustness score based on independent `+/-10%` and `+/-20%` perturbations of each optimized parameter around the best parameter set.
- **D-18:** Neighborhood robustness is reported as the percentage of neighboring parameter sets that still achieve Sharpe greater than `0.5`.
- **D-19:** A strategy should be interpreted as robust when at least `70%` of those neighboring parameter sets remain profitable by that threshold.

### Runtime and output policy
- **D-20:** Walk-forward runs automatically when `optimize` is invoked with `--walk-forward`.
- **D-21:** Monte Carlo and stability analysis do not change the default `optimize` path. They run automatically for walk-forward research runs, and for non-walk-forward optimization they only run when explicitly requested with `--monte-carlo` and `--stability`.
- **D-22:** Walk-forward terminal progress must show current window number, window date range, in-sample Sharpe, validation Sharpe, out-of-sample Sharpe, and cumulative out-of-sample performance so far.
- **D-23:** Walk-forward outputs are saved under `results/optimization/YYYY-MM-DD_HHMMSS/walk_forward/` with:
  - `window_results.csv`
  - `aggregated_summary.json`
  - `equity_curve.png`
  - `params_over_time.csv`
- **D-24:** Monte Carlo and stability outputs live alongside the existing optimization outputs rather than in a separate command or results root.
- **D-25:** Before starting, the system should warn if estimated runtime exceeds 30 minutes based on early trial timing and should print an estimated completion time.

### Configuration and validation rules
- **D-26:** All new settings must follow the existing typed TOML config pattern and must be validated at load time.
- **D-27:** New Phase 6 settings belong in dedicated config sections rather than being stuffed into the current `[optimization]` section:
  - `[walk_forward]` for rolling-window settings
  - `[monte_carlo]` for simulation settings
- **D-28:** Phase 6 must preserve the milestone-wide rule that nothing breaks the existing 47 passing tests or changes current strategy behavior.

### the agent's Discretion
- Exact internal module boundaries for walk-forward orchestration, Monte Carlo utilities, and stability-analysis helpers
- Exact runtime-estimation formula, as long as it produces an actionable warning before long runs
- Exact shape of intermediate data structures, as long as the locked outputs and CLI behaviors are preserved

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and scope
- `.planning/PROJECT.md` - v1.1 milestone goal, native-first principle, backward-compatibility requirement, and CLI/tearsheet constraints
- `.planning/REQUIREMENTS.md` - Phase 6 requirements `INT-01` through `INT-04`
- `.planning/ROADMAP.md` - Phase 6 goal and success criteria
- `.planning/STATE.md` - current milestone state and carry-forward concerns

### Existing optimization implementation
- `src/mgc_bt/optimization/study.py` - current `optimize` orchestration, Optuna study lifecycle, progress callbacks, and holdout reruns
- `src/mgc_bt/optimization/objective.py` - current objective scoring path through `run_backtest(settings, params)`
- `src/mgc_bt/optimization/results.py` - current optimization result persistence and manifest patterns
- `src/mgc_bt/optimization/export.py` - current best-run and holdout export flow
- `src/mgc_bt/config.py` - typed TOML config loader and validation patterns
- `configs/settings.toml` - current optimization/backtest configuration structure that Phase 6 must extend

### Existing backtest foundation
- `src/mgc_bt/backtest/runner.py` - shared reusable backtest entry point that all research workflows must continue to use
- `src/mgc_bt/backtest/artifacts.py` - existing artifact and manifest persistence patterns
- `src/mgc_bt/backtest/results.py` - current backtest summary contracts that future analysis will build on

### Nautilus and analysis references
- `nt_docs/concepts/backtesting.md` - high-level vs low-level backtest APIs, repeated-run guidance, `BacktestNode` vs `BacktestEngine.reset()`, and related reporting/backtest concepts
- `nt_docs/api_reference/backtest.md` - installed Nautilus backtest module reference surface

### Test and contract protection
- `tests/test_optimize_objective.py` - current optimization-objective contracts
- `tests/test_optimization_results.py` - current optimization export and persistence expectations
- `tests/test_cli.py` - current CLI behavior that Phase 6 must extend without regression

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mgc_bt/optimization/study.py`: existing Optuna orchestration, progress callbacks, early stopping, SQLite persistence, and best-run rerun flow that Phase 6 should extend rather than replace
- `src/mgc_bt/optimization/objective.py`: current in-process optimization execution path through `run_backtest(settings, params)`; walk-forward should still route through the same runner contract
- `src/mgc_bt/optimization/results.py`: reusable CSV/JSON/manifest writing patterns for new walk-forward, Monte Carlo, and stability outputs
- `src/mgc_bt/config.py`: established typed dataclass config model and validation layer for adding `[walk_forward]` and `[monte_carlo]`
- `src/mgc_bt/cli.py`: existing `optimize` entry point and flag style; Phase 6 should extend this interface rather than create parallel commands

### Established Patterns
- Optimization already uses Optuna with a single study orchestration surface and machine-readable artifact outputs; Phase 6 should keep that shape
- Result bundles already use timestamped canonical directories, optional `latest/` refresh, and `manifest.json`; new Phase 6 outputs should follow the same persistence conventions
- The platform is native-first with Nautilus: use existing catalog-backed backtest infrastructure and extend around it rather than reimplementing simulation logic
- Current config loading is strict and TOML-typed; new research settings must validate early and fail with clear config errors

### Integration Points
- `optimize` CLI flow in `src/mgc_bt/cli.py`
- study orchestration in `src/mgc_bt/optimization/study.py`
- backtest execution via `src/mgc_bt/backtest/runner.py`
- optimization result export via `src/mgc_bt/optimization/results.py` and `src/mgc_bt/optimization/export.py`

</code_context>

<specifics>
## Specific Ideas

- Walk-forward should feel like a serious research mode layered onto `optimize`, not a separate tool or side workflow.
- The final test set must stay hidden until explicitly requested because the user wants a genuinely untouched evaluation slice.
- Monte Carlo should answer "is this edge real or just fortunate sequencing?" rather than merely adding decorative charts.
- Stability analysis should distinguish smooth hills from sharp spikes around the winner, with Optuna parameter importance driving which heatmaps matter most.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 6 scope.

</deferred>

---

*Phase: 06-research-integrity-framework*
*Context gathered: 2026-04-08*
