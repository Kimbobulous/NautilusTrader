## Plan 08-01 Summary

- Added a new shared reporting package under `src/mgc_bt/reporting/`.
- Implemented filesystem-first run-folder loaders for backtest and optimization results.
- Built a self-contained Plotly HTML shell with one-time Plotly bundle embedding and explicit missing-section notices.
- Added foundation coverage in `tests/test_tearsheet.py` for loader discovery, self-contained HTML, and unavailable-section behavior.

Verification:

- `uv run pytest tests/test_tearsheet.py -q`
