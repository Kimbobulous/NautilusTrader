---
phase: 10-full-5-year-optimization-run
plan: 01
subsystem: research
tags: [toml, config, optimize, walk-forward, monte-carlo, smoke-run]
requires:
  - phase: 10-full-5-year-optimization-run
    provides: "Locked Phase 10 run contract and smoke/full operator policy"
provides:
  - "Production optimization windows aligned to the locked 2021-03-09 to 2025-12-31 research dataset"
  - "Reusable configs/smoke_optimization.toml for end-to-end smoke validation"
  - "Regression tests covering both production and smoke optimization config contracts"
affects: [phase-10-findings, smoke-run, full-run, operator-commands]
tech-stack:
  added: []
  patterns: ["Typed TOML smoke config alongside production settings", "Operator commands validated against live CLI parser"]
key-files:
  created: [configs/smoke_optimization.toml]
  modified: [configs/settings.toml, tests/test_config.py]
key-decisions:
  - "Locked production optimization dates to the Phase 10 research contract before any human-run optimization begins."
  - "Gave the smoke run its own study name and SQLite storage file to avoid colliding with the full research run."
  - "Kept the protected final test hidden by preserving final_test_months=6 and omitting --final-test from the command contract."
patterns-established:
  - "Research execution phases can use standalone smoke config files through the global --config flag."
  - "Long-running human-operated runs should be validated with fast config and health checks first."
requirements-completed: [RES-01]
duration: 20min
completed: 2026-04-09
one_liner: "Phase 10 prep now uses locked 2021-2025 optimization windows plus a reusable smoke config for walk-forward research validation"
---

# Phase 10: Full 5-Year Optimization Run Summary

**Phase 10 prep now uses locked 2021-2025 optimization windows plus a reusable smoke config for walk-forward research validation**

## Performance

- **Duration:** 20 min
- **Started:** 2026-04-10T00:40:00Z
- **Completed:** 2026-04-10T00:55:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Updated [settings.toml](C:/dev/nautilustrader/configs/settings.toml) to the locked Phase 10 in-sample and holdout windows.
- Added [smoke_optimization.toml](C:/dev/nautilustrader/configs/smoke_optimization.toml) as a reusable smoke-run config with `6/1/1/1` walk-forward windows and `20` max trials.
- Extended [test_config.py](C:/dev/nautilustrader/tests/test_config.py) to lock both the production and smoke research config contracts.
- Verified both `uv run python -m mgc_bt health` and `uv run python -m mgc_bt --config configs/smoke_optimization.toml health` report `backtest: READY` and `optimize: READY`.

## Task Commits

1. **Task 1-3: Phase 10 run prep, smoke config, and command-contract validation** - pending plan commit in current execution checkpoint

## Files Created/Modified

- [settings.toml](C:/dev/nautilustrader/configs/settings.toml) - locked Phase 10 production optimization windows
- [smoke_optimization.toml](C:/dev/nautilustrader/configs/smoke_optimization.toml) - standalone reusable smoke optimization config
- [test_config.py](C:/dev/nautilustrader/tests/test_config.py) - regression coverage for production and smoke config values

## Decisions Made

- Used a separate smoke study/storage pair (`mgc-optuna-smoke`, `optuna_storage_smoke.db`) so the smoke run cannot contaminate the full-run study state.
- Kept the smoke config on the same dataset coverage as production so the smoke run validates the real Phase 10 pipeline, not a toy date range.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `health` reports `ingest: ATTENTION` because the source folders contain degraded Databento days and the catalog already exists, but both production and smoke configs are `backtest: READY` and `optimize: READY`, so these are warnings rather than blockers for Phase 10 research execution.

## User Setup Required

Run the smoke commands next:

- `uv run python -m mgc_bt --config configs/smoke_optimization.toml health`
- `uv run python -m mgc_bt --config configs/smoke_optimization.toml optimize --walk-forward`

Then paste the smoke terminal summary and the run directory so Plan 10-02 can validate artifacts before the full run starts.

## Next Phase Readiness

- Phase 10 Wave 1 is complete.
- The phase is now waiting on the human-run smoke optimization boundary defined in Plan 10-02.
- Full-run commands should not start until the smoke artifact bundle is reviewed.

---
*Phase: 10-full-5-year-optimization-run*
*Completed: 2026-04-09*
