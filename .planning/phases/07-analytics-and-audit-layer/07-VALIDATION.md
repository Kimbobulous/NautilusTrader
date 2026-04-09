---
phase: 07
slug: analytics-and-audit-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 07 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none - existing repo pytest discovery |
| **Quick run command** | `uv run pytest tests/test_backtest_artifacts.py tests/test_optimization_results.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~30-60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest` for the touched analytics/result tests
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | ANL-01 | T-07-01 / - | Audit capture persists required fields without changing order submission behavior | unit | `uv run pytest tests/test_strategy_logic.py -q` | ✅ | ⬜ pending |
| 07-02-01 | 02 | 1 | ANL-02, ANL-03 | T-07-02 / - | Analytics CSVs derive from canonical trades/equity and do not block core backtest artifacts | unit/integration | `uv run pytest tests/test_backtest_artifacts.py -q` | ✅ | ⬜ pending |
| 07-03-01 | 03 | 2 | ANL-04 | T-07-03 / - | Parameter sensitivity uses completed optimization results only and writes machine-readable analytics output | unit/integration | `uv run pytest tests/test_optimization_results.py tests/test_optimization_stability.py -q` | ✅ | ⬜ pending |
| 07-04-01 | 04 | 2 | ANL-01, ANL-02, ANL-03, ANL-04 | T-07-04 / - | Analytics failures warn and continue, manifests include analytics files, CLI contracts remain stable | integration | `uv run pytest tests/test_cli.py tests/test_backtest_artifacts.py tests/test_optimization_results.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_backtest_analytics.py` - synthetic drawdown and breakdown coverage
- [ ] `tests/test_optimization_analytics.py` - parameter sensitivity and optimization analytics coverage

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Inspect a large `audit_log.csv` from a bounded real backtest | ANL-01 | Need a human sanity check that rows are understandable and fields reconcile with strategy behavior | Run a short backtest, open `analytics/audit_log.csv`, and verify rejected and executed setups are both visible |
| Confirm analytics warning text is actionable when a post-processing step is forced to fail | ANL-01, ANL-02, ANL-03, ANL-04 | Warning quality is user-facing and easier to judge manually | Simulate an analytics write failure in a bounded run and confirm the core result bundle still saves with a clear warning |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
