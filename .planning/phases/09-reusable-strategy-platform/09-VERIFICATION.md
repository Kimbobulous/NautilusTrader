# Phase 09 Verification

## Golden Regression

- Fixture: `tests/fixtures/mgc_golden_output.json`
- Window:
  - `instrument_id = MGCJ1.GLBX`
  - `start_date = 2021-03-09T00:00:00+00:00`
  - `end_date = 2021-06-30T23:59:00+00:00`
- Exact locked metrics:
  - `total_pnl = -33.0`
  - `sharpe_ratio = -68.603085`
  - `total_trades = 14`
  - `win_rate = 28.5714`
  - `max_drawdown = 36.5`

## Wave Verification

- 09-01:
  - reusable strategy base extracted
  - bounded traded MGC window preserved exactly
- 09-02:
  - registry-first strategy selection added
  - runner contract stayed `run_backtest(settings, params)`
- 09-03:
  - dedicated `compare` command added
  - bounded compare smoke created two normal backtest folders and one comparison folder
- 09-04:
  - permanent golden test added to the normal suite
  - `USAGE.md` documents add/register/select/compare workflow

## Bounded Comparison Smoke

Command:

```powershell
uv run python -m mgc_bt compare --strategy-a mgc_production --strategy-b mgc_production --instrument-id MGCJ1.GLBX --start-date 2021-03-09T00:00:00+00:00 --end-date 2021-03-10T23:59:00+00:00
```

Observed outputs:

- comparison folder: `results/comparisons/2026-04-09_181028`
- run A folder: `results/backtests/2026-04-09_181028_strategy_a`
- run B folder: `results/backtests/2026-04-09_181028_strategy_b`
- comparison tearsheet: `results/comparisons/2026-04-09_181028/comparison_tearsheet.html`

## Full Suite

- `uv run pytest -q`
- Result: `89 passed`

## Final Golden CLI Rerun

Command:

```powershell
uv run python -m mgc_bt backtest --instrument-id MGCJ1.GLBX --start-date 2021-03-09T00:00:00+00:00 --end-date 2021-06-30T23:59:00+00:00
```

Observed result:

- `Total PnL: -33.0`
- `Sharpe ratio: -68.603085`
- `Win rate: 28.5714`
- `Max drawdown: 36.5`
- `Total trades: 14`
- run directory: `results/backtests/2026-04-09_181140`
