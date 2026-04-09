## 06-01 Summary

- Added typed Phase 6 settings via `[walk_forward]` and `[monte_carlo]` in `configs/settings.toml` and loaded them through `WalkForwardConfig` and `MonteCarloConfig`.
- Extended `mgc_bt optimize` with the new Phase 6 flags while preserving the existing no-flag behavior and gating `--final-test` behind `--walk-forward`.
- Added additive Phase 6 metadata support to optimization summaries and run configs without changing the existing default artifact contract.
- Extended regression coverage to prove the new settings validate, the new flags parse correctly, and a default optimize run still does not create `walk_forward/`, `monte_carlo/`, or `stability/` artifact directories.

Verification:

- `uv run pytest tests/test_config.py tests/test_cli.py tests/test_optimization_results.py -q`
- `uv run python -m mgc_bt --config configs/settings.toml optimize --help`
