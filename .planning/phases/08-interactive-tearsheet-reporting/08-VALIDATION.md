---
phase: 08
slug: interactive-tearsheet-reporting
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 08 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none - existing repo pytest discovery |
| **Quick run command** | `uv run pytest tests/test_tearsheet.py tests/test_cli.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~45-90 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_tearsheet.py tests/test_cli.py -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | VIZ-01, VIZ-02, VIZ-03 | T-08-01 / - | Loader/render foundation consumes filesystem artifacts only and renders explicit unavailable notices for missing optional inputs | unit | `uv run pytest tests/test_tearsheet.py -q -k "loader or missing"` | ✅ | ⬜ pending |
| 08-02-01 | 02 | 1 | VIZ-01, VIZ-03 | T-08-02 / - | Backtest tearsheet generation is self-contained, manifest-aware, and non-blocking | unit/integration | `uv run pytest tests/test_backtest_artifacts.py tests/test_tearsheet.py -q -k "backtest"` | ✅ | ⬜ pending |
| 08-03-01 | 03 | 2 | VIZ-02, VIZ-03 | T-08-03 / - | Optimization tearsheet consumes walk-forward, Monte Carlo, stability, and best-run analytics from disk without rerunning optimization | unit/integration | `uv run pytest tests/test_optimization_results.py tests/test_tearsheet.py -q -k "optimization"` | ✅ | ⬜ pending |
| 08-04-01 | 04 | 3 | VIZ-01, VIZ-02, VIZ-03 | T-08-04 / - | Tearsheet generation failures warn and continue while manifests and CLI summaries remain stable | integration | `uv run pytest tests/test_cli.py tests/test_backtest_artifacts.py tests/test_optimization_results.py tests/test_tearsheet.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_tearsheet.py` - shared loader/rendering/integration coverage for Phase 8

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Open a generated `tearsheet.html` locally and confirm dark theme, section toggles, and Plotly interactions feel usable | VIZ-01, VIZ-02, VIZ-03 | Visual quality and interaction feel are user-facing and not fully captured by automated assertions | Run a bounded backtest and optimize, open each tearsheet in a browser, and verify header, stat cards, charts, collapse toggles, and explicit unavailable notices |
| Sanity-check HTML size for a realistic result folder | VIZ-03 | Artifact usefulness depends on staying reasonably sized for local opening | Generate a representative tearsheet and confirm it opens locally without long stalls or browser warnings |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
