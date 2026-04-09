# Phase 7: Analytics and Audit Layer - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 7 adds explainability and analysis on top of the shipped backtest and optimization workflows. It must generate a full signal-and-trade audit trail, richer performance breakdowns, and deeper drawdown and parameter-sensitivity analytics without changing trading behavior, blocking core result persistence, or requiring a re-run for future tearsheet generation.

</domain>

<decisions>
## Implementation Decisions

### Trade audit log contract
- **D-01:** Phase 7 must produce a full signal audit, not just an executed-trades log.
- **D-02:** The audit log records every bar where the strategy is in `PULLBACK_ARMED` state, whether or not an entry fires.
- **D-03:** Each armed-state audit row must capture:
  - `timestamp`
  - `instrument_id`
  - bar `open`, `high`, `low`, `close`, `volume`
  - `supertrend_direction`
  - `supertrend_value`
  - `vwap_value`
  - `price_vs_vwap`
  - `wavetrend_zscore`
  - `wavetrend_divergence_detected`
  - `delta_value`
  - `delta_threshold`
  - `delta_pass`
  - `volume`
  - `volume_avg`
  - `volume_pass`
  - `absorption_detected`
  - `candle_formation`
  - `optional_confirmation_count`
  - `entry_fired`
  - `entry_rejected_reason` when no entry fires
- **D-04:** Each executed-trade audit row must capture:
  - `entry_timestamp`
  - `exit_timestamp`
  - `entry_price`
  - `exit_price`
  - `direction`
  - `pnl`
  - `pnl_dollars`
  - `exit_reason`
  - `max_favorable_excursion`
  - `max_adverse_excursion`
  - `bars_held`
  - `volatility_cluster_at_entry`
  - `session_at_entry`
- **D-05:** The audit artifact is saved as `analytics/audit_log.csv` alongside every backtest result.
- **D-06:** The audit log is the most important Phase 7 analytics artifact because it explains why trades were taken or rejected.
- **D-07:** Because five-year runs will generate large audit files, implementation must use efficient streaming CSV writing rather than building a huge in-memory dataframe for `pandas.to_csv`.

### Performance breakdown definitions
- **D-08:** Phase 7 must compute performance breakdowns for:
  - session
  - volatility regime
  - month
  - year
  - day of week
  - hour of day (UTC)
- **D-09:** Session buckets are locked as:
  - `rth`: `13:30-20:00 UTC`
  - `asian`: `00:00-07:00 UTC`
  - `london`: `07:00-13:30 UTC`
  - `globex_overnight`: `20:00-24:00 UTC`
- **D-10:** Volatility regime uses the Adaptive SuperTrend volatility cluster at trade entry:
  - `1 = low`
  - `2 = medium`
  - `3 = high`
- **D-11:** Each breakdown category must compute:
  - `trade_count`
  - `win_rate`
  - `total_pnl`
  - `average_pnl_per_trade`
  - `sharpe_ratio`
  - `max_drawdown`
- **D-12:** Each breakdown is saved as its own CSV under `analytics/breakdowns/`.

### Drawdown analysis contract
- **D-13:** Phase 7 must compute and persist drawdown episodes as continuous periods where equity remains below its prior peak.
- **D-14:** Each drawdown episode row must include:
  - `episode_start`
  - `episode_end`
  - `episode_duration_bars`
  - `episode_duration_days`
  - `drawdown_pct`
  - `drawdown_dollars`
  - `recovery_start`
  - `recovery_end`
  - `recovery_duration_bars`
  - `recovery_duration_days`
  - `recovered`
- **D-15:** Phase 7 must also compute and persist the summary drawdown metrics:
  - `max_drawdown_pct`
  - `max_drawdown_dollars`
  - `avg_drawdown_pct`
  - `avg_drawdown_dollars`
  - `max_drawdown_duration_days`
  - `avg_drawdown_duration_days`
  - `max_recovery_duration_days`
  - `avg_recovery_duration_days`
  - `total_drawdown_episodes`
  - `pct_time_in_drawdown`
