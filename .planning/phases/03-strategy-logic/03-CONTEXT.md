# Phase 3: Strategy Logic - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 replaces the temporary Phase 2 harness strategy with the real rule-based MGC futures strategy inside Nautilus `Strategy` lifecycle handlers. This phase owns indicator state, trend qualification, pullback arming, entry confirmation, and ATR-based exit behavior, while preserving the Phase 2 backtest runner contract and event-driven execution model. It does not add Optuna workflow, new data vendors, live trading, or order-book-driven microstructure logic beyond the trades-and-bars approximations explicitly locked for v1.

</domain>

<decisions>
## Implementation Decisions

### Strategy architecture
- **D-01:** Implement the production strategy as a Nautilus `Strategy` subclass and remove the Phase 2 harness from the active backtest path.
- **D-02:** Keep the Phase 2 reusable runner contract intact so `run_backtest(config, params) -> dict` continues to be the programmatic entry point for later optimization.
- **D-03:** Evaluate signals only on completed 1-minute bars, matching the backtest realism locked in Phase 2.
- **D-04:** Maintain an explicit state machine with `FLAT`, `PULLBACK_ARMED`, and `IN_TRADE`.
- **D-05:** The strategy must not emit signals until all indicators are valid, with a minimum warm-up of 200 bars and an `is_ready` gate.

### Indicator implementation approach
- **D-06:** All indicators must be implemented as pure Python rolling-state classes with `update(bar)`-style incremental behavior.
- **D-07:** Do not use vectorized or batch-oriented libraries such as `pandas_ta` for live strategy logic.
- **D-08:** Each indicator class should expose current derived values through properties so the strategy can consume them per bar.
- **D-09:** Each indicator class must have its own synthetic-data unit tests.

### Trend gate
- **D-10:** Adaptive SuperTrend is the primary directional gate.
- **D-11:** VWAP is a secondary directional filter.
- **D-12:** Longs are allowed only when SuperTrend is bullish and price is above VWAP.
- **D-13:** Shorts are allowed only when SuperTrend is bearish and price is below VWAP.
- **D-14:** Trend gating is binary; there is no scoring or weighted blend between SuperTrend and VWAP.

### Adaptive SuperTrend spec
- **D-15:** Maintain a rolling ATR window with configurable length, default 10.
- **D-16:** Run K-Means clustering over ATR history to produce three volatility centroids: high, medium, and low.
- **D-17:** Assign the current ATR to the nearest centroid and use that centroid times the SuperTrend factor for band construction.
- **D-18:** Default SuperTrend factor is 3.0.
- **D-19:** SuperTrend direction should follow the user-provided convention: `1 = bearish`, `-1 = bullish`.
- **D-20:** SuperTrend warm-up is at least ATR length plus training period, with default training period 100 bars.

### VWAP spec
- **D-21:** VWAP is session-based and resets at midnight UTC for the 24/7 Globex workflow.
- **D-22:** VWAP uses typical price `(high + low + close) / 3`.
- **D-23:** Bullish VWAP context means price above VWAP; bearish context means price below VWAP.
- **D-24:** `vwap_reset_hour_utc` remains a tunable parameter even though the default reset is midnight UTC.

### WaveTrend and Z-score spec
- **D-25:** WaveTrend and Z-score are optional confirmation signals, not required core triggers.
- **D-26:** Either WaveTrend divergence or Z-score extreme counts as one valid optional confirmation, interchangeable with absorption or candle confirmation.
- **D-27:** WaveTrend defaults: `n1=10`, `n2=21`, `z-score lookback=20`, `HMA smoothing=12`.
- **D-28:** Default Z-score thresholds are `+2.0` overbought and `-2.0` oversold.
- **D-29:** Divergence detection tracks the last two pivot highs or lows on both price and WaveTrend.
- **D-30:** Bullish divergence means price makes a lower low while WaveTrend makes a higher low; bearish divergence is the inverse.

### Pullback and pivot rules
- **D-31:** Repeated pullback attempts are allowed while the active trend gate remains valid.
- **D-32:** A fresh trend expansion is not required between attempts after a flat exit.
- **D-33:** A minimum pullback depth rule is required before any entry can trigger.
- **D-34:** Swing highs and swing lows use a fractal pivot definition with 2 bars on each side.
- **D-35:** A swing high is confirmed when a bar high is higher than the prior 2 bars and the next 2 bars.
- **D-36:** A swing low is confirmed when a bar low is lower than the prior 2 bars and the next 2 bars.
- **D-37:** `min_pullback_bars` measures elapsed bars since the most recent confirmed swing low for longs and the most recent confirmed swing high for shorts.

