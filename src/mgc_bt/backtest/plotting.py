from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


def save_equity_curve_png(equity_curve: list[dict[str, object]], output_path: Path) -> None:
    frame = pd.DataFrame.from_records(equity_curve)
    if frame.empty:
        raise RuntimeError("Cannot plot an empty equity curve.")

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["equity"] = frame["equity"].astype(float)

    figure, axis = plt.subplots(figsize=(12, 6))
    axis.plot(frame["timestamp"], frame["equity"], color="#9c7a2b", linewidth=1.8)
    axis.set_title("Equity Curve")
    axis.set_xlabel("Time (UTC)")
    axis.set_ylabel("Equity")
    axis.grid(True, alpha=0.25)
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(output_path, dpi=144)
    plt.close(figure)