- **D-16:** Episode detail is saved to `analytics/drawdown_episodes.csv`.
- **D-17:** Underwater equity time series is saved to `analytics/underwater_curve.csv`.
- **D-18:** Summary drawdown metrics are added into the existing `summary.json` rather than split into a separate summary file.

### Parameter sensitivity methodology
- **D-19:** Parameter sensitivity must reuse existing optimization results and must not trigger new backtests.
- **D-20:** For each optimized parameter, completed Optuna trials are grouped into `5` equal-width buckets by parameter value.
- **D-21:** For each parameter, Phase 7 must compute:
  - `correlation_with_objective` using Pearson correlation between parameter value and objective score
  - `sharpe_range_across_buckets` as the range of mean Sharpe across the 5 buckets
- **D-22:** `most_sensitive = true` is assigned to the top `3` parameters ranked by `sharpe_range_across_buckets`.
- **D-23:** The parameter sensitivity artifact is saved as `analytics/parameter_sensitivity.csv` with columns:
  - `parameter_name`
  - `correlation_with_objective`
  - `sharpe_range_across_buckets`
  - `most_sensitive`

### Output structure and lifecycle
- **D-24:** All Phase 7 analytics live under an `analytics/` subdirectory inside the existing timestamped results directory.
- **D-25:** Backtest analytics layout is locked as:
  - `results/backtests/YYYY-MM-DD_HHMMSS/analytics/audit_log.csv`
  - `results/backtests/YYYY-MM-DD_HHMMSS/analytics/drawdown_episodes.csv`
  - `results/backtests/YYYY-MM-DD_HHMMSS/analytics/underwater_curve.csv`
  - `results/backtests/YYYY-MM-DD_HHMMSS/analytics/breakdowns/by_session.csv`
  - `results/backtests/YYYY-MM-DD_HHMMSS/analytics/breakdowns/by_volatility_regime.csv`
  - `results/backtests/YYYY-MM-DD_HHMMSS/analytics/breakdowns/by_month.csv`
  - `results/backtests/YYYY-MM-DD_HHMMSS/analytics/breakdowns/by_year.csv`
  - `results/backtests/YYYY-MM-DD_HHMMSS/analytics/breakdowns/by_day_of_week.csv`
  - `results/backtests/YYYY-MM-DD_HHMMSS/analytics/breakdowns/by_hour.csv`
- **D-26:** Optimization analytics layout is locked as:
  - `results/optimization/YYYY-MM-DD_HHMMSS/analytics/parameter_sensitivity.csv`
  - `results/optimization/YYYY-MM-DD_HHMMSS/analytics/breakdowns/` using the same trade-breakdown structure, built from best-run trades
- **D-27:** Phase 8 tearsheets must be able to consume Phase 7 outputs directly from the filesystem without rerunning the backtest, so Phase 7 artifacts are the canonical source for later reporting.
- **D-28:** Analytics generation runs automatically after every `backtest` and `optimize` run; it is not a separate command.
- **D-29:** Analytics failures must warn and continue. They must never block the main run result from being saved.
- **D-30:** All analytics files must be listed in the run's `manifest.json`.

### the agent's Discretion
- Exact internal module boundaries for audit capture, breakdown aggregation, drawdown analytics, and optimization-sensitivity helpers
- Exact CSV row-model split between signal-audit rows and executed-trade rows, as long as the locked fields are persisted and the resulting artifact remains machine-readable
- Exact warning text when analytics generation fails, as long as failure is explicit and non-blocking

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and scope
- `.planning/PROJECT.md` - v1.1 milestone priorities, native-first rule, and no-strategy-change constraint
- `.planning/REQUIREMENTS.md` - Phase 7 requirements `ANL-01` through `ANL-04`
- `.planning/ROADMAP.md` - Phase 7 goal and success criteria
- `.planning/STATE.md` - current milestone state and carry-forward concerns

