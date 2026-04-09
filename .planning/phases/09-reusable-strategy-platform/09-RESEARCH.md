---
phase: 09
slug: reusable-strategy-platform
status: complete
created: 2026-04-09
---

# Phase 09 - Research

## Goal

Design a reusable strategy platform on top of the shipped backtest, optimization, analytics, and tearsheet stack without changing validated MGC strategy behavior.

## Findings

### 1. Nautilus already provides the right strategy abstraction

- `nt_docs/concepts/strategies.md` confirms the native extension point is still a concrete class inheriting from `Strategy`.
- Nautilus expects strategies to own their own `on_start`, `on_stop`, `on_bar`, `on_trade_tick`, and order/position event handlers.
- That makes a thin event-driven base class the correct Phase 9 shape. A heavy framework with prescriptive signal hooks would fight Nautilus rather than extend it.

### 2. The current MGC architecture already exposes the right refactor seam

- `src/mgc_bt/backtest/strategy.py` already separates a Nautilus `MgcProductionStrategy` wrapper from a strategy-local signal engine and helper logic.
- The strategy file also contains the reusable primitive candidates Phase 9 wants to extract:
  - candle pattern detection
  - delta accumulation
  - absorption confirmation
  - volume average helpers
- This means Phase 9 can preserve MGC behavior by:
  - keeping the MGC signal-combination logic local
  - extracting only true primitives
  - moving plumbing into a shared base without rewriting the decision rules

### 3. Strategy switching should happen at the `ImportableStrategyConfig` seam

- `src/mgc_bt/backtest/configuration.py` hardcodes:
  - `strategy_path="mgc_bt.backtest.strategy:MgcProductionStrategy"`
  - `config_path="mgc_bt.backtest.strategy:MgcStrategyConfig"`
- That is the cleanest Phase 9 insertion point for:
  - a named strategy registry
  - an optional fully-qualified import override
- The shared execution contract in `src/mgc_bt/backtest/runner.py` can stay unchanged if strategy resolution happens before `BacktestRunConfig` is built.

### 4. Typed TOML config is already the platform contract

- `src/mgc_bt/config.py` is the canonical settings boundary and already validates phase-specific defaults.
- Phase 9 should extend this layer rather than introduce ad hoc CLI-only strategy settings.
- A registry-friendly config model should keep the common case simple:
  - `strategy = "mgc_production"`
- Advanced users can then override with an explicit class path while still flowing through the same typed config loader.

### 5. Comparison should reuse ordinary runs, not invent a second-class mode

- The project already has:
  - standard backtest result bundles
  - analytics generation
  - tearsheets
  - comparison-friendly reporting infrastructure in `src/mgc_bt/reporting/`
- The lowest-risk comparison architecture is:
  - run strategy A as a normal backtest
  - run strategy B as a normal backtest
  - derive a lightweight comparison folder from those existing artifacts
- This aligns with the locked Phase 9 decision to keep two normal run folders plus one comparison folder.

### 6. Golden regression protection is necessary before major refactor seams move

- Phase 9 is explicitly refactor-only, but it touches the most behavior-sensitive code path in the project.
- The existing broad test suite is necessary but not sufficient, because a refactor can preserve public structure while still changing trade timing or filtering.
- A permanent deterministic golden fixture should therefore lock:
  - exact trade count
  - exact total PnL
  - exact Sharpe
  - for one bounded MGC backtest window
- This fixture should live alongside the regular suite and run on every `uv run pytest -q`.

## Implementation Implications

### Recommended plan split

1. Extract reusable base/plumbing and standalone indicator primitives first.
2. Add registry-based strategy resolution and config-driven switching second.
3. Build a dedicated `compare` command on top of normal backtest runs third.
4. Finish with golden-fixture protection, documentation, and extensibility hardening.

### Safety constraints

- Do not change current MGC entry/exit/risk logic.
- Keep `run_backtest(settings, params) -> dict` as the core execution path.
- Keep Nautilus-native `Strategy` as the runtime foundation.
- Reuse existing analytics and tearsheet artifacts instead of recomputing them in comparison mode.

## Research Conclusion

Phase 9 should be planned as a behavior-preserving platform refactor with four execution slices:

- reusable strategy base and signal-primitives extraction
- strategy registry and config-driven selection
- dedicated comparison workflow
- golden regression plus operator documentation

This approach matches Nautilus-native patterns, preserves the validated backtest stack, and gives future strategies a real extension path without destabilizing the current MGC system.
