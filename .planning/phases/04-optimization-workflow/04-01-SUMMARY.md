# Plan 04-01 Summary

## Outcome

Completed the Optuna orchestration foundation for Phase 4:

- Expanded `[optimization]` in `configs/settings.toml`
- Added typed optimization settings and validation in `src/mgc_bt/config.py`
- Added Optuna dependency to `pyproject.toml`
- Implemented search-space sampling in `src/mgc_bt/optimization/search_space.py`
- Implemented objective scoring and trial execution in `src/mgc_bt/optimization/objective.py`
- Implemented study bootstrap, progress reporting, and early stopping in `src/mgc_bt/optimization/study.py`
- Wired the CLI `optimize` command in `src/mgc_bt/cli.py`
- Added focused coverage in `tests/test_config.py`, `tests/test_optimize_objective.py`, and `tests/test_cli.py`

## Engine Reuse Decision

- The shared backtest runner currently creates a fresh `BacktestNode` per segment per call in `src/mgc_bt/backtest/runner.py`.
- I verified the installed `nautilus_trader 1.225.0` low-level API does support `BacktestEngine.reset()` and the local docs explicitly recommend it for parameter optimization when the same dataset can persist in memory.
- I did **not** refactor the project to a low-level `BacktestEngine.reset()` path for Phase 4 because this project's full optimization dataset is catalog-backed and includes large multi-year trade data. Nautilus' own docs recommend the high-level `BacktestNode` path when the data stream exceeds available memory and benefits from catalog-backed loading.
- In other words: `reset()` is real, but it is the wrong default tradeoff here unless we are willing to preload and retain the optimization dataset in memory or redesign the execution path around low-level manual chunking.
- The Phase 4 implementation therefore keeps the verified catalog-backed runner path and documents this as an intentional scalability and correctness decision, not an oversight.

## Verification

Automated:

- `uv run pytest tests/test_config.py tests/test_optimize_objective.py tests/test_optimization_results.py tests/test_cli.py -q`

The optimization entrypoint is now in place, runner reuse remains in-process and shared, and the engine-reuse decision is documented for future revisiting.
