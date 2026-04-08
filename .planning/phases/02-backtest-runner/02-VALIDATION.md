---
phase: 02
slug: backtest-runner
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-08
---

# Phase 2 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_backtest_contracts.py tests/test_backtest_runner.py tests/test_backtest_artifacts.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_backtest_contracts.py tests/test_backtest_runner.py tests/test_backtest_artifacts.py -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | BT-01, BT-02, BT-03, BT-04 | T-02-01 / T-02-02 | Venue config, roll logic, and bar-close next-bar assumptions are deterministic and explicit | unit | `uv run pytest tests/test_backtest_contracts.py -q` | ✅ | ⬜ pending |
| 02-02-01 | 02 | 2 | BT-01, BT-05, BT-06 | T-02-03 / T-02-04 | CLI and Python runner share one execution path and return structured metrics | unit/smoke | `uv run pytest tests/test_backtest_runner.py -q` | ✅ | ⬜ pending |
| 02-03-01 | 03 | 3 | BT-05, BT-06, BT-07 | T-02-05 / T-02-06 | Result artifacts are reproducible, machine-readable, and refreshed into `latest/` safely | unit | `uv run pytest tests/test_backtest_artifacts.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_backtest_contracts.py` - verify contract-mode selection, roll fallback behavior, and config translation
- [ ] `tests/test_backtest_runner.py` - verify `run_backtest(config, params) -> dict` and CLI wrapping
- [ ] `tests/test_backtest_artifacts.py` - verify summary/trade/artifact output structure and `latest/` refresh
- [ ] `pyproject.toml` - continues to declare pytest test command support

---

## Manual-Only Verifications

- [ ] Run one bounded real backtest smoke test against the local catalog and confirm the summary includes metrics plus an instrument id
- [ ] Confirm the chosen Nautilus 1.225.0 fill/venue configuration actually enforces the intended next-bar execution assumptions

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
