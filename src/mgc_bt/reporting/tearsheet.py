from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
import html
import math
import statistics
import tomllib
from typing import Any

import plotly.graph_objects as go
import plotly.io as pio

from mgc_bt.reporting.loaders import SECTION_UNAVAILABLE_PREFIX
from mgc_bt.reporting.loaders import TearsheetPayload
from mgc_bt.reporting.loaders import load_tearsheet_payload


class _ChartEmbedder:
    def __init__(self) -> None:
        self._included_bundle = False

    def render(self, figure: go.Figure, *, div_id: str) -> str:
        include_bundle = not self._included_bundle
        self._included_bundle = True
        html_text = pio.to_html(
            figure,
            full_html=False,
            include_plotlyjs=include_bundle,
            config={"responsive": True, "displaylogo": False},
            div_id=div_id,
        )
        return _sanitize_embedded_html(html_text)


def write_tearsheet(run_dir: Path | str) -> Path:
    payload = load_tearsheet_payload(Path(run_dir))
    html_text = render_tearsheet(payload)
    output_path = payload.run_dir / "tearsheet.html"
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


def render_tearsheet(payload: TearsheetPayload) -> str:
    embedder = _ChartEmbedder()
    sections = [
        _render_header(payload),
        _render_executive_summary(payload),
        _render_equity_section(payload, embedder),
        _render_drawdown_section(payload, embedder),
        _render_trade_analysis(payload, embedder),
        _render_breakdowns(payload, embedder),
        _render_audit_diagnostics(payload, embedder),
    ]
    if payload.run_type == "optimize":
        sections.append(_render_optimization_section(payload, embedder))
    sections.append(_render_footer(payload))
    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>tearsheet.html</title>
  <style>
    :root {{
      --bg: #0b1220;
      --panel: #111c2f;
      --panel-2: #16243b;
      --text: #d8e5f4;
      --muted: #93a8c0;
      --pos: #17c3a5;
      --neg: #ef5b5b;
      --warn: #f5b942;
      --grid: rgba(255,255,255,0.08);
      --border: rgba(255,255,255,0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: 'Segoe UI', Tahoma, sans-serif; background: radial-gradient(circle at top, #13233c, var(--bg) 45%); color: var(--text); }}
    .page {{ max-width: 1360px; margin: 0 auto; padding: 24px; }}
    .hero, .section, .footer-panel {{ background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); border: 1px solid var(--border); border-radius: 18px; padding: 20px; margin-bottom: 18px; }}
    .hero h1, .section h2 {{ margin: 0 0 10px; }}
    .subtle {{ color: var(--muted); }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-top: 18px; }}
    .stat {{ background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 14px; }}
    .stat .label {{ color: var(--muted); font-size: 0.9rem; }}
    .stat .value {{ font-size: 1.5rem; font-weight: 700; margin-top: 6px; }}
    .value.pos {{ color: var(--pos); }}
    .value.neg {{ color: var(--neg); }}
    .value.warn {{ color: var(--warn); }}
    .section-header {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 12px; }}
    .toggle {{ background: var(--panel-2); color: var(--text); border: 1px solid var(--border); border-radius: 999px; padding: 8px 12px; cursor: pointer; }}
    .notice {{ background: rgba(239,91,91,0.12); color: #ffc5c5; border-left: 4px solid var(--neg); padding: 12px; border-radius: 10px; }}
    .grid-2 {{ display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }}
    .grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
    .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 14px; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 8px 10px; border-bottom: 1px solid var(--grid); text-align: left; font-size: 0.92rem; }}
    th {{ color: var(--muted); }}
    pre {{ margin: 0; white-space: pre-wrap; word-break: break-word; color: var(--text); }}
    .path-list code {{ display: block; padding: 3px 0; color: var(--muted); }}
    @media (max-width: 980px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="page">
    {body}
  </div>
  <script>
    function toggleSection(id, button) {{
      const node = document.getElementById(id);
      const hidden = node.style.display === 'none';
      node.style.display = hidden ? 'block' : 'none';
      button.textContent = hidden ? 'Hide' : 'Show';
    }}
  </script>
</body>
</html>"""


def _render_header(payload: TearsheetPayload) -> str:
    strategy_name = payload.summary.get("strategy_name") or "MGC Strategy"
    generated = payload.manifest.get("generated_at") if payload.manifest else datetime.now(tz=UTC).isoformat()
    return f"""
<section class="hero">
  <h1>{html.escape(strategy_name)}</h1>
  <div class="subtle">Instrument: {html.escape(str(payload.summary.get("instrument_id", "unknown")))}</div>
  <div class="subtle">Date range: {html.escape(str(payload.summary.get("start_date", "n/a")))} to {html.escape(str(payload.summary.get("end_date", "n/a")))}</div>
  <div class="subtle">Generated: {html.escape(str(generated))}</div>
</section>"""


def _render_executive_summary(payload: TearsheetPayload) -> str:
    pnls = [_to_float(trade.get("realized_pnl", trade.get("pnl", 0.0))) for trade in payload.trades]
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    profit_factor = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
    cards = [
        ("Total PnL", payload.summary.get("total_pnl"), _pnl_class(_to_float(payload.summary.get("total_pnl")))),
        ("Sharpe ratio", payload.summary.get("sharpe_ratio"), _threshold_class(_to_float(payload.summary.get("sharpe_ratio")), good=1.0, bad=0.5)),
        ("Win rate", f"{_to_float(payload.summary.get('win_rate')):.2f}%", _threshold_class(_to_float(payload.summary.get("win_rate")), good=55.0, bad=45.0)),
        ("Max drawdown", payload.summary.get("max_drawdown_pct") or payload.summary.get("max_drawdown"), "neg" if _to_float(payload.summary.get("max_drawdown_pct") or payload.summary.get("max_drawdown")) > 20 else "warn"),
        ("Total trades", payload.summary.get("total_trades"), "warn"),
        ("Profit factor", round(profit_factor, 4), _threshold_class(profit_factor, good=1.5, bad=1.0)),
    ]
    card_html = "".join(
        f'<div class="stat"><div class="label">{html.escape(label)}</div><div class="value {css}">{html.escape(_format_value(value))}</div></div>'
        for label, value, css in cards
    )
    return f"""
<section class="section">
  <div class="section-header"><h2>Executive summary</h2></div>
  <div class="stats">{card_html}</div>
</section>"""


def _render_equity_section(payload: TearsheetPayload, embedder: _ChartEmbedder) -> str:
    content = _section_start("section-equity", "Equity curve")
    if not payload.underwater_curve:
        content += _notice(payload.notices.get("underwater_curve.csv", "Section unavailable - underwater_curve.csv not found"))
        return content + _section_end()
    equity_x = [row["timestamp"] for row in payload.underwater_curve]
    equity_y = [_to_float(row["equity"]) for row in payload.underwater_curve]
    dd_y = [_to_float(row["underwater_pct"]) for row in payload.underwater_curve]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity_x, y=equity_y, name="Equity", line={"color": "#17c3a5", "width": 2}))
    fig.add_trace(go.Scatter(x=equity_x, y=dd_y, name="Drawdown %", yaxis="y2", line={"color": "#ef5b5b", "width": 1.5}, fill="tozeroy", opacity=0.35))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#111c2f", plot_bgcolor="#111c2f", margin={"l": 40, "r": 40, "t": 40, "b": 30}, yaxis={"title": "Equity"}, yaxis2={"title": "Drawdown %", "overlaying": "y", "side": "right"}, legend={"orientation": "h"})
    content += embedder.render(fig, div_id="equity-chart")
    return content + _section_end()


def _render_drawdown_section(payload: TearsheetPayload, embedder: _ChartEmbedder) -> str:
    content = _section_start("section-drawdown", "Drawdown analysis")
    if not payload.underwater_curve:
        content += _notice(payload.notices.get("underwater_curve.csv", "Section unavailable - underwater_curve.csv not found"))
        return content + _section_end()
    fig = go.Figure([go.Scatter(x=[row["timestamp"] for row in payload.underwater_curve], y=[_to_float(row["underwater_dollars"]) for row in payload.underwater_curve], name="Underwater $", fill="tozeroy", line={"color": "#ef5b5b"})])
    fig.update_layout(template="plotly_dark", paper_bgcolor="#111c2f", plot_bgcolor="#111c2f", margin={"l": 40, "r": 20, "t": 40, "b": 30})
    content += '<div class="grid-2"><div class="card">'
    content += embedder.render(fig, div_id="underwater-chart")
    content += '</div><div class="card"><h3>Drawdown episodes</h3>'
    if payload.drawdown_episodes:
        content += _table(payload.drawdown_episodes[:10], columns=["episode_start", "episode_end", "drawdown_pct", "drawdown_dollars", "recovery_duration_days", "recovered"])
    else:
        content += _notice(payload.notices.get("drawdown_episodes.csv", "Section unavailable - drawdown_episodes.csv not found"))
    content += "</div></div>"
    return content + _section_end()


def _render_trade_analysis(payload: TearsheetPayload, embedder: _ChartEmbedder) -> str:
    content = _section_start("section-trades", "Trade analysis")
    if not payload.trades:
        content += _notice(payload.notices.get("trades.csv", "Section unavailable - trades.csv not found"))
        return content + _section_end()
    returns = [_to_float(item.get("realized_return", item.get("pnl", 0.0))) for item in payload.trades]
    durations = [_trade_duration_minutes(item) for item in payload.trades if _trade_duration_minutes(item) is not None]
    wins = sum(1 for item in payload.trades if _to_float(item.get("realized_pnl", item.get("pnl", 0.0))) > 0)
    losses = max(len(payload.trades) - wins, 0)
    fig_hist = go.Figure([go.Histogram(x=returns, marker={"color": "#17c3a5"})])
    fig_hist.update_layout(template="plotly_dark", paper_bgcolor="#111c2f", plot_bgcolor="#111c2f", margin={"l": 40, "r": 20, "t": 40, "b": 30})
    fig_pie = go.Figure([go.Pie(labels=["Wins", "Losses"], values=[wins, losses], marker={"colors": ["#17c3a5", "#ef5b5b"]})])
    fig_pie.update_layout(template="plotly_dark", paper_bgcolor="#111c2f", margin={"l": 20, "r": 20, "t": 40, "b": 20})
    avg_duration = round(statistics.mean(durations), 2) if durations else 0.0
    content += '<div class="grid-3">'
    content += f'<div class="card">{embedder.render(fig_hist, div_id="trade-return-hist")}</div>'
    content += f'<div class="card">{embedder.render(fig_pie, div_id="trade-winloss-pie")}</div>'
    content += f'<div class="card"><h3>Average trade duration</h3><div class="value warn">{avg_duration} minutes</div></div>'
    content += "</div>"
    return content + _section_end()


def _render_breakdowns(payload: TearsheetPayload, embedder: _ChartEmbedder) -> str:
    content = _section_start("section-breakdowns", "Performance breakdowns")
    chart_blocks: list[str] = []
    for key, title in [("by_session", "By session"), ("by_volatility_regime", "By volatility regime"), ("by_day_of_week", "By day of week"), ("by_hour", "By hour")]:
        rows = payload.breakdowns.get(key, [])
        if rows:
            fig = go.Figure([go.Bar(x=[row["bucket"] for row in rows], y=[_to_float(row["total_pnl"]) for row in rows], marker={"color": "#17c3a5"})])
            fig.update_layout(template="plotly_dark", paper_bgcolor="#111c2f", plot_bgcolor="#111c2f", title=title, margin={"l": 40, "r": 20, "t": 40, "b": 30})
            chart_blocks.append(f'<div class="card">{embedder.render(fig, div_id=f"{key}-chart")}</div>')
        else:
            chart_blocks.append(f'<div class="card"><h3>{html.escape(title)}</h3>{_notice(payload.notices.get(key, f"{SECTION_UNAVAILABLE_PREFIX}{key}.csv not found"))}</div>')
    monthly_rows = _monthly_heatmap_rows(payload.trades)
    if monthly_rows:
        fig = go.Figure(data=go.Heatmap(z=[row["values"] for row in monthly_rows], x=[row["months"] for row in monthly_rows][0], y=[row["year"] for row in monthly_rows], colorscale="RdYlGn"))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#111c2f", plot_bgcolor="#111c2f", title="Monthly PnL heatmap", margin={"l": 40, "r": 20, "t": 40, "b": 30})
        chart_blocks.append(f'<div class="card">{embedder.render(fig, div_id="monthly-heatmap")}</div>')
    else:
        chart_blocks.append(f'<div class="card"><h3>Monthly PnL heatmap</h3>{_notice("Section unavailable - trades.csv not found")}</div>')
    content += f'<div class="grid-3">{"".join(chart_blocks)}</div>'
    return content + _section_end()


def _render_audit_diagnostics(payload: TearsheetPayload, embedder: _ChartEmbedder) -> str:
    content = _section_start("section-audit", "Audit diagnostics")
    if not payload.audit_log:
        content += _notice(payload.notices.get("audit_log.csv", "Section unavailable - audit_log.csv not found"))
        return content + _section_end()
    rejection_counts = Counter(row.get("entry_rejected_reason", "none") for row in payload.audit_log if (row.get("record_type") == "armed_bar" and not _to_bool(row.get("entry_fired"))))
    if rejection_counts:
        fig = go.Figure([go.Bar(x=list(rejection_counts.keys()), y=list(rejection_counts.values()), marker={"color": "#f5b942"})])
        fig.update_layout(template="plotly_dark", paper_bgcolor="#111c2f", plot_bgcolor="#111c2f", title="Entry rejection reasons", margin={"l": 40, "r": 20, "t": 40, "b": 30})
        content += '<div class="grid-2"><div class="card">'
        content += embedder.render(fig, div_id="audit-rejections")
        content += "</div>"
    else:
        content += '<div class="grid-2"><div class="card">'
        content += _notice("Section unavailable - no rejected entries found in audit_log.csv")
        content += "</div>"
    signal_points = _signal_quality_points(payload.audit_log)
    if signal_points:
        fig2 = go.Figure([go.Scatter(x=[item["timestamp"] for item in signal_points], y=[item["optional_confirmation_count"] for item in signal_points], mode="lines+markers", line={"color": "#17c3a5"})])
        fig2.update_layout(template="plotly_dark", paper_bgcolor="#111c2f", plot_bgcolor="#111c2f", title="Signal quality over time", margin={"l": 40, "r": 20, "t": 40, "b": 30})
        content += '<div class="card">'
        content += embedder.render(fig2, div_id="audit-signal-quality")
        content += "</div></div>"
    else:
        content += f'<div class="card">{_notice("Section unavailable - no signal quality rows found in audit_log.csv")}</div></div>'
    return content + _section_end()


def _render_optimization_section(payload: TearsheetPayload, embedder: _ChartEmbedder) -> str:
    content = _section_start("section-optimization", "Optimization sections")
    blocks: list[str] = []
    blocks.append(_optimization_ranked_block(payload, embedder))
    blocks.append(_optimization_walk_forward_block(payload, embedder))
    blocks.append(_optimization_monte_carlo_block(payload, embedder))
    blocks.append(_optimization_stability_block(payload, embedder))
    blocks.append(_optimization_sensitivity_block(payload, embedder))
    content += "".join(blocks)
    return content + _section_end()


def _optimization_ranked_block(payload: TearsheetPayload, embedder: _ChartEmbedder) -> str:
    if not payload.ranked_results:
        return f'<div class="card">{_notice(payload.notices.get("ranked_results.csv", "Section unavailable - ranked_results.csv not found"))}</div>'
    top_rows = payload.ranked_results[:10]
    fig = go.Figure([go.Scatter(x=[row["trial_number"] for row in top_rows], y=[_to_float(row["objective_score"]) for row in top_rows], mode="markers+lines", marker={"color": "#17c3a5"})])
    fig.update_layout(template="plotly_dark", paper_bgcolor="#111c2f", plot_bgcolor="#111c2f", title="Ranked objective scores", margin={"l": 40, "r": 20, "t": 40, "b": 30})
    return f'<div class="card"><h3>Ranked results</h3>{embedder.render(fig, div_id="opt-ranked")}</div>'


def _optimization_walk_forward_block(payload: TearsheetPayload, embedder: _ChartEmbedder) -> str:
    if not payload.walk_forward_windows:
        return f'<div class="card"><h3>Walk-forward</h3>{_notice(payload.notices.get("window_results.csv", "Section unavailable - window_results.csv not found"))}</div>'
    fig = go.Figure([go.Bar(x=[row["window_index"] for row in payload.walk_forward_windows], y=[_to_float(row.get("test_sharpe")) for row in payload.walk_forward_windows], marker={"color": "#4fc3f7"})])
    fig.update_layout(template="plotly_dark", paper_bgcolor="#111c2f", plot_bgcolor="#111c2f", title="Walk-forward test Sharpe by window", margin={"l": 40, "r": 20, "t": 40, "b": 30})
    return f'<div class="card"><h3>Walk-forward</h3>{embedder.render(fig, div_id="opt-wf")}</div>'


def _optimization_monte_carlo_block(payload: TearsheetPayload, embedder: _ChartEmbedder) -> str:
    if not payload.monte_carlo_confidence_bands:
        return f'<div class="card"><h3>Monte Carlo</h3>{_notice(payload.notices.get("equity_confidence_bands.csv", "Section unavailable - equity_confidence_bands.csv not found"))}</div>'
    rows = payload.monte_carlo_confidence_bands
    x = [row.get("trade_index", idx) for idx, row in enumerate(rows)]
    fig = go.Figure()
    for column, color in [("p05", "#ef5b5b"), ("p25", "#f5b942"), ("p50", "#17c3a5"), ("p75", "#4fc3f7"), ("p95", "#9c6bff")]:
        if column in rows[0]:
            fig.add_trace(go.Scatter(x=x, y=[_to_float(row.get(column)) for row in rows], mode="lines", name=column, line={"color": color}))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#111c2f", plot_bgcolor="#111c2f", title="Monte Carlo fan chart", margin={"l": 40, "r": 20, "t": 40, "b": 30})
    return f'<div class="card"><h3>Monte Carlo</h3>{embedder.render(fig, div_id="opt-mc")}</div>'


def _optimization_stability_block(payload: TearsheetPayload, embedder: _ChartEmbedder) -> str:
    if not payload.stability_heatmap_rows:
        return f'<div class="card"><h3>Parameter heatmap</h3>{_notice(payload.notices.get("top_pair_heatmap.csv", "Section unavailable - top_pair_heatmap.csv not found"))}</div>'
    xs = sorted({row["value_x"] for row in payload.stability_heatmap_rows})
    ys = sorted({row["value_y"] for row in payload.stability_heatmap_rows})
    z = []
    for y in ys:
        z.append([
            _to_float(next((row["sharpe_ratio"] for row in payload.stability_heatmap_rows if row["value_x"] == x and row["value_y"] == y), 0.0))
            for x in xs
        ])
    fig = go.Figure(data=go.Heatmap(x=xs, y=ys, z=z, colorscale="Viridis"))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#111c2f", plot_bgcolor="#111c2f", title="Parameter heatmap", margin={"l": 40, "r": 20, "t": 40, "b": 30})
    return f'<div class="card"><h3>Parameter heatmap</h3>{embedder.render(fig, div_id="opt-heatmap")}</div>'


def _optimization_sensitivity_block(payload: TearsheetPayload, embedder: _ChartEmbedder) -> str:
    if not payload.parameter_sensitivity:
        return f'<div class="card"><h3>Parameter sensitivity</h3>{_notice(payload.notices.get("parameter_sensitivity.csv", "Section unavailable - parameter_sensitivity.csv not found"))}</div>'
    rows = payload.parameter_sensitivity
    fig = go.Figure([go.Bar(x=[row["parameter_name"] for row in rows], y=[_to_float(row["sharpe_range_across_buckets"]) for row in rows], marker={"color": ["#17c3a5" if _to_bool(row["most_sensitive"]) else "#4fc3f7" for row in rows]})])
    fig.update_layout(template="plotly_dark", paper_bgcolor="#111c2f", plot_bgcolor="#111c2f", title="Parameter sensitivity", margin={"l": 40, "r": 20, "t": 40, "b": 60})
    return f'<div class="card"><h3>Parameter sensitivity</h3>{embedder.render(fig, div_id="opt-sensitivity")}</div>'


def _render_footer(payload: TearsheetPayload) -> str:
    config_summary = _config_summary(payload.run_config_text)
    path_items = [
        payload.run_dir / "summary.json" if payload.run_type == "backtest" else payload.shared_run_dir / "summary.json",
        payload.run_dir / "tearsheet.html",
        payload.run_dir / "manifest.json",
    ]
    paths = "".join(f"<code>{html.escape(path.as_posix())}</code>" for path in path_items)
    return f"""
<section class="footer-panel">
  <h2>Footer</h2>
  <div class="grid-2">
    <div class="card"><h3>Run config summary</h3><pre>{html.escape(config_summary)}</pre></div>
    <div class="card path-list"><h3>File paths</h3>{paths}</div>
  </div>
</section>"""


def _config_summary(run_config_text: str) -> str:
    if not run_config_text:
        return "Section unavailable - run_config.toml not found"
    try:
        data = tomllib.loads(run_config_text)
    except tomllib.TOMLDecodeError:
        return "Unable to parse run_config.toml"
    lines: list[str] = []
    if "run" in data:
        lines.append(f"mode = {data['run'].get('mode', 'n/a')}")
        lines.append(f"instrument_id = {data['run'].get('instrument_id', 'n/a')}")
    if "best_params" in data:
        best = list(data["best_params"].items())[:8]
        lines.append("best_params:")
        for key, value in best:
            lines.append(f"  {key} = {value}")
    elif "backtest" in data:
        lines.append(f"trade_size = {data['backtest'].get('trade_size', 'n/a')}")
        lines.append(f"slippage_ticks = {data['backtest'].get('slippage_ticks', 'n/a')}")
    return "\n".join(lines)


def _monthly_heatmap_rows(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    buckets: dict[int, dict[int, float]] = {}
    for trade in trades:
        ts_text = trade.get("opened_at") or trade.get("entry_timestamp")
        if not ts_text:
            continue
        ts = datetime.fromisoformat(str(ts_text).replace("Z", "+00:00"))
        buckets.setdefault(ts.year, {})
        buckets[ts.year][ts.month] = buckets[ts.year].get(ts.month, 0.0) + _to_float(trade.get("realized_pnl", trade.get("pnl", 0.0)))
    if not buckets:
        return []
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return [{"year": year, "months": month_names, "values": [round(months.get(idx, 0.0), 4) for idx in range(1, 13)]} for year, months in sorted(buckets.items())]


def _signal_quality_points(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    points = []
    for row in rows:
        if row.get("record_type") != "armed_bar":
            continue
        timestamp = row.get("timestamp")
        if not timestamp:
            continue
        points.append({"timestamp": timestamp, "optional_confirmation_count": _to_float(row.get("optional_confirmation_count"))})
    return points[-250:]


def _trade_duration_minutes(trade: dict[str, Any]) -> float | None:
    start_text = trade.get("opened_at") or trade.get("entry_timestamp")
    end_text = trade.get("closed_at") or trade.get("exit_timestamp")
    if not start_text or not end_text:
        return None
    start = datetime.fromisoformat(str(start_text).replace("Z", "+00:00"))
    end = datetime.fromisoformat(str(end_text).replace("Z", "+00:00"))
    return (end - start).total_seconds() / 60.0


def _section_start(section_id: str, title: str) -> str:
    return f'<section class="section"><div class="section-header"><h2>{html.escape(title)}</h2><button class="toggle" onclick="toggleSection(\'{section_id}\', this)">Hide</button></div><div id="{section_id}">'


def _section_end() -> str:
    return "</div></section>"


def _notice(message: str) -> str:
    return f'<div class="notice">{html.escape(message)}</div>'


def _table(rows: list[dict[str, Any]], *, columns: list[str]) -> str:
    header = "".join(f"<th>{html.escape(column)}</th>" for column in columns)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html.escape(_format_value(row.get(column)))}</td>" for column in columns) + "</tr>")
    return f'<div class="table-wrap"><table><thead><tr>{header}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _format_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if math.isfinite(value):
            return f"{value:.4f}"
        return str(value)
    return str(value)


def _pnl_class(value: float) -> str:
    if value > 0:
        return "pos"
    if value < 0:
        return "neg"
    return "warn"


def _threshold_class(value: float, *, good: float, bad: float) -> str:
    if value >= good:
        return "pos"
    if value < bad:
        return "neg"
    return "warn"


def _to_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes"}


def _sanitize_embedded_html(html_text: str) -> str:
    return (
        html_text.replace("https://", "https-disabled://")
        .replace("http://", "http-disabled://")
        .replace("cdn.plot.ly", "cdn.plotly.local")
    )
