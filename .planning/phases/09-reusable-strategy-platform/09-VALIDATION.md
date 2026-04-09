---
phase: 09
slug: reusable-strategy-platform
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 09 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none - existing repo pytest discovery |
| **Quick run command** | `uv run pytest tests/test_strategy_base.py tests/test_strategy_registry.py tests/test_compare.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~60-120 seconds |

---

## Sampling Rate

- After every task commit: run the plan-local verify command for the touched area
- After every plan wave: run `uv run pytest -q`
- Before `/gsd-verify-work`: full suite must be green
- Max feedback latency: 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|--------|
| 09-01-01 | 01 | 1 | PLT-01, PLT-02 | Thin strategy base and extracted primitives preserve MGC behavior while remaining independently testable | unit | `uv run pytest tests/test_strategy_base.py tests/test_strategy_indicators.py tests/test_strategy_logic.py -q` | pending |
| 09-02-01 | 02 | 1 | PLT-03 | Config-driven strategy selection resolves through registry or import override without changing the runner contract | unit/integration | `uv run pytest tests/test_config.py tests/test_strategy_registry.py tests/test_cli.py -q -k "strategy or registry or backtest"` | pending |
| 09-03-01 | 03 | 2 | PLT-04 | Dedicated compare workflow produces two normal runs plus a comparison folder and reuses tearsheet/reporting assets | integration | `uv run pytest tests/test_compare.py tests/test_cli.py tests/test_tearsheet.py -q -k "compare"` | pending |
| 09-04-01 | 04 | 3 | PLT-01, PLT-03, PLT-04 | Golden fixture locks MGC behavior exactly while docs explain how new strategies plug into the platform | integration | `uv run pytest tests/test_strategy_golden.py tests/test_compare.py tests/test_cli.py -q` | pending |

---

## Wave 0 Requirements

- [ ] `tests/test_strategy_base.py` - independent coverage for the thin shared base
- [ ] `tests/test_strategy_registry.py` - registry/import override coverage
- [ ] `tests/test_compare.py` - comparison workflow coverage
- [ ] `tests/test_strategy_golden.py` - permanent bounded regression fixture

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Run a bounded `compare` command and visually confirm the two normal run folders and comparison tearsheet feel coherent | PLT-04 | Side-by-side comparison usability is user-facing and not fully captured by file assertions | Execute a short bounded compare run, open `comparison_tearsheet.html`, and confirm both strategies and metric deltas are visible |
| Read the updated `USAGE.md` add-a-strategy section and confirm it is sufficient for a new contributor | PLT-01, PLT-03 | Documentation clarity is best judged from an operator perspective | Follow the documented steps mentally from config to registry entry and confirm no hidden code edits are required |

---

## Validation Sign-Off

- [ ] All tasks have automated verification or Wave 0 coverage
- [ ] Sampling continuity preserved across all 4 plans
- [ ] Full suite remains green after each wave
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
