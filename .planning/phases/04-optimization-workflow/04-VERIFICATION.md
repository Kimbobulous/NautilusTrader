---
status: passed
phase: 04-optimization-workflow
verified: 2026-04-09
---

# Phase 4 Verification

## Goal Check

Phase 4 goal was to deliver a repeatable Optuna workflow that tests parameter combinations, ranks results, and saves best-run artifacts.

Verdict: passed.

## Must-Haves

- [x] User can run `optimize` against the catalog-backed backtest workflow
- [x] Each trial records objective score plus raw backtest metrics including Sharpe, PnL, win rate, max drawdown, and trade count
- [x] Optimization outputs include a ranked parameter table saved to the results directory
- [x] The best parameter set produces a saved equity curve PNG and reproducible artifact bundle
- [x] The search space includes strategy parameters plus the approved custom risk parameters without optimizing native `RiskEngineConfig` guardrails
- [x] SQLite-backed study resume is supported through `--resume`
- [x] Holdout evaluation is exported separately and clearly labeled
- [x] The catalog continuity note is preserved where catalog-backed assumptions still matter:
  - definitions were ingested with legacy Cython decoding
  - bars/trades were ingested with `as_legacy_cython=False`

## Automated Checks

- `uv run pytest tests/test_config.py tests/test_optimize_objective.py tests/test_optimization_results.py tests/test_cli.py -q`
- `uv run pytest -q`

All passed.

## Manual Checks

- Bounded real optimization smoke run passed on a temporary short-window config derived from `configs/settings.toml` using:
  - `uv run python -m mgc_bt ... optimize --study-name phase4-smoke --max-trials 2`
- The smoke run produced:
  - `ranked_results.csv`
  - `optimization_summary.json`
  - `failed_trials.json`
  - `best_run/`
  - `top_10/`
  - `best_run/holdout_results.json`
  - `best_run/holdout_equity_curve.png`
  - refreshed `latest/`

## Notes

- The shared runner still uses the high-level `BacktestNode` path and therefore creates fresh engines per call. This was reviewed explicitly for Phase 4.
- I verified that `BacktestEngine.reset()` exists and is recommended by Nautilus for parameter optimization when the dataset can persist in memory.
- I intentionally retained the catalog-backed `BacktestNode` runner for this project because the full bars-plus-trades optimization dataset is large enough that the high-level catalog path remains the safer fit than a low-level in-memory reset-based refactor.
