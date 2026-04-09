## Plan 08-02 Summary

- Extended the shared tearsheet renderer with the backtest report flow: header, executive summary, equity, drawdown, trade analysis, breakdowns, audit diagnostics, and footer.
- Wired automatic backtest `tearsheet.html` generation into `src/mgc_bt/backtest/artifacts.py`.
- Kept tearsheet generation best-effort so backtest core artifacts still persist if reporting fails.
- Updated manifests and backtest contract tests to include `tearsheet.html` and `latest/` coverage.

Verification:

- `uv run pytest tests/test_backtest_artifacts.py tests/test_tearsheet.py tests/test_cli.py -q`
