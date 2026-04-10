---
phase: 10
slug: full-5-year-optimization-run
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-09
---

# Phase 10 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none |
| **Quick run command** | `uv run pytest tests/test_config.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After config changes:** Run `uv run pytest tests/test_config.py -q`
- **After plan wave completion:** Run `uv run pytest -q`
- **Before phase closeout:** Confirm the saved smoke/full artifact checks passed
- **Max feedback latency:** 30 seconds for automated checks, human-paced for smoke/full runs

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | RES-01 | T-10-01 | Locked date windows and smoke config load through typed TOML without exposing final test | unit | `uv run pytest tests/test_config.py -q` | ✅ | ⬜ pending |
| 10-02-01 | 02 | 2 | RES-01 | T-10-02 | Smoke run artifacts are validated from persisted files before full run approval | manual + filesystem | `uv run pytest -q` | ✅ | ⬜ pending |
| 10-02-02 | 02 | 2 | RES-02 | T-10-03 | Final gate report is produced only from completed artifact bundle and stops before Phase 11 | manual + filesystem | `uv run pytest -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Smoke optimization runs end to end and writes expected artifact bundle | RES-01 | Human runs long-lived optimize command directly | Run smoke health + optimize commands, paste output and run directory, then validate files and key metrics |
| Full 5-year optimization completes and produces stop-gate metrics | RES-01, RES-02 | Human must monitor runtime, resume, and terminal output | Run full health + optimize command, resume if needed, paste final output and run directory, then validate files and produce findings report |
| Tearsheet visual notes are included in the gate report | RES-02 | Browser inspection is human-facing | Open `tearsheet.html`, note the equity curve and walk-forward chart shape, include the observation in the final findings |

---

## Validation Sign-Off

- [x] All tasks have automated verify or manual validation coverage
- [x] Sampling continuity maintained
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
