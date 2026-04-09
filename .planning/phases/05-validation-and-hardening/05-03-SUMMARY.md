# 05-03 Summary

## What Changed

- Added `manifest.json` output for backtest and optimization result directories.
- Added collision-safe timestamped result-folder creation.
- Added explicit `--force` handling so CLI commands only refresh `latest/` when requested.
- Preserved canonical timestamped output folders even when `latest/` is left untouched.
- Added root [USAGE.md](C:/dev/nautilustrader/USAGE.md) with:
  - exact commands
  - output layout
  - optimization resume guidance
  - rerun guidance
  - common errors and fixes
- Improved CLI help text to explain command intent and `--force` behavior.

## Why It Matters

Repeated local research runs are safer now: artifacts are easier to audit, `latest/` is no longer overwritten implicitly, and a new operator has a concrete runbook.

## Verification

- `uv run pytest tests/test_backtest_artifacts.py tests/test_optimization_results.py tests/test_cli.py -q`
- bounded smoke backtest on `MGCJ1.GLBX` for `2021-03-09T00:00:00+00:00` to `2021-03-09T06:00:00+00:00`
- bounded smoke optimize on short-window config with `--max-trials 1`