### Entry trigger contract
- **D-38:** Core required triggers are: delta imbalance candle in trend direction and above-average volume.
- **D-39:** At least one optional confirmation must also be present.
- **D-40:** Valid optional confirmations are absorption, candle formation, WaveTrend divergence, and WaveTrend Z-score extreme.
- **D-41:** There is no weighting among optional confirmations; any one of them satisfies the optional-confirmation requirement.

### Delta imbalance definition
- **D-42:** For each 1-minute bar, join trades whose timestamps fall within that bar window.
- **D-43:** Use the trade aggressor side from the trades catalog to classify buy-initiated versus sell-initiated volume.
- **D-44:** Delta equals buy volume minus sell volume.
- **D-45:** Store delta in rolling strategy state alongside bar-derived features.
- **D-46:** A delta imbalance candle occurs when absolute delta exceeds a configurable threshold and delta direction matches the bar close direction.
- **D-47:** `delta_imbalance_threshold` is expressed as a fraction of total bar volume.

### Volume and absorption rules
- **D-48:** Average volume uses a simple rolling mean over a configurable lookback, default 20 bars.
- **D-49:** Average range uses a simple rolling mean of `high - low` over a configurable lookback, default 20 bars.
- **D-50:** Absorption is approximated from bars only for v1; MBP/order-book logic is out of scope.
- **D-51:** Bullish or bearish absorption requires volume above average times `absorption_volume_multiplier` and range below average times `absorption_range_multiplier`.
- **D-52:** Bullish absorption additionally requires the close in the upper 40% of the bar range.
- **D-53:** Bearish absorption additionally requires the close in the lower 40% of the bar range.

### Candle confirmation definitions
- **D-54:** All three candle-pattern families count equally as valid candle confirmation.
- **D-55:** Bullish pin bar: lower wick at least 66% of total range, close in the upper 34% of range, and bar makes a new low versus the prior 6 bars.
- **D-56:** Bearish pin bar: upper wick at least 66% of total range, close in the lower 34% of range, and bar makes a new high versus the prior 6 bars.
- **D-57:** Bullish shaved bar: close within the top 5% of the bar range.
- **D-58:** Bearish shaved bar: close within the bottom 5% of the bar range.
- **D-59:** Inside bar requires current high lower than prior bar high and current low higher than prior bar low.
- **D-60:** Inside-bar breakout confirmation is the next bar closing above the inside-bar high for bullish confirmation or below the inside-bar low for bearish confirmation.

### Trade management and exits
- **D-61:** Trade size is fixed at one contract in v1.
- **D-62:** No pyramiding, no scaling in, and no scaling out.
- **D-63:** Only one open position may exist at a time.
- **D-64:** Same-direction re-entry is allowed only after the prior position is flat and a new valid setup forms.
- **D-65:** ATR trailing stop is mandatory and uses configurable period and multiplier, default `14` and `2.0`.
- **D-66:** For longs, stop equals highest close since entry minus ATR times multiplier and may only ratchet upward.
- **D-67:** For shorts, use the symmetric trailing-stop behavior based on lowest close since entry and ATR.
- **D-68:** Exit on ATR trailing stop or hard opposite trend flip, whichever comes first.
- **D-69:** A hard opposite trend flip means both SuperTrend and VWAP flip against the current trade direction on the same completed bar.
- **D-70:** If only one of SuperTrend or VWAP flips, remain in the trade and let the ATR stop manage it.
- **D-71:** If both flip simultaneously, exit at that bar close regardless of trailing-stop location.

### Session handling
- **D-72:** Trade all available Globex data for v1; no explicit session blocking is applied.
- **D-73:** Low-liquidity periods are handled indirectly by the required above-average-volume trigger rather than a separate schedule filter.

### Optimization-facing parameter contract
- **D-74:** These parameter names must match exactly for later Optuna integration: `supertrend_atr_length`, `supertrend_factor`, `supertrend_training_period`, `vwap_reset_hour_utc`, `wavetrend_n1`, `wavetrend_n2`, `wavetrend_ob_level`, `delta_imbalance_threshold`, `absorption_volume_multiplier`, `absorption_range_multiplier`, `volume_lookback`, `atr_trail_length`, `atr_trail_multiplier`, and `min_pullback_bars`.
- **D-75:** Phase 3 should shape strategy config and internal naming around those future optimization parameter names to avoid Phase 4 refactors.

### Testing requirements
- **D-76:** Every indicator class needs a dedicated unit test using synthetic bar data.
- **D-77:** Strategy signal logic needs at least one end-to-end test that feeds a short bar sequence through the full state machine and verifies state transitions.

