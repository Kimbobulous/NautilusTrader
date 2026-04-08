# Phase 2: Backtest Runner - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 2-Backtest Runner
**Areas discussed:** Contract handling, execution timing, output structure, reusable runner API

---

## Contract handling mode

| Option | Description | Selected |
|--------|-------------|----------|
| Single-contract only | Debug one specific contract at a time | |
| Auto-rolling only | Always backtest through contract rolls | |
| Both | Single-contract debug mode plus default auto-roll mode | ✓ |

**User's choice:** Both
**Notes:** Default is auto-roll when no instrument id is supplied. Single-contract mode accepts an explicit CLI instrument id.

---

## Roll rule

| Option | Description | Selected |
|--------|-------------|----------|
| Open-interest roll | Switch when back month open interest exceeds front month | ✓ |
| Calendar-only roll | Roll using a fixed business-day rule | |
| Other | User-defined alternative | |

**User's choice:** Open-interest roll with calendar fallback
**Notes:** If open interest is unavailable, roll 5 business days before the contract's last trading day. For v1 planning, MGC last trading day is the third-to-last business day of the delivery month.

---

## Execution timing

| Option | Description | Selected |
|--------|-------------|----------|
| Next-bar execution | Bar-close decision, next-bar fill | ✓ |
| Same-bar close execution | Fill on the same completed bar | |
| Trade-aware execution | Next available trade-aware fill | |

**User's choice:** Next-bar execution
**Notes:** This is the conservative v1 realism choice. Orders are submitted after signal confirmation and should fill at the next bar with 1 tick slippage and `$0.50` per-side commission configured through Nautilus venue/fill settings.

---

## Output structure

| Option | Description | Selected |
|--------|-------------|----------|
| Timestamped run folders | Preserve each run separately | |
| Fixed latest folder | Overwrite a single current result set | |
| Both | Canonical timestamped folder plus refreshed `latest/` | ✓ |

**User's choice:** Both
**Notes:** Canonical outputs go under `results/backtests/YYYY-MM-DD_HHMMSS/`, then `results/backtests/latest/` is refreshed. Required artifacts are `summary.json`, `trades.csv`, `equity_curve.png`, and `run_config.toml`.

---

## Reusable runner API

| Option | Description | Selected |
|--------|-------------|----------|
| CLI-only backtest entry | Run only through shell command | |
| Pure Python core runner | Reusable callable plus CLI wrapper | ✓ |
| Other | User-defined alternative | |

**User's choice:** Pure Python core runner
**Notes:** The core shape must be `run_backtest(config, params) -> dict` so Phase 4 Optuna trials can call the runner in-process without subprocess overhead.

---

## the agent's Discretion

- Internal backtest module split
- Exact plotting/output libraries
- Whether Phase 2 uses a temporary smoke-test strategy harness before Phase 3 implements the real strategy logic

## Deferred Ideas

- Full strategy rules remain in Phase 3
- Any richer execution realism stays out of scope for v1
