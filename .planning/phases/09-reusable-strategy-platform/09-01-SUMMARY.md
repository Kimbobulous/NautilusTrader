# Plan 09-01 Summary

## Outcome

Completed the thin reusable strategy base and extracted reusable signal primitives without changing current MGC trading behavior.

## What Changed

- Added `BaseResearchStrategy` in `src/mgc_bt/backtest/strategy_base.py` for shared runtime plumbing:
  - lifecycle start/stop wiring
  - trade-tick forwarding
  - shared decision handling
  - generic entry order submission
  - position open/close forwarding
  - account equity lookup
- Added `src/mgc_bt/backtest/strategy_primitives.py` with reusable primitives:
  - `DeltaAccumulator`
  - `AbsorptionDetector`
  - `volume_pass`
  - `delta_pass`
  - candle-pattern helpers for pin bars, shaved bars, and inside-bar breakout detection
- Refactored `MgcProductionStrategy` to inherit `BaseResearchStrategy`
- Refactored `MgcSignalEngine` to consume the extracted primitive layer while preserving its MGC-specific signal-combination rules
- Added independent shared-base coverage in `tests/test_strategy_base.py`
- Extended primitive coverage in `tests/test_strategy_indicators.py`

## Verification

- `uv run pytest tests/test_strategy_base.py tests/test_strategy_indicators.py tests/test_strategy_logic.py -q`
  - `19 passed`
- `uv run python -m mgc_bt backtest --instrument-id MGCJ1.GLBX --start-date 2021-03-09T00:00:00+00:00 --end-date 2021-06-30T23:59:00+00:00`
  - `Total PnL: -33.0`
  - `Win rate: 28.5714`
  - `Max drawdown: 36.5`
  - `Total trades: 14`

## Notes

- The reusable layer is intentionally thin. MGC-specific signal composition remains in `src/mgc_bt/backtest/strategy.py`.
- The traded bounded backtest stayed stable after the refactor, so Phase 9 can continue to registry/config switching from a safe baseline.
