## 06-03 Summary

- Added deterministic Monte Carlo analysis in `src/mgc_bt/optimization/monte_carlo.py` using realized trade logs only, with both permutation and bootstrap methods plus explicit skip behavior for tiny samples.
- Wired Monte Carlo into optimization so it auto-runs for walk-forward, stays opt-in for standard optimize, and writes the Phase 6 artifact set under `monte_carlo/`.
- Extended CLI summaries to surface Monte Carlo state cleanly for the three cases that matter in practice: completed, skipped by flag, and not requested.
- Added regression coverage for deterministic Monte Carlo math and artifact/schema persistence.

Verification:

- `uv run pytest tests/test_cli.py tests/test_optimization_results.py tests/test_monte_carlo.py -q`
