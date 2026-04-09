# Retrospective

## Milestone: v1.0 - MGC Research Workflow

**Shipped:** 2026-04-09
**Phases:** 5 | **Plans:** 17

### What Was Built

- Databento ingestion into a Nautilus Parquet catalog for MGC definitions, bars, and trades
- Reusable Nautilus backtest runner and persisted backtest artifact bundle
- Production rule-based MGC strategy with custom risk controls
- Optuna optimization workflow with holdout evaluation
- Shared preflight validation, `health`, safer results handling, and usage documentation

### What Worked

- Sequential phase execution fit the dependency chain well and reduced rework.
- Locking design decisions early through context/planning kept later implementation focused.
- Building on Nautilus native infrastructure prevented a lot of unnecessary custom-engine complexity.

### What Was Inefficient

- A few Phase 5 hardening issues only surfaced during real local smoke runs, especially around repeated in-process backtest execution.
- Some planning-state metrics in `STATE.md` were clearly generic placeholders and not especially informative for actual elapsed effort.

### Patterns Established

- Shared reusable Python entry points under the CLI are the right shape for future expansion.
- Catalog-backed workflows need explicit preservation of the definitions-vs-bars/trades decode split.
- Local operator hardening is most effective when it reuses the real command code paths rather than adding parallel setup tools.

### Key Lessons

- Treat Nautilus logging as process-level state when repeatedly running backtests in one process.
- Preflight validation should land before more UX polish; it prevents the most expensive failures.
- Small smoke runs on real local data are still necessary even when the test suite is green.

### Cost Observations

- Model mix: not tracked in-code
- Sessions: one milestone cycle across 2026-04-08 to 2026-04-09
- Notable: keeping planning, implementation, verification, and git discipline tightly coupled made the workflow predictable

## Milestone: v1.1 - Quant Research Infrastructure

**Shipped:** 2026-04-09
**Phases:** 4 | **Plans:** 16

### What Was Built

- Walk-forward optimization with rolling in-sample/OOS windows and time-weighted aggregate OOS metrics
- Monte Carlo permutation and bootstrap analysis with deterministic seeding
- Optuna fANOVA parameter stability with 5×5 heatmap and neighborhood robustness reruns (`scikit-learn` added to venv)
- Streaming trade audit capture with full `PULLBACK_ARMED` bar records and executed-trade enrichment fields
- Multi-dimension performance breakdowns: session, volatility regime, month, year, day of week, hour
- Drawdown episode and underwater-equity exports with additive drawdown metrics in `summary.json`
- Automatic self-contained Plotly HTML tearsheets after every `backtest` and `optimize` run
- Thin reusable strategy base class (`BaseResearchStrategy`), standalone indicator primitives, config-driven strategy registry, and a dedicated `compare` CLI command with overlay tearsheet

### What Worked

- Additive extension discipline: every phase added new artifacts or paths without touching default behavior, keeping regressions minimal.
- Filesystem-first reporting (Phase 8 reads Phase 7 artifacts instead of re-running) proved to be a clean contract boundary.
- Locking the MGC golden fixture before refactoring gave immediate confidence that signal behavior was preserved across Phase 9 changes.
- Keeping walk-forward, Monte Carlo, and stability as opt-in flags preserved the default optimize path exactly.

### What Was Inefficient

- Accomplishments in SUMMARY.md used free-form structure instead of a machine-parseable `one_liner` field, so `gsd-tools milestone complete` extracted zero accomplishments automatically.
- STATE.md used a non-standard field name that caused a CLI warning on `milestone complete`; the tool couldn't find "Last Activity Description".

### Patterns Established

- Additive artifact bundles (`walk_forward/`, `monte_carlo/`, `stability/`, `analytics/`) coexist cleanly when each has a dedicated subdirectory.
- Best-effort generation (tearsheets, analytics) with warning-only failure handling is the right default for reporting layers.
- Golden fixture regression test locked before refactor = safest refactor workflow.
- Strategy registry with named keys + optional import-path override is the right extensibility pattern for adding future strategies.

### Key Lessons

- Plan SUMMARY.md format with machine-parseable fields (`one_liner:`) so GSD tools can extract accomplishments automatically.
- Keep STATE.md field names in sync with what `gsd-tools` expects; free-form edits drift from the CLI's parsing.
- Streaming CSV writers (`csv.writer` row-by-row) are the right memory discipline for audit logs that may span many bars.

### Cost Observations

- Sessions: one milestone cycle on 2026-04-09
- Notable: 163 files changed across 4 phases with 89 tests passing — high change density with zero regressions

## Cross-Milestone Trends

| Metric | v1.0 | v1.1 |
|--------|------|------|
| Phases | 5 | 4 |
| Plans | 17 | 16 |
| Test count at close | ~47 | 89 |
| Files changed | ~80 | 163 |
| Primary theme | Foundation + correctness | Trust + reusability |

- Both milestones followed additive extension discipline — no regressions.
- Research integrity (v1.1) required more test infrastructure than runtime infrastructure.
- Planning doc drift (STATE.md fields, SUMMARY.md format) is a recurring friction point worth standardizing.
