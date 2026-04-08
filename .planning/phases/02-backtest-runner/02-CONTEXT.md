# Phase 2: Backtest Runner - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 delivers a trustworthy Nautilus backtest runner over the catalog built in Phase 1. This phase covers contract selection and rolling behavior, venue and fill-model assumptions, reusable backtest execution APIs, and machine-readable plus human-readable result artifacts. It does not implement the full production strategy logic; Phase 3 owns the actual trend, pullback, trigger, and exit rules.

</domain>

<decisions>
## Implementation Decisions

### Runner mode and contract handling
- **D-01:** Support both single-contract mode and auto-roll mode.
- **D-02:** Auto-roll is the default when no explicit instrument id is provided.
- **D-03:** Single-contract mode must accept an instrument id through the CLI for targeted debugging.
- **D-04:** Auto-roll should prefer open-interest-based rolling when that signal is available.
- **D-05:** If open interest is not available from the catalog-backed workflow, fall back to a calendar roll 5 business days before the contract's last trading day.
- **D-06:** For v1 planning, treat MGC last trading day as the third-to-last business day of the delivery month.

### Execution realism
- **D-07:** Signals are evaluated on completed 1-minute bars only.
- **D-08:** Execution must use bar-close decision, next-bar execution behavior.
- **D-09:** The backtest cost model includes `$0.50` commission per side.
- **D-10:** The backtest cost model includes 1 tick of slippage per fill.
- **D-11:** Commission and slippage must be implemented through Nautilus backtest venue and fill-model configuration, not by patching results after the fact.
- **D-12:** Before implementation, the exact Nautilus 1.225.0 configuration pattern should be verified against `nt_docs/concepts/backtesting.md`.

### Results contract
- **D-13:** Each canonical backtest run writes to `results/backtests/YYYY-MM-DD_HHMMSS/`.
- **D-14:** After each run, `results/backtests/latest/` is refreshed with the same artifacts for convenience.
- **D-15:** Each run folder must contain `summary.json`, `trades.csv`, `equity_curve.png`, and `run_config.toml`.
- **D-16:** `summary.json` must be machine-readable and usable by Phase 4 without parsing console text.
- **D-17:** `summary.json` must include at minimum `total_pnl`, `sharpe_ratio`, `win_rate`, `max_drawdown`, `total_trades`, `start_date`, `end_date`, `instrument_id`, and all strategy parameters used.

### API and architecture
- **D-18:** The core runner must be a reusable Python function with the shape `run_backtest(config, params) -> dict`.
- **D-19:** The CLI `backtest` command is a wrapper over that reusable function rather than a separate execution path.
- **D-20:** Phase 2 should prefer Nautilus configuration objects and catalog-backed backtesting patterns over manual vectorized simulation.
- **D-21:** The runner design must leave Phase 4 able to call the backtest programmatically in-process without subprocess overhead.

### Catalog continuity from Phase 1
- **D-22:** Any Phase 2 code that reads or reasons about the catalog must preserve the established Databento decoding split from Phase 1.
- **D-23:** Databento definitions are legacy Cython decoded for catalog compatibility on Nautilus 1.225.0.
- **D-24:** Databento bars and trades use `as_legacy_cython=False`.

### the agent's Discretion
- Exact module boundaries under `src/mgc_bt/backtest/`
- Whether Phase 2 uses a minimal smoke-test strategy or strategy adapter placeholder to validate the runner before full Phase 3 logic exists
- The specific output schema details beyond the required summary keys
- The exact plotting library used for the equity-curve PNG

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Nautilus backtesting
- `nt_docs/concepts/backtesting.md` - Primary reference for `BacktestNode`, `BacktestEngine`, venue configuration, sequencing, and fill-model behavior
- `nt_docs/getting_started/backtest_high_level.py` - Recommended high-level catalog-backed backtest pattern
- `nt_docs/getting_started/backtest_low_level.py` - Low-level comparison reference when deciding what should remain reusable in Python
- `nt_docs/api_reference/backtest.md` - Backtest configuration and result API surface
- `nt_docs/concepts/strategies.md` - Strategy lifecycle boundaries for what Phase 2 can scaffold versus what Phase 3 must implement

### Catalog continuity
- `.planning/phases/01-catalog-foundation/01-VERIFICATION.md` - Verified Phase 1 ingest outcomes and catalog readiness
- `.planning/phases/01-catalog-foundation/01-02-SUMMARY.md` - Records the critical Databento decoding split required for catalog compatibility
- `nt_docs/api_reference/persistence.md` - Catalog query and persistence details used by the backtest runner

### Project planning context
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mgc_bt/config.py` already provides typed TOML-backed settings and Windows-safe path resolution.
- `src/mgc_bt/cli.py` already exposes the `backtest` command surface, though it is still a stub.
- `catalog/` contains validated MGC instruments, bars, and trades from the real local Databento data.

### Established Patterns
- The project already uses a `src/` layout, typed config dataclasses, and a CLI wrapper approach.
- Phase 1 proved the local Databento and Nautilus integration with real data, so Phase 2 should reuse the catalog rather than touch raw DBN files directly.
- Planning and verification should stay sequential: runner setup first, results extraction second, artifact generation third.

### Integration Points
- Config file: `configs/settings.toml`
- Package root: `src/mgc_bt/`
- Catalog root defaults to `catalog/`
- Results root defaults to `results/`

</code_context>

<specifics>
## Specific Ideas

- The backtest runner should feel like a clean research primitive: callable from Python for optimization and callable from the CLI for normal use.
- Auto-roll behavior should be explicit and reproducible rather than hidden inside ad hoc contract selection logic.
- Phase 2 should establish a stable results bundle contract so Phase 4 reads `summary.json` instead of scraping console output.

</specifics>

<deferred>
## Deferred Ideas

- Full Adaptive SuperTrend, VWAP, WaveTrend, trigger, and ATR stop logic remain in Phase 3.
- Any richer intrabar or trade-aware execution modeling remains out of scope for v1.

</deferred>

---

*Phase: 02-backtest-runner*
*Context gathered: 2026-04-08*
