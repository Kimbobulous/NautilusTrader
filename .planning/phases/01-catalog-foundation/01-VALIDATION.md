---
phase: 01
slug: catalog-foundation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-08
---

# Phase 1 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_cli.py tests/test_databento_discovery.py tests/test_ingest_validation.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_cli.py tests/test_databento_discovery.py tests/test_ingest_validation.py -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | CLI-01, CLI-02, CLI-03 | T-01-01 / T-01-02 | CLI only resolves configured paths and fails clearly on invalid config | unit | `uv run pytest tests/test_cli.py -q` | ✅ | ⬜ pending |
| 01-02-01 | 02 | 2 | DATA-01, DATA-02, DATA-03 | T-01-03 / T-01-04 | Ingest writes definitions before bars/trades and does not decode arbitrary schemas by accident | unit/integration | `uv run pytest tests/test_databento_discovery.py -q` | ✅ | ⬜ pending |
| 01-03-01 | 03 | 3 | DATA-04, DATA-05, DATA-06 | T-01-05 / T-01-06 | Reporting distinguishes structural failures from quality warnings | unit | `uv run pytest tests/test_ingest_validation.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli.py` - verify CLI command registration and config loading
- [ ] `tests/test_databento_discovery.py` - verify exact folder discovery and schema grouping
- [ ] `tests/test_ingest_validation.py` - verify structural failure and warning classification
- [ ] `pyproject.toml` - declare pytest test command support

---

## Manual-Only Verifications

All Phase 1 behaviors should have automated verification. No manual-only verification is required.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
