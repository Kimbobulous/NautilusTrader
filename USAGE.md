# MGC BT Usage

This project is a local Windows CLI workflow for loading Databento MGC data into a Nautilus catalog, running backtests, and running Optuna optimization.

## Environment

- Activate the existing virtual environment:
  - `.venv\Scripts\activate`
- Run commands from the project root:
  - `C:\dev\nautilustrader`
- Use `uv` for Python command execution and package management.

## Main Commands

### Health Check

Run this first when you want to verify the local setup before a long run:

```powershell
uv run python -m mgc_bt health
```

What it checks:
- ingest readiness
- backtest readiness
- optimization readiness

The summary tells you what is:
- `READY`
- `MISSING`
- `ATTENTION`

### Ingest

Load local Databento files into the Nautilus catalog:

```powershell
uv run python -m mgc_bt ingest
```

Expected output:
- counts for definitions, bars, and trades
- catalog date range
- data quality warnings when applicable

### Backtest

Run the default auto-roll backtest:

```powershell
uv run python -m mgc_bt backtest
```

Run a single-contract debug backtest:

```powershell
uv run python -m mgc_bt backtest --instrument-id MGCJ1.GLBX
```

Run a bounded date window:

```powershell
uv run python -m mgc_bt backtest --start-date 2021-03-08T00:00:00+00:00 --end-date 2021-03-08T06:00:00+00:00
```

Refresh `results/backtests/latest/` explicitly:

```powershell
uv run python -m mgc_bt backtest --force
```

Without `--force`, the canonical timestamped run folder is still written, but `latest/` is left untouched.

Strategy selection for normal backtests comes from `configs/settings.toml`:

```toml
[backtest]
strategy = "mgc_production"
strategy_class = ""
```

`strategy` is the common-case named registry selector. `strategy_class` is an advanced override using `package.module:ClassName`.

### Optimize

Run optimization with the configured study:

```powershell
uv run python -m mgc_bt optimize
```

Resume an existing study:

```powershell
uv run python -m mgc_bt optimize --resume --study-name mgc-v1
```

Run with a smaller temporary trial cap:

```powershell
uv run python -m mgc_bt optimize --max-trials 20
```

Refresh `results/optimization/latest/` explicitly:

```powershell
uv run python -m mgc_bt optimize --force
```

Without `--force`, the canonical timestamped optimization folder is still written, but `latest/` is left untouched.

### Compare

Run two strategies against the same bounded window:

```powershell
uv run python -m mgc_bt compare --strategy-a mgc_production --strategy-b mgc_production --instrument-id MGCJ1.GLBX --start-date 2021-03-09T00:00:00+00:00 --end-date 2021-03-10T23:59:00+00:00
```

Use an explicit import override for one side when you are testing an unregistered strategy:

```powershell
uv run python -m mgc_bt compare --strategy-a mgc_production --strategy-b scratch --strategy-class-b mypackage.strategies:MyStrategy --instrument-id MGCJ1.GLBX --start-date 2021-03-09T00:00:00+00:00 --end-date 2021-03-10T23:59:00+00:00
```

## Output Layout

### Backtest

Canonical runs are written under:

```text
results/backtests/YYYY-MM-DD_HHMMSS/
```

Files:
- `summary.json`
- `trades.csv`
- `equity_curve.png`
- `run_config.toml`
- `manifest.json`
- `tearsheet.html`
- `analytics/`

### Optimization

Canonical runs are written under:

```text
results/optimization/YYYY-MM-DD_HHMMSS/
```

Files:
- `ranked_results.csv`
- `optimization_summary.json`
- `failed_trials.json`
- `run_config.toml`
- `manifest.json`
- `best_run/`
- `top_10/`

`best_run/` contains:
- `summary.json`
- `trades.csv`
- `equity_curve.png`
- `run_config.toml`
- `holdout_results.json`
- `holdout_equity_curve.png`
- `manifest.json`

### Comparison

Comparison runs are written under:

```text
results/comparisons/YYYY-MM-DD_HHMMSS/
```

Files:
- `comparison_summary.json`
- `metrics_delta.csv`
- `comparison_tearsheet.html`

Each side of the comparison still gets its own normal timestamped folder under `results/backtests/`.

## Add A Strategy

Future strategies plug into the existing runner without editing runner or CLI code.

1. Create a Nautilus-native strategy class and config class.
   Example pattern:
   - `MyStrategyConfig`
   - `MyStrategy`
2. Put reusable plumbing in the thin base where appropriate, but keep your signal engine inside the strategy module.
3. Register the strategy in [strategy_registry.py](C:/dev/nautilustrader/src/mgc_bt/backtest/strategy_registry.py) by adding a new named entry.
4. Select it in `configs/settings.toml`:

```toml
[backtest]
strategy = "my_strategy"
strategy_class = ""
```

5. For advanced local experiments, skip registry changes and use an explicit import override instead:

```toml
[backtest]
strategy = "mgc_production"
strategy_class = "mypackage.strategies:MyStrategy"
```

6. Run it with the normal commands:
   - `uv run python -m mgc_bt backtest`
   - `uv run python -m mgc_bt optimize`
   - `uv run python -m mgc_bt compare --strategy-a mgc_production --strategy-b my_strategy ...`

The important rule is that adding a strategy should require only a new class plus a registry entry, not runner or CLI edits.

## Rerun Best Parameters Manually

After an optimization run:

1. Open the run folder’s `optimization_summary.json` to find `best_params`.
2. Open the same run folder’s `run_config.toml` for the exact study window and config values.
3. Run a backtest manually with matching dates or the saved `best_run` artifacts as your reference.

For a direct rerun on the configured backtest path:

```powershell
uv run python -m mgc_bt backtest --force
```

If you want a specific contract or bounded window, add `--instrument-id`, `--start-date`, and `--end-date`.

## Common Errors And Fixes

### `Config file is not valid TOML`

Fix:
- open `configs/settings.toml`
- correct the broken section header, quote, or key/value syntax

### `Catalog data was not found`

Fix:
- run `uv run python -m mgc_bt ingest`
- or point `catalog_root` at a populated catalog in `configs/settings.toml`

### `Instrument '...' was not found in the catalog`

Fix:
- confirm the instrument ID exists in the ingested MGC contracts
- or remove `--instrument-id` to use the default auto-roll path

### `Optuna study '...' does not exist in storage`

Fix:
- run `optimize` without `--resume` first
- or use the correct `--study-name` for an existing study

### `Optimization holdout_end is in the future`

Fix:
- update `[optimization].holdout_end` in `configs/settings.toml`
- use a completed historical end date

## Notes

- This workflow is local and Windows-first.
- `health` is the safest first command before a long optimization run.
- The project uses Nautilus Trader native infrastructure as its base; hardening checks are there to make local operation clearer and safer, not to replace Nautilus behavior.
