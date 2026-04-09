from __future__ import annotations

from pathlib import Path
import csv
import html

import plotly.graph_objects as go

from mgc_bt.reporting.loaders import load_tearsheet_payload
from mgc_bt.reporting.tearsheet import ChartEmbedder
from mgc_bt.reporting.tearsheet import render_html_document


def write_comparison_tearsheet(
    *,
    comparison_dir: Path,
    strategy_a_run_dir: Path,
    strategy_b_run_dir: Path,
    strategy_a_label: str,
    strategy_b_label: str,
) -> Path:
    payload_a = load_tearsheet_payload(strategy_a_run_dir)
    payload_b = load_tearsheet_payload(strategy_b_run_dir)
    metrics_delta = _read_csv_rows(comparison_dir / "metrics_delta.csv")

    embedder = ChartEmbedder()
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=[row["timestamp"] for row in payload_a.underwater_curve or []],
            y=[float(row["equity"]) for row in payload_a.underwater_curve or []],
            name=strategy_a_label,
            line={"color": "#17c3a5", "width": 2},
        ),
    )
    figure.add_trace(
        go.Scatter(
            x=[row["timestamp"] for row in payload_b.underwater_curve or []],
            y=[float(row["equity"]) for row in payload_b.underwater_curve or []],
            name=strategy_b_label,
            line={"color": "#4fc3f7", "width": 2},
        ),
    )
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="#111c2f",
        plot_bgcolor="#111c2f",
        title="Equity curve comparison",
        margin={"l": 40, "r": 20, "t": 40, "b": 30},
    )

    table_rows = "".join(
        "<tr>"
        f"<td>{html.escape(row['metric'])}</td>"
        f"<td>{html.escape(str(row['strategy_a']))}</td>"
        f"<td>{html.escape(str(row['strategy_b']))}</td>"
        f"<td>{html.escape(str(row['delta_b_minus_a']))}</td>"
        "</tr>"
        for row in metrics_delta
    )
    body = f"""
<section class="hero">
  <h1>Strategy comparison</h1>
  <div class="subtle">A: {html.escape(strategy_a_label)}</div>
  <div class="subtle">B: {html.escape(strategy_b_label)}</div>
</section>
<section class="section">
  <div class="section-header"><h2>Equity curves</h2></div>
  {embedder.render(figure, div_id="comparison-equity")}
</section>
<section class="section">
  <div class="section-header"><h2>Metric deltas</h2></div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Metric</th><th>{html.escape(strategy_a_label)}</th><th>{html.escape(strategy_b_label)}</th><th>Delta B-A</th></tr>
      </thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>
</section>
"""
    output_path = comparison_dir / "comparison_tearsheet.html"
    output_path.write_text(render_html_document(title="comparison_tearsheet.html", body=body), encoding="utf-8")
    return output_path


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