### Catalog continuity from earlier phases
- **D-78:** Any Phase 3 code touching catalog-backed assumptions must preserve the verified Phase 1 and Phase 2 Databento decode split.
- **D-79:** Definitions were ingested using legacy Cython decoding for Nautilus 1.225.0 catalog compatibility.
- **D-80:** Bars and trades were ingested using `as_legacy_cython=False`.

### the agent's Discretion
- Exact file/module boundaries for indicators versus strategy helpers under `src/mgc_bt/backtest/`
- Whether shared rolling-window utilities are introduced to reduce duplicate indicator bookkeeping
- The precise internal representation of state-machine enums and helper methods, as long as the locked behavior is preserved

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Nautilus strategy lifecycle and backtest integration
- `nt_docs/concepts/strategies.md` - Official strategy lifecycle, handler model, subscriptions, cache access, and order-management patterns
- `nt_docs/concepts/backtesting.md` - Backtest execution model and constraints that Phase 3 strategy logic must continue to respect
- `nt_docs/api_reference/backtest.md` - Current Nautilus 1.225.0 backtest config and node reference used by the existing runner
- `nt_docs/getting_started/backtest_high_level.py` - High-level backtest pattern that Phase 3 continues to plug into

### Nautilus indicator surface
- `nt_docs/api_reference/indicators.md` - Indicator reference context for naming, expectations, and possible interoperability

### Existing project decisions and carry-forward constraints
- `.planning/PROJECT.md` - Project scope, constraints, and rule-based-only requirement
- `.planning/REQUIREMENTS.md` - Phase 3 requirements STRAT-01 through STRAT-05 and testing expectations carried into planning
- `.planning/ROADMAP.md` - Phase 3 goal, scope boundary, and plan breakdown
- `.planning/STATE.md` - Current phase position and carry-forward notes
- `.planning/phases/02-backtest-runner/02-CONTEXT.md` - Locked backtest runner contract that the production strategy must fit into
- `.planning/phases/02-backtest-runner/02-VERIFICATION.md` - Verified next-bar execution behavior and the note that Phase 3 replaces the harness strategy
- `.planning/phases/01-catalog-foundation/01-CONTEXT.md` - Catalog and configuration decisions that still constrain strategy work
- `.planning/phases/01-catalog-foundation/01-VERIFICATION.md` - Verified catalog readiness and structural assumptions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mgc_bt/backtest/runner.py` - Existing reusable backtest entry point that Phase 3 must continue to call without subprocess indirection
- `src/mgc_bt/backtest/configuration.py` - Existing Nautilus `BacktestRunConfig` and venue/fill/latency setup that already satisfies the next-bar execution requirement
- `src/mgc_bt/backtest/results.py` - Existing summary and artifact metric extraction that the production strategy should continue to feed
- `src/mgc_bt/backtest/artifacts.py` - Existing result-bundle persistence contract used by the CLI and later optimization
- `src/mgc_bt/config.py` and `configs/settings.toml` - Existing typed config system ready to absorb strategy parameters

### Established Patterns
- The project already uses a typed TOML config, a reusable Python runner, and CLI wrappers over core functions
- Phase 2 proved that the active backtest path should stay Nautilus-native and event-driven rather than vectorized
- The current strategy implementation in `src/mgc_bt/backtest/strategy_stub.py` is intentionally temporary and should be replaced rather than expanded into the production rule set

### Integration Points
- `src/mgc_bt/backtest/strategy_stub.py` is the current strategy insertion point and likely replacement target
- `src/mgc_bt/backtest/configuration.py` currently imports the harness strategy path and will need to point at the production strategy config/class
- `src/mgc_bt/backtest/contracts.py` and the catalog-backed selection logic already provide the instrument/bar context the production strategy needs
- `tests/` already contains backtest-runner coverage and is ready for indicator and state-machine tests

</code_context>

<specifics>
## Specific Ideas

- The strategy should be built from rolling, per-bar stateful indicator components rather than one large monolithic `on_bar()` method.
- Delta imbalance should use real trade aggressor-side information from the trades catalog, while absorption remains a bars-only approximation in v1.
- The production strategy should feel deterministic and inspectable enough that later Optuna trials can vary parameters without changing architecture.

</specifics>

<deferred>
## Deferred Ideas

- Any MBP-1 or order-book-specific absorption logic is deferred beyond v1; Phase 3 should use the locked bars-only approximation.
- Any session-blocking logic, pyramiding, scaling, or intrabar execution refinements remain out of scope for this phase.

</deferred>

---

*Phase: 03-strategy-logic*
*Context gathered: 2026-04-08*
