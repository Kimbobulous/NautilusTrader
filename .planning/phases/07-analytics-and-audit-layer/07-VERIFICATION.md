## Phase 7 Verification

Phase 7 completed all four planned execution tracks:

1. `07-01` audit capture and streamed `audit_log.csv`
2. `07-02` backtest breakdown and drawdown analytics
3. `07-03` optimization parameter sensitivity and best-run analytics
4. `07-04` additive manifest and non-blocking analytics hardening

Verified outcomes:

- Backtests now write `analytics/audit_log.csv`, breakdown CSVs, `drawdown_episodes.csv`, and `underwater_curve.csv`.
- Optimization runs now write `analytics/parameter_sensitivity.csv` plus best-run breakdown analytics alongside the existing Phase 6 outputs.
- Analytics remain additive: core bundles persist first, and analytics failures warn instead of blocking the run.
- The Phase 7 analytics bundle is filesystem-first and ready for Phase 8 tearsheet generation.

Verification commands:

- `uv run pytest -q`
- `uv run python -m mgc_bt backtest --instrument-id MGCJ1.GLBX --start-date 2021-03-09T00:00:00+00:00 --end-date 2021-03-09T06:00:00+00:00`
- temporary narrow-window optimize smoke derived from `configs/settings.toml` with `--study-name phase7-smoke-2 --max-trials 1`

Result:

- `67 passed`
- bounded real backtest smoke passed on `MGCJ1.GLBX`
- bounded optimization smoke passed on a temporary narrow-window config derived from `configs/settings.toml`
