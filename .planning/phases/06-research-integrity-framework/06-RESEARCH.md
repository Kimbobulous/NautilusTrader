# Phase 6 Research

## Executive Recommendation

Plan Phase 6 as an orchestration and contract extension on top of the current `optimize` flow, not as a rewrite of optimization or backtesting.

The safest shape is:
- keep the existing default `optimize` path unchanged
- add `--walk-forward` as an opt-in mode
- add `--final-test`, `--monte-carlo`, `--stability`, `--skip-monte-carlo`, and `--skip-stability` as explicit flags
- reuse `run_backtest(settings, params)` everywhere for evaluation
- persist new research artifacts alongside the current optimization outputs using additive schemas

That keeps the current 47-test baseline stable while adding statistically stronger validation around it.

## What You Need To Know Before Planning

- The current optimizer is a single Optuna study with one in-sample objective and a post-study holdout rerun.
- `objective.py` should stay the single-run scoring contract. Walk-forward and validation logic should live above it.
- `backtest/runner.py` already provides the reusable catalog-backed execution entry point, so Phase 6 should layer around that instead of introducing a new execution engine.
- The project already stores rich backtest outputs such as `trade_log` and `equity_curve`, which is enough to drive Monte Carlo and later tearsheets without rerunning the strategy.
- Phase 6 is mostly about trust, leakage control, and result shape, not new trading logic.

## Standard Stack

- `nautilus_trader` high-level backtesting via `BacktestNode` stays the foundation for repeated runs.
- `run_backtest(settings, params)` remains the one reusable evaluation primitive.
- Optuna remains the study engine for optimization and parameter importance.
- `optuna.importance.get_param_importances()` with the default `FanovaImportanceEvaluator` is the right native-first choice for parameter stability.
- `argparse` remains the CLI layer, extended in place.
- Typed dataclass config loading in `src/mgc_bt/config.py` remains the config pattern.

## Architecture Patterns

### Walk-forward

- Treat walk-forward as a coordinator around repeated optimization runs.
- For each rolling window, run a training optimization pass, rerun the shortlisted candidates on validation, then score the selected parameters on the test slice.
- Keep window orchestration outside `compute_objective_score()` and outside the default `run_optimization()` path.
- Aggregate walk-forward results from the per-window out-of-sample slices, not from the training metrics.
- Use time-based windows, not fold-count abstractions, because the requirement and context are calendar-driven.

### Final Test

- Keep the final test slice completely hidden by default.
- Only run it when `--final-test` is passed.
- Emit a clear warning before the hidden test is touched.
- Do not let validation or parameter selection see the final test data.

### Monte Carlo

- Use the realized `trade_log` from backtest or optimization results as the input source.
- Do not rerun strategy backtests for Monte Carlo.
- Run both permutation and bootstrap analysis from the same trade ledger so the outputs are comparable.
- Seed the random generator from config so the analysis is reproducible.

### Parameter Stability

- Use Optuna fANOVA to identify the two most important parameters.
- Re-run actual backtests on a small grid around the best region rather than building a surrogate surface.
- Evaluate neighborhood robustness by perturbing the best parameter set at `+/-10%` and `+/-20%`.
- Keep the heatmap and robustness score additive to the study output instead of replacing the ranked results.

## Don't Hand-Roll

- Do not build a new simulation engine for validation.
- Do not replace Nautilus execution with pandas-side replay.
- Do not create a separate walk-forward command when the requirement is to extend `optimize`.
- Do not mutate the existing objective contract to make it aware of validation/test splits.
- Do not re-implement parameter importance with custom statistics when Optuna already provides a native evaluator.
- Do not derive Monte Carlo from equity curve resampling if the trade log is available; trade-level resampling is cleaner and easier to explain.

## Result Contracts

### Preserve Existing Output Shape

- Keep current optimization return keys intact.
- Add new fields only when the new mode is enabled.
- Keep `ranked_results.csv`, `optimization_summary.json`, `run_config.toml`, and `manifest.json` working as they do now.