### Existing backtest and strategy implementation
- `src/mgc_bt/backtest/strategy.py` - current signal gating, state-machine flow, and entry/exit reason strings that should feed audit explainability
- `src/mgc_bt/backtest/results.py` - current summary, trade-log, and equity-curve derivation that Phase 7 should extend
- `src/mgc_bt/backtest/artifacts.py` - backtest artifact layout, manifest updates, and `latest/` refresh patterns
- `src/mgc_bt/backtest/runner.py` - shared run path that must continue to produce the core backtest result before analytics attach
- `src/mgc_bt/backtest/indicators/vwap.py` - existing session reset semantics relevant to session analytics interpretation

### Existing optimization and research outputs
- `src/mgc_bt/optimization/results.py` - current optimization persistence patterns that Phase 7 should extend for best-run analytics and parameter sensitivity
- `src/mgc_bt/optimization/study.py` - orchestration path for attaching analytics automatically to optimize runs
- `src/mgc_bt/optimization/walk_forward.py` - walk-forward result model and artifacts that Phase 7 should consume rather than recreate
- `src/mgc_bt/optimization/monte_carlo.py` - existing research outputs that Phase 8 will later combine with analytics
- `src/mgc_bt/optimization/stability.py` - existing stability outputs that parameter sensitivity should complement, not duplicate

### Validation and output protection
- `src/mgc_bt/validation/preflight.py` - shared validation patterns and non-blocking warning style
- `tests/test_cli.py` - CLI contracts that Phase 7 extends automatically after runs
- `tests/test_optimization_results.py` - optimization output contract protection
- `tests/test_backtest_results.py` or equivalent result tests if present - existing backtest artifact and summary expectations

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mgc_bt/backtest/strategy.py`: already emits explicit decision and exit reasons (`atr_stop`, hard trend flips, risk rejections) that can seed a richer audit trail instead of inventing new reason vocabularies
- `src/mgc_bt/backtest/results.py`: already knows how to derive trades, equity, and summary metrics; drawdown analytics should build on those canonical result series
- `src/mgc_bt/optimization/results.py`: already writes machine-readable optimization artifacts and manifests, making it the natural place for parameter sensitivity and best-run analytics attachment
- Phase 6 research artifacts (`walk_forward/`, `monte_carlo/`, `stability/`) already exist and should be referenced by later tearsheets rather than recomputed

### Established Patterns
- Timestamped results folders plus `latest/` refresh and `manifest.json` are already standard
- New analytics should be generated automatically as part of run completion, but non-critical post-processing failures must warn and continue
- Typed TOML config and clean module separation remain the project standard
- Native Nautilus infrastructure remains the foundation; custom analytics should sit on top of existing engine outputs rather than reimplement execution logic

### Integration Points
- backtest completion flow in `src/mgc_bt/backtest/artifacts.py` and `src/mgc_bt/backtest/results.py`
- optimize completion flow in `src/mgc_bt/optimization/results.py` and `src/mgc_bt/optimization/export.py`
- strategy state and signal context in `src/mgc_bt/backtest/strategy.py`
- manifest updates for both backtest and optimization outputs

</code_context>

<specifics>
## Specific Ideas

- The audit log should make it possible to answer "why did the strategy not trade here?" without stepping through code.
- Session and volatility-regime analytics should be built from the same canonical trade set used for summary metrics, so totals reconcile cleanly.
- Drawdown analysis should be stored in a filesystem-first way because Phase 8 tearsheets must consume it without rerunning anything.
- Parameter sensitivity should stay honest and interpretable by using completed trial results rather than synthetic local derivatives or extra optimization passes.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 7 scope.

</deferred>

---

*Phase: 07-analytics-and-audit-layer*
*Context gathered: 2026-04-09*
