# Phase 9: Reusable Strategy Platform - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 09-reusable-strategy-platform
**Areas discussed:** generic strategy base, indicator extraction boundary, strategy switching, comparison workflow, comparison output, behavior-preservation validation

---

## Generic Strategy Base

| Option | Description | Selected |
|--------|-------------|----------|
| Thin base | Shared lifecycle, audit, risk, and artifact plumbing only | ✓ |
| Heavy framework | Shared lifecycle plus standardized strategy hook structure | |
| Minimal wrapper | Very little shared infrastructure beyond config plumbing | |

**User's choice:** Thin event-driven base class.
**Notes:** Each strategy owns its own signal engine fully. The base class must never dictate indicator usage or signal composition.

---

## Indicator Extraction Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Indicators only | Extract pure indicators and rolling utilities only | |
| Indicators + signal primitives | Extract indicators plus candle, delta, absorption, and related primitives | ✓ |
| Near-full engine | Extract most of the current signal engine into reusable pieces | |

**User's choice:** Indicators plus reusable signal primitives.
**Notes:** MGC-specific signal-combination logic must stay in the MGC strategy and not be generalized prematurely.

---

## Strategy Switching

| Option | Description | Selected |
|--------|-------------|----------|
| Named registry | Only short strategy names in config | |
| Import paths only | Only explicit dotted import paths | |
| Hybrid | Named registry by default with optional import override | ✓ |

**User's choice:** Hybrid registry plus explicit override.
**Notes:** `mgc_production` remains the default and new strategies should be add-and-register rather than requiring runner edits.

---

## Strategy Comparison Workflow

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated command | Add a separate `compare` command | ✓ |
| Extend backtest | Add comparison flags to `backtest` | |
| API first | Keep comparison as library-only for now | |

**User's choice:** Dedicated `compare` command.
**Notes:** The user wants the normal `backtest` command to stay clean and unambiguous.

---

## Comparison Output Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Single rich comparison folder | One unified folder with all artifacts | |
| Two normal runs + lightweight comparison | Preserve normal run folders and add a small comparison summary folder | ✓ |
| Full paired comparison bundle | Larger comparison-specific artifact system | |

**User's choice:** Two normal run folders plus a lightweight comparison summary.
**Notes:** Reuse the current tearsheet and artifact system instead of building a new reporting path.

---

## Behavior-Preservation Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Structural only | Rely on existing tests and public-behavior checks | |
| Golden only | Exact deterministic fixture checks only | |
| Hybrid | Add a permanent golden fixture plus keep the full suite passing | ✓ |

**User's choice:** Hybrid validation.
**Notes:** Phase 9 is explicitly refactor-only. A permanent golden fixture is required so future refactors cannot silently change MGC behavior.

---

## the agent's Discretion

- Exact registry internals
- Exact base-class hook naming
- Exact comparison tearsheet composition beyond the required side-by-side summary content

## Deferred Ideas

None.
