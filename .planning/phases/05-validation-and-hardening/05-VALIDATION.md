---
phase: 05
slug: validation-and-hardening
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-09
---

# Phase 5 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_config.py tests/test_cli.py tests/test_optimization_results.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~60 seconds automated plus short manual CLI smoke checks |

---

## Sampling Rate

- **After every task commit:** Run the narrowest relevant pytest command for the changed area
- **After every plan wave:** Run `uv run pytest tests/test_config.py tests/test_cli.py tests/test_optimization_results.py -q`
- **Before `/gsd-verify-work`:** Full suite must pass
- **Max feedback latency:** ~60 seconds for automated checks

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | CLI-01, DATA-06, BT-06, OPT-05 | T-05-01 / T-05-02 | Fragile workflow edges are protected by regression coverage for malformed config, missing catalog, resume misuse, and persisted output integrity | unit/integration | `uv run pytest tests/test_config.py tests/test_cli.py tests/test_optimization_results.py -q` | X | pending |
| 05-02-01 | 02 | 2 | CLI-01, DATA-06, BT-06 | T-05-03 / T-05-04 | Shared preflight checks fail fast on integrity problems and power both command execution and `health` summaries | unit/integration | `uv run pytest tests/test_cli.py -q -k "health or missing or resume or config"` | X | pending |
| 05-03-01 | 03 | 3 | CLI-01, BT-06, OPT-05 | T-05-05 / T-05-06 | Result directories avoid unsafe overwrites, write manifests, gate `latest/` refresh behind `--force`, and document repeatable usage clearly | unit/integration | `uv run pytest tests/test_backtest_artifacts.py tests/test_optimization_results.py tests/test_cli.py -q` | X | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] Existing tests remain green before Phase 5 execution begins
- [ ] `tests/test_config.py` remains the config-validation anchor
- [ ] `tests/test_cli.py` remains the CLI-facing regression anchor
- [ ] `tests/test_optimization_results.py` remains the optimization persistence anchor

---

## Manual-Only Verifications

- [ ] Run `uv run python -m mgc_bt health` and confirm it reports ingest, backtest, and optimize readiness separately
- [ ] Run one bounded backtest and confirm manifest generation plus `latest/` overwrite behavior with and without `--force`
- [ ] Run one bounded optimize and confirm manifest generation, resume validation, and `latest/` overwrite behavior with and without `--force`
- [ ] Review `USAGE.md` end to end and confirm commands and output paths match current code

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s for automated checks
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
