## Plan 08-03 Summary

- Extended the shared tearsheet with optimization-only sections for ranked results, walk-forward, Monte Carlo, stability, and parameter sensitivity.
- Attached `tearsheet.html` generation to optimization outputs after optional analyses are written.
- Added a walk-forward `best_run/` export so optimization tearsheets can reuse the shared backtest sections consistently.
- Expanded optimization tests for manifest inclusion, optional-section visibility, and non-blocking tearsheet failures.

Verification:

- `uv run pytest tests/test_optimization_results.py tests/test_tearsheet.py tests/test_cli.py -q`
