# Phase 9: Reusable Strategy Platform - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Refactor the current single-strategy platform into a reusable strategy framework without changing validated MGC behavior. This phase covers a thin generic strategy base, broader reusable indicator and signal-primitive extraction, config-driven strategy switching, and a dedicated side-by-side strategy comparison workflow. It does not add new trading logic, alter existing thresholds, or replace the current backtest/optimization foundations.

</domain>

<decisions>
## Implementation Decisions

### Generic Strategy Base
- **D-01:** Use a thin event-driven base class, not a heavy strategy framework. The base should provide shared lifecycle hooks, audit hook integration, trade metadata enrichment, risk-manager wiring, and artifact plumbing only.
- **D-02:** Each concrete strategy owns its own signal engine completely. The base class must not dictate indicator choice, state-machine shape, or entry/exit composition rules.
- **D-03:** The base class should automatically manage audit-log file handle lifecycle and expose common hooks that future strategies can opt into without rewriting operational plumbing.

### Indicator and Primitive Extraction
- **D-04:** Extract both pure indicators and reusable signal primitives.
- **D-05:** Pure reusable indicators include ATR, Adaptive SuperTrend, VWAP, WaveTrend, rolling stats, and fractal pivots.
- **D-06:** Reusable signal primitives include candle pattern detectors, delta accumulator, absorption detector, and volume average.
- **D-07:** Do not extract MGC-specific signal-combination logic. The rule that combines SuperTrend, VWAP, WaveTrend, delta, absorption, and candle confirmations remains in the MGC strategy implementation.

### Strategy Switching
- **D-08:** Use a hybrid switching model: named registry by default, optional explicit import-path override for advanced users.
- **D-09:** `mgc_production` remains the default named strategy.
- **D-10:** Adding a new strategy should require defining the class and registering it, not editing runner or CLI logic.

### Strategy Comparison
- **D-11:** Add a dedicated `compare` CLI command rather than overloading `backtest`.
- **D-12:** CLI shape should support side-by-side strategy execution on the same data window, e.g. `python -m mgc_bt compare --strategy-a ... --strategy-b ...`.
- **D-13:** Comparison output uses two normal run folders plus a lightweight comparison folder. Each strategy keeps its full normal artifact bundle and tearsheet, while the comparison folder stores `comparison_summary.json`, `metrics_delta.csv`, and `comparison_tearsheet.html`.
- **D-14:** The comparison reporting layer should reuse the existing tearsheet infrastructure rather than introducing a parallel reporting engine.

### Behavior Preservation and Validation
- **D-15:** Phase 9 is refactor-only. No existing MGC strategy logic, thresholds, or signal conditions may change.
- **D-16:** The MGC production strategy must produce identical backtest results before and after the refactor.
- **D-17:** Add a permanent golden fixture regression test using a bounded deterministic MGC backtest window. Exact trade count, exact PnL, and exact Sharpe must match pre-refactor outputs.
- **D-18:** The full existing suite must continue passing alongside the new golden fixture.
- **D-19:** New base-class infrastructure must have its own independent tests instead of relying only on MGC strategy coverage.

### Documentation and Extensibility
- **D-20:** Phase 9 should end with a clear documented pattern in `USAGE.md` showing exactly how to add a new strategy to the platform.

### the agent's Discretion
- Exact registry implementation details, as long as the default named-path flow stays simple and the import override remains available.
- Exact base-class method names and hook names, as long as the base remains thin and event-driven.
- Exact structure of the comparison tearsheet, as long as it reuses the current reporting system and the required artifacts are present.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and Phase Scope
- `.planning/PROJECT.md` - project principles, native-Nautilus-first rule, and v1.1 milestone constraints
- `.planning/REQUIREMENTS.md` - `PLT-01` through `PLT-04` acceptance targets for Phase 9
- `.planning/ROADMAP.md` - Phase 9 goal, dependency on Phase 8, and milestone success criteria
- `.planning/STATE.md` - current milestone position and carry-forward constraints from Phases 6-8

### Prior Phase Decisions
- `.planning/phases/06-research-integrity-framework/06-CONTEXT.md` - optimization workflow and holdout/walk-forward decisions that Phase 9 must preserve
- `.planning/phases/07-analytics-and-audit-layer/07-CONTEXT.md` - analytics, audit-log, and artifact contracts that every future strategy should inherit
- `.planning/phases/08-interactive-tearsheet-reporting/08-CONTEXT.md` - shared reporting and tearsheet constraints that comparison output should reuse

### Nautilus Foundation
- `nt_docs/concepts/strategies.md` - Nautilus event-driven strategy model to preserve in the reusable base
- `nt_docs/concepts/backtesting.md` - backtest integration model that Phase 9 must extend rather than replace
- `nt_docs/api_reference/backtest.md` - current installed backtest config surface and high-level runner assumptions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mgc_bt/backtest/indicators/__init__.py` - current reusable indicator exports already provide a starting library boundary
- `src/mgc_bt/backtest/risk.py` - standalone custom risk manager that should remain strategy-agnostic and reusable
- `src/mgc_bt/backtest/analytics.py` - shared audit and trade-metadata infrastructure that the thin base class should wire automatically
- `src/mgc_bt/reporting/` - shared filesystem-first tearsheet infrastructure ready to support comparison output

### Established Patterns
- `src/mgc_bt/backtest/strategy.py` - current strategy splits a Nautilus `Strategy` wrapper from an internal signal engine, which is the main reusable architectural pattern to preserve
- `src/mgc_bt/config.py` - typed TOML config pattern should remain the mechanism for strategy selection and comparison settings
- `src/mgc_bt/backtest/runner.py` - shared `run_backtest(settings, params) -> dict` contract is the core execution path and should not be replaced
- `src/mgc_bt/backtest/configuration.py` - current hardcoded `ImportableStrategyConfig` path is the main integration seam for introducing registry-based strategy resolution

### Integration Points
- Strategy registry and import override resolution will need to connect through `src/mgc_bt/backtest/configuration.py`
- Comparison workflow should live alongside the existing CLI surface in `src/mgc_bt/cli.py` and the existing result/reporting directories
- Golden-fixture validation should extend the existing backtest/strategy test suite instead of inventing a separate verification path

</code_context>

<specifics>
## Specific Ideas

- The common case should stay simple: `strategy = "mgc_production"` in TOML should just work.
- Power users should still be able to point at a fully qualified strategy class without patching runner code.
- Comparison output should feel like a lightweight orchestration layer over two normal runs, not a second-class special backtest mode.
- Strategy reuse matters, but preserving validated MGC behavior matters more than aggressive abstraction.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 09-reusable-strategy-platform*
*Context gathered: 2026-04-09*
