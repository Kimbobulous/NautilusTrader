---
phase: 01-catalog-foundation
plan: 01
subsystem: infra
tags: [python, uv, argparse, toml, config]
requires: []
provides:
  - src-layout Python package for `mgc_bt`
  - TOML-backed settings loader with Windows-safe path resolution
  - CLI entrypoint with `ingest`, `backtest`, and `optimize` commands
affects: [catalog-ingestion, validation, phase-2-backtest]
tech-stack:
  added: [setuptools, pytest]
  patterns: [src-layout package, config-first CLI]
key-files:
  created: [pyproject.toml, configs/settings.toml, src/mgc_bt/cli.py, src/mgc_bt/config.py]
  modified: []
key-decisions:
  - "Used a src-layout package and editable install flow so `python -m mgc_bt` works cleanly from the local venv."
  - "Normalized configured paths through `pathlib.Path` at load time to avoid Windows backslash drift."
patterns-established:
  - "CLI commands load shared settings before dispatching work."
  - "Config sections for future phases exist from day one rather than being introduced ad hoc."
requirements-completed: [CLI-01, CLI-02, CLI-03]
duration: 35min
completed: 2026-04-08
---

# Phase 1: Catalog Foundation Summary

**src-layout Python package with TOML config loading and a reusable `mgc_bt` command surface**

## Performance

- **Duration:** 35 min
- **Started:** 2026-04-08T07:20:00-05:00
- **Completed:** 2026-04-08T07:55:00-05:00
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Added `pyproject.toml` and editable-install support for a real Python package.
- Created `configs/settings.toml` with the locked `paths`, `ingestion`, `backtest`, and `optimization` sections.
- Implemented the initial CLI plus tests that lock parser and config behavior.

## Task Commits

Implementation landed in aggregate phase commits for this local execution run:

1. **Task 1-3: Scaffold package, config, and CLI** - `012ea0f` (feat)
2. **Cleanup: ignore editable install metadata** - `7ce95f6` (chore)

**Plan metadata:** Covered by the phase planning docs already committed before execution.

## Files Created/Modified
- `pyproject.toml` - Project metadata, package discovery, and pytest configuration.
- `configs/settings.toml` - Shared project settings for paths and future workflow sections.
- `src/mgc_bt/__main__.py` - `python -m mgc_bt` entrypoint.
- `src/mgc_bt/cli.py` - Command parser and command dispatch.
- `src/mgc_bt/config.py` - Typed TOML settings loader.
- `tests/test_cli.py` - CLI and config regression coverage.

## Decisions Made
- Kept the CLI on `argparse` to minimize dependencies and keep PowerShell behavior predictable.
- Used editable installation in the local venv so the `src` layout stays clean without adding a root package shim.

## Deviations from Plan

None - plan executed as intended.

## Issues Encountered

- `argparse` only accepted `--config` before the subcommand at first. The CLI now normalizes global options so both `mgc_bt --config ... ingest` and `mgc_bt ingest --config ...` work.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The ingest plan now has a stable package, config, and CLI surface to plug into.
- Future `backtest` and `optimize` commands can extend the existing parser without changing the command contract.

---
*Phase: 01-catalog-foundation*
*Completed: 2026-04-08*
