# 05-02 Summary

## What Changed

- Added shared preflight validation under [preflight.py](C:/dev/nautilustrader/src/mgc_bt/validation/preflight.py).
- Added [health.py](C:/dev/nautilustrader/src/mgc_bt/validation/health.py) and wired `python -m mgc_bt health`.
- Updated the CLI so `ingest`, `backtest`, and `optimize` all run preflight checks before execution.
- Wrapped malformed TOML parsing in a clear `ConfigError`.
- Added actionable CLI failure paths for:
  - missing catalog data
  - invalid backtest ranges or instrument IDs
  - future holdout windows
  - missing `--resume` studies
- Retained a shared Nautilus log guard in the backtest runner so repeated in-process backtest calls remain stable during optimization and holdout reruns.

## Why It Matters

The workflow now tells the user what is wrong before a long run starts, and the new `health` command gives one place to verify the entire local setup.

## Verification

- `uv run pytest tests/test_config.py tests/test_cli.py -q`
- `uv run python -m mgc_bt health`
