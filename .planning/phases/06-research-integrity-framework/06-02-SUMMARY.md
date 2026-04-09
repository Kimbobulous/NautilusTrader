## 06-02 Summary

- Added a real walk-forward coordinator in `src/mgc_bt/optimization/walk_forward.py` with rolling train/validation/test windows, training-bar skips, validation reranking, inconclusive test handling, and time-weighted aggregate OOS math.
- Extended the optimization objective layer so train, validation, test, and final-test evaluations all flow through the shared `run_backtest(settings, params)` contract.
- Branched `run_optimization(...)` so `--walk-forward` now writes a dedicated `walk_forward/` artifact bundle while the legacy no-flag optimize path remains untouched.
- Added regression coverage for walk-forward summary rendering, shared-runner evaluation, and exact walk-forward artifact filenames.

Verification:

- `uv run pytest tests/test_cli.py tests/test_optimize_objective.py tests/test_optimization_results.py -q`
