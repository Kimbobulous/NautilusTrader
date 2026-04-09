# Phase 3: Strategy Logic - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 03-strategy-logic
**Areas discussed:** Trend gate, Pullback and reset behavior, Entry trigger contract, Delta and absorption interpretation, Trade management, Session and time filters, Swing and pivot definition, Candle formation definitions, WaveTrend/Z-score role, Exit precedence

---

## Trend gate

| Option | Description | Selected |
|--------|-------------|----------|
| Adaptive SuperTrend and VWAP must both agree before trades are allowed | Hard binary gate with SuperTrend direction plus VWAP location confirmation | X |
| Adaptive SuperTrend is primary and VWAP is only a filter | SuperTrend can allow trades even if VWAP is not aligned | |
| Looser scoring/weighting model between them | Trend direction would be based on a combined score instead of hard gates | |

**User's choice:** Adaptive SuperTrend is primary, VWAP is secondary, and both must agree as a hard binary gate. No scoring or weighting.
**Notes:** If SuperTrend says bearish there are no longs regardless of VWAP. Longs require price above VWAP; shorts require price below VWAP.

---

## Pullback and reset behavior

| Option | Description | Selected |
|--------|-------------|----------|
| One pullback state per trend leg, then require a fresh trend expansion before re-entry | Restricts repeated attempts inside one trend move | |
| Allow repeated pullback attempts while trend remains valid | Re-arm setups without requiring a fresh expansion leg | X |
| Pullback must also meet a minimum depth or bar-count rule | Add a structural retrace requirement before entry is allowed | X |

**User's choice:** Allow repeated pullback attempts while trend remains valid, with a minimum pullback depth rule.
**Notes:** Entry should not chase trend extremes; price must retrace at least a configurable number of bars from the latest relevant swing.

---

## Entry trigger contract

| Option | Description | Selected |
|--------|-------------|----------|
| Require all trigger families | Delta, absorption, volume, and candle confirmation all mandatory | |
| Require a smaller core set with optional confirmation | Mandatory base triggers plus at least one extra confirmation | X |
| Use a point/score threshold across trigger families | Flexible score-based confirmation model | |

**User's choice:** Use a smaller core set with optional confirmation.
**Notes:** Core triggers are delta imbalance in trend direction and above-average volume. At least one optional confirmation must be present.

---

## Delta and absorption interpretation

| Option | Description | Selected |
|--------|-------------|----------|
| Trades-only interpretation for v1, with absorption approximated from trade/volume/bar behavior | Avoids needing MBP-1 while still defining both concepts concretely | X |
| Extend ingestion/backtest usage to include MBP-1 for a more literal absorption definition | Pulls in order-book-style data for Phase 3 | |
| Implement the rest now and defer absorption to a later phase | Leaves absorption out of the Phase 3 production logic | |

**User's choice:** Trades-only interpretation for v1.
**Notes:** Delta uses trade aggressor side from the trades catalog. Absorption is approximated from bars using high volume, compressed range, and close-in-defense-zone behavior.

---

## Trade management

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed 1-contract entries, no pyramiding, one open position at a time | Simplest and most controlled v1 position model | X |
| Fixed 1-contract entries with same-direction re-entry after flat | Allows repeated setups without adding pyramiding | X |
| Configurable size and limited pyramiding | More flexible but adds complexity to v1 | |

**User's choice:** One contract, no pyramiding, one open position at a time, with same-direction re-entry allowed only after flat.
**Notes:** No scaling in or out.

---

## Session and time filters

| Option | Description | Selected |
|--------|-------------|----------|
| Trade all available Globex data | No schedule-based filtering in v1 | X |
| Trade only a defined intraday window | Restrict to a chosen session | |
| Block low-liquidity windows but otherwise allow broad coverage | Add manual blackout windows | |

**User's choice:** Trade all available Globex data.
**Notes:** The required above-average-volume trigger should naturally suppress many low-liquidity setups.

---

## Swing and pivot definition

| Option | Description | Selected |
|--------|-------------|----------|
| Fractal pivot rule with 2 bars on each side | Confirms swing highs and lows from surrounding structure | X |
| Rolling highest high / lowest low over a lookback window | Simpler rolling-extreme rule | |
| Simpler bar-count-only pullback without explicit pivots | Pullback measured without confirmed swings | |

**User's choice:** Fractal pivot rule with 2 bars on each side.
**Notes:** `min_pullback_bars` measures elapsed bars since the latest confirmed swing low for longs and swing high for shorts.

---

## Candle formation definitions

| Option | Description | Selected |
|--------|-------------|----------|
| Lock explicit geometric rules for each pattern | Exact wick/range/close conditions are specified in advance | X |
| Use only one or two patterns in v1 | Reduce candle logic scope | |
| Keep names but let implementation choose standard definitions | Delegate pattern geometry to the builder | |

**User's choice:** Lock exact geometric rules.
**Notes:** Pin bars, shaved bars, and inside-bar breakouts all count equally as candle confirmation. User provided exact thresholds and breakout confirmation behavior.

---

## WaveTrend / Z-score role

| Option | Description | Selected |
|--------|-------------|----------|
| Either one counts as an optional confirmation | Divergence or Z-score extreme can satisfy the optional-confirmation requirement | X |
| It never counts toward the required optional rule and is only informational/filtering | WaveTrend signals are advisory only | |
| It can replace absorption/candle confirmation if extreme/divergent enough | Strong WaveTrend event substitutes for other optional signals | |

**User's choice:** Either WaveTrend divergence or Z-score extreme counts as an optional confirmation.
**Notes:** The optional-confirmation pool is: absorption, candle formation, WaveTrend divergence, or WaveTrend Z-score extreme.

---

## Exit precedence

| Option | Description | Selected |
|--------|-------------|----------|
| ATR stop only | Ignore trend flips unless the stop is hit | |
| Exit on ATR stop or hard opposite trend flip | Close if both major trend gates reverse against the position | X |
| Exit on ATR stop or opposite trigger-quality setup | Allow a stronger reversal signal to close the trade | |

**User's choice:** Exit on ATR stop or hard opposite trend flip.
**Notes:** A hard opposite trend flip means both SuperTrend and VWAP flip against the current trade direction on the same completed bar. One without the other is not enough to force exit.

---

## the agent's Discretion

- Exact module boundaries under `src/mgc_bt/backtest/`
- Shared helper extraction for rolling-window logic
- Internal enum and helper design for the state machine

## Deferred Ideas

- MBP-1 or order-book-specific absorption logic beyond the bars-only v1 approximation
- Session blocking or liquidity-window filtering beyond the required volume trigger
