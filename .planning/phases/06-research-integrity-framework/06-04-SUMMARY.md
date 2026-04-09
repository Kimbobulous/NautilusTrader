## 06-04 Summary

- Added stability analysis in `src/mgc_bt/optimization/stability.py` using Optuna’s `FanovaImportanceEvaluator`, a 5x5 top-pair heatmap, and neighborhood robustness reruns around the best parameter set.
- Wired stability into both optimization paths so it is explicit opt-in for standard optimize and automatic for walk-forward unless skipped.
- Added structured `stability/` artifact writing with importance, heatmap, robustness, and summary outputs that can coexist with `walk_forward/` and `monte_carlo/`.
- Installed `scikit-learn` into the project venv with `uv pip install scikit-learn` so Optuna fANOVA can run in the local environment.
- Locked the full Phase 6 surface with regression coverage spanning config, CLI, walk-forward, Monte Carlo, and stability.

Verification:

- `uv run pytest tests/test_config.py tests/test_cli.py tests/test_optimize_objective.py tests/test_optimization_results.py tests/test_monte_carlo.py tests/test_optimization_stability.py -q`
