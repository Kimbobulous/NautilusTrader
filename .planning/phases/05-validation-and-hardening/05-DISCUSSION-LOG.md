# Phase 5 Discussion Log

**Date:** 2026-04-09
**Phase:** 05 - Validation and Hardening

## Decisions Captured

- Validation depth is strong preflight checking before `ingest`, `backtest`, and `optimize`.
- Regression coverage should focus on config validation, result integrity, optimization persistence and resume, and common user mistakes.
- Operator safeguards use a mixed model: fail on integrity issues, warn on convenience issues.
- Results hardening should add overwrite protection and `manifest.json`, but no cleanup automation yet.
- Add `--force` to `backtest` and `optimize` to explicitly allow overwriting `latest/`.
- Add a concise root `USAGE.md` plus clearer CLI help text.
- Phase 5 must not add new strategy logic, indicators, or optimization features.
- Add a unified `python -m mgc_bt health` command that runs all command preflight checks and summarizes readiness.

## Key Examples Locked By User

- `ingest` preflight checks:
  - source data directories exist
  - at least one relevant DBN file exists
  - catalog path is writable
  - overlapping existing catalog data warns
- `backtest` preflight checks:
  - catalog exists
  - definitions, bars, and trades are present
  - requested date range has data
  - explicit instrument ID exists if supplied
  - required backtest settings are present
- `optimize` preflight checks:
  - all `backtest` checks
  - in-sample and holdout windows do not overlap
  - holdout end is not in the future
  - storage path is writable
  - `--resume` requires an existing study

## Boundary Reminder

If implementation identifies something that looks like a feature addition instead of hardening, it should be deferred or sent to backlog instead of being pulled into Phase 5.
