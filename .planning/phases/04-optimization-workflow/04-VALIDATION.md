---
phase: 04
slug: optimization-workflow
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-09
---

# Phase 4 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_optimize_objective.py tests/test_optimization_results.py tests/test_cli.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~45 seconds plus one bounded manual smoke run |

---

## Sampling Rate

- **After every task commit:** Run the smallest targeted pytest command for the files touched
- **After every plan wave:** Run `uv run pytest tests/test_optimize_objective.py tests/test_optimization_results.py tests/test_cli.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds for automated checks, excluding the manual smoke optimization

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | OPT-01, OPT-02 | T-04-01 / T-04-02 | Trials reuse the shared backtest runner, objective penalties are deterministic, and CLI optimize wiring stays thin | unit/integration | `uv run pytest tests/test_optimize_objective.py tests/test_cli.py -q` | X | pending |
| 04-01-02 | 01 | 1 | OPT-01, OPT-05 | T-04-03 | Optimization config validates runtime limits, seed, study name, and date windows before a study starts | unit | `uv run pytest tests/test_config.py -q -k "optimization"` | X | pending |
| 04-02-01 | 02 | 2 | OPT-02, OPT-03, OPT-05 | T-04-04 / T-04-05 | Ranked outputs, failure logs, and SQLite resume state are persisted deterministically without overwriting canonical runs | unit/integration | `uv run pytest tests/test_optimization_results.py -q` | X | pending |
| 04-03-01 | 03 | 3 | OPT-03, OPT-04, OPT-05 | T-04-06 / T-04-07 | Best-run export, holdout rerun, and overfitting warning behave correctly and keep holdout artifacts distinct from in-sample results | integration | `uv run pytest tests/test_optimization_results.py tests/test_cli.py -q -k "holdout or best or optimize"` | X | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_optimize_objective.py` - objective penalties, early stopping, and search-space sampling coverage
- [ ] `tests/test_optimization_results.py` - ranked CSV, failed-trial JSON, best-run, holdout, and `latest/` persistence coverage
- [ ] `pyproject.toml` - pytest support remains declared
- [ ] Optuna dependency is installed through `uv`

---

## Manual-Only Verifications

- [ ] Run one bounded optimization smoke test with a very small trial budget and confirm progress output, result persistence, and `latest/` refresh
- [ ] Confirm the best-params holdout rerun writes clearly labeled holdout artifacts
- [ ] Confirm the CLI warns when holdout Sharpe is more than `0.3` below in-sample Sharpe in a crafted or real test case

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s for automated checks
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
