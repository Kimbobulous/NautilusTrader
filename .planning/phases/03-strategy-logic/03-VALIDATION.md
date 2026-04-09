---
phase: 03
slug: strategy-logic
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-08
---

# Phase 3 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_strategy_indicators.py tests/test_strategy_logic.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~35 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_strategy_indicators.py tests/test_strategy_logic.py -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 35 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | STRAT-01, STRAT-02, STRAT-05 | T-03-01 / T-03-02 | Rolling indicators update deterministically one bar at a time and respect warm-up gating | unit | `uv run pytest tests/test_strategy_indicators.py -q` | X | pending |
| 03-02-01 | 02 | 2 | STRAT-01, STRAT-02, STRAT-05 | T-03-03 / T-03-04 | Trend and pullback state transitions do not generate setups before confirmed pivots and readiness | unit | `uv run pytest tests/test_strategy_logic.py -q -k "trend or pullback"` | X | pending |
| 03-03-01 | 03 | 3 | STRAT-03, STRAT-05 | T-03-05 / T-03-06 | Entry confirmation only fires when core triggers and at least one optional confirmation are aligned | unit/integration | `uv run pytest tests/test_strategy_logic.py -q -k "entry or trigger or delta"` | X | pending |
| 03-04-01 | 04 | 4 | STRAT-04, STRAT-05 | T-03-07 / T-03-08 | ATR exits ratchet correctly, hard opposite trend flips exit correctly, and the production strategy runs through the shared runner path | integration/smoke | `uv run pytest tests/test_strategy_logic.py tests/test_backtest_runner.py -q` | X | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_strategy_indicators.py` - synthetic-data coverage for each custom rolling indicator class
- [ ] `tests/test_strategy_logic.py` - state-machine, trigger-combination, and exit-behavior coverage
- [ ] `pyproject.toml` - continue declaring pytest support

---

## Manual-Only Verifications

- [ ] Run one bounded real backtest with the production strategy against a short MGC contract window and confirm the runner still produces metrics, trades, and artifacts
- [ ] Confirm trade-tick delta accumulation aligns with completed 1-minute bars in at least one inspected smoke run

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing references
- [ ] No watch-mode flags
- [ ] Feedback latency < 35s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
