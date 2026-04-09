# Plan 04-03 Summary

## Outcome

Completed the best-run and holdout export layer for Phase 4:

- Added best-run and holdout rerun helpers in `src/mgc_bt/optimization/export.py`
- Exported the full best-run bundle under `best_run/`
- Exported light top-ranked bundles under `top_10/`
- Added clearly labeled holdout outputs:
  - `holdout_results.json`
  - `holdout_equity_curve.png`
- Added CLI overfitting warning when holdout Sharpe underperforms in-sample Sharpe by more than `0.3`
- Reused the shared runner for both best-run and holdout reruns rather than inventing a second export path

## Key Notes

- Holdout execution is now visibly separate from in-sample optimization results.
- The root optimization run folder includes its own `run_config.toml` for study-level reproducibility, while `best_run/run_config.toml` preserves the exact rerun settings used for the best parameter set.
- The bounded real CLI smoke run on a short temporary window completed successfully and produced:
  - ranked results
  - best-run bundle
  - holdout artifacts
  - refreshed `latest/`

## Verification

Automated:

- `uv run pytest tests/test_optimization_results.py tests/test_cli.py -q`

Manual:

- Ran a bounded real CLI smoke optimization using a temporary short-window config derived from `configs/settings.toml` with:
  - `--study-name phase4-smoke`
  - `--max-trials 2`

Phase 4 now finishes with an honest in-sample plus holdout evaluation story instead of only a leaderboard of trial scores.
