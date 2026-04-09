# 09-03 Summary

Implemented the dedicated strategy comparison workflow on top of two normal backtest runs.

## What changed

- Added `src/mgc_bt/compare.py` to orchestrate:
  - strategy A run
  - strategy B run
  - lightweight comparison outputs
- Added `compare` CLI command in `src/mgc_bt/cli.py`
- Added `src/mgc_bt/reporting/comparison.py` for a filesystem-first comparison tearsheet
- Reused the shared reporting shell from `src/mgc_bt/reporting/tearsheet.py`
- Added comparison coverage in:
  - `tests/test_compare.py`
  - `tests/test_cli.py`
  - `tests/test_tearsheet.py`

## Verification

- `uv run pytest tests/test_compare.py tests/test_cli.py tests/test_tearsheet.py -q -k "compare or comparison"`
- `uv run python -m mgc_bt compare --strategy-a mgc_production --strategy-b mgc_production --instrument-id MGCJ1.GLBX --start-date 2021-03-09T00:00:00+00:00 --end-date 2021-03-10T23:59:00+00:00`

## Outcome

The platform can now compare two strategies without inventing a second-class execution path: each side gets a standard backtest run folder, and the comparison folder only adds summary, deltas, and an overlay tearsheet.
