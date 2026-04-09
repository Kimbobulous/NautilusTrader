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

## Cross-Milestone Trends

- No prior milestones archived yet.