### Additive Research Schemas

- `walk_forward/window_results.csv` should describe each window and its status.
- `walk_forward/aggregated_summary.json` should contain the combined out-of-sample summary.
- `walk_forward/equity_curve.png` should visualize the stitched OOS curve.
- `walk_forward/params_over_time.csv` should capture parameter drift by window.
- Monte Carlo JSON should include the sample count, percentiles, p-value, and pass/fail verdict.
- Stability JSON should include the top parameter pair, heatmap grid data, and neighborhood robustness score.

### Fields That Will Help Phase 8

- `schema_version`
- `run_type`
- `analysis_type`
- `window_id`
- `train_start`, `train_end`
- `validate_start`, `validate_end`
- `test_start`, `test_end`
- `selected_trial_number`
- `selected_params`
- `status`
- `skipped_reason`
- `inconclusive`
- `percentiles`
- `equity_curve`
- `trade_log`

Those fields will make the later Plotly tearsheet phase much easier because the plots can consume one stable machine-readable schema instead of scraping text summaries.

## Config And CLI

- Add dedicated top-level config sections for `[walk_forward]` and `[monte_carlo]`.
- Keep the existing `[optimization]` section as the source of the default non-walk-forward path.
- Validate all new config fields at load time in the same style as the current config loader.
- Add CLI flags rather than new commands.
- Keep `optimize` behavior identical when no new flags are passed.
- Make final-test gating explicit so hidden evaluation cannot happen accidentally.

## Optuna fANOVA Constraints

- `get_param_importances()` works on completed trials.
- If there are no completed trials, it cannot produce a useful result.
- If you pass a `params` list, Optuna only considers completed trials that contain all of those params.
- The default evaluator is fANOVA, which is the right fit here because the search space is fixed and fully unconditional.
- fANOVA can become slow at very high trial counts, so compute it once per run and cache the result in the run artifacts.

For this phase, fANOVA is sufficient. A custom importance implementation would add maintenance burden without a clear benefit.

## Common Pitfalls

- The biggest risk is leaking final-test information into model selection.
- The second biggest risk is turning walk-forward into a huge runtime multiplier by rerunning too many candidates per window.
- The third biggest risk is changing default optimize behavior while adding flags.
- Another risk is treating inconclusive windows as losses instead of explicitly excluding them from failure accounting.
- Another risk is writing only summary metrics and not enough structured data for tearsheet work later.
- Another risk is computing Monte Carlo on timestamps rather than trade order, which makes interpretation harder.

## Tests To Protect

- Keep the current optimize CLI tests green when no new flags are used.
- Add config validation tests for the new sections and timestamps.
- Add CLI parsing tests for the new flags.
- Add orchestration tests that monkeypatch `run_backtest()` and confirm walk-forward selection flow.
- Add Monte Carlo tests with fixed seeds and deterministic sample summaries.
- Add stability tests that confirm fANOVA output is used and gracefully skipped when insufficient completed trials exist.
- Add hidden final-test gating tests to prove the test slice is untouched unless explicitly requested.

## Suggested Plan Slices

1. Add config and CLI flags first, with zero behavior change when the flags are absent.
2. Add a walk-forward orchestrator that reuses `run_backtest()` and emits the new machine-readable window outputs.
3. Add Monte Carlo generation from existing trade logs with deterministic seeding and persisted summaries.
4. Add fANOVA-based stability analysis plus local perturbation reruns around the best parameter set.
5. Add final-test gating and the runtime warning path.
6. Add additive tests for each new contract while verifying the current optimize path stays unchanged.

## Bottom Line

Phase 6 should be planned as a layered research-integrity wrapper around the current optimizer:

- default optimize stays the same
- walk-forward is opt-in orchestration
- Monte Carlo and stability are analysis layers on already-produced results
- they should auto-run for `--walk-forward` research runs, but the default no-flag optimize path should stay unchanged unless explicitly opted in
- final test stays hidden unless explicitly unlocked
- outputs should be structured now so Phase 8 can build tearsheets without another refactor
