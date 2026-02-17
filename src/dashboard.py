# src/dashboard.py
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import html as html_lib

import plotly.graph_objects as go


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_date_slug(generated_at: str | None) -> str:
    if not generated_at:
        return datetime.utcnow().isoformat()[:10]
    return generated_at[:10]


def kpi_cards(metrics: dict) -> dict[str, str]:
    total = metrics.get("items_total", 0)
    by_source = metrics.get("items_by_source", {}) or {}
    last7 = metrics.get("items_last_7d_by_source", {}) or {}
    dup = metrics.get("duplicates", {}) or {}

    sources_n = len(by_source)
    last7_total = sum(int(v) for v in last7.values()) if last7 else 0
    dup_urls = int(dup.get("duplicate_urls", 0))
    dup_titles = int(dup.get("duplicate_titles", 0))

    return {
        "Items collected": f"{total}",
        "Sources": f"{sources_n}",
        "Items (last 7d)": f"{last7_total}",
        "Duplicates (URLs / titles)": f"{dup_urls} / {dup_titles}",
    }


def bar_items_by_source(by_source: dict) -> go.Figure:
    sources = list(by_source.keys())
    counts = [by_source[s] for s in sources]

    fig = go.Figure(data=[go.Bar(x=sources, y=counts)])
    fig.update_layout(
        title="Items by source (total)",
        xaxis_title="Source",
        yaxis_title="Items",
        margin=dict(l=40, r=20, t=60, b=40),
        height=360,
    )
    return fig


def bar_items_last7_by_source(last7: dict, by_source: dict) -> go.Figure:
    sources = list(by_source.keys())
    counts = [int(last7.get(s, 0)) for s in sources]

    fig = go.Figure(data=[go.Bar(x=sources, y=counts)])
    fig.update_layout(
        title="Items in last 7 days (published_at → fallback parsed_at)",
        xaxis_title="Source",
        yaxis_title="Items (7d)",
        margin=dict(l=40, r=20, t=60, b=40),
        height=360,
    )
    return fig


def cadence_stack_by_source(cadence: dict, by_source: dict) -> go.Figure:
    """
    Stacked bar by source per day (last 30d). Much more informative than a single line.
    """
    per_source = (cadence or {}).get("items_per_day_by_source", {}) or {}
    all_days = set()
    for src, daymap in per_source.items():
        all_days.update(daymap.keys())
    days = sorted(all_days)

    # If empty, return an empty fig with message
    if not days:
        fig = go.Figure()
        fig.update_layout(
            title="Publishing cadence (last 30 days) — stacked by source",
            annotations=[dict(text="No cadence data available (dates missing)", x=0.5, y=0.5, showarrow=False)],
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            height=380,
        )
        return fig

    fig = go.Figure()
    for src in sorted(by_source.keys()):
        daymap = per_source.get(src, {}) or {}
        y = [int(daymap.get(d, 0)) for d in days]
        fig.add_trace(go.Bar(name=src, x=days, y=y))

    fig.update_layout(
        barmode="stack",
        title="Publishing cadence (last 30 days) — stacked by source",
        xaxis_title="Day",
        yaxis_title="Items",
        margin=dict(l=40, r=20, t=60, b=40),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def bar_top_keywords(top_list: list[dict], title: str, value_field: str = "count") -> go.Figure:
    top_list = top_list or []
    terms = [x.get("term") for x in top_list]
    vals = [x.get(value_field, 0) for x in top_list]

    fig = go.Figure(data=[go.Bar(x=terms, y=vals)])
    fig.update_layout(
        title=title,
        xaxis_title="Keyword",
        yaxis_title=value_field,
        margin=dict(l=40, r=20, t=60, b=40),
        height=380,
    )
    return fig


def most_recent_html_table(most_recent: dict, by_source: dict) -> str:
    rows = []
    for src in sorted(by_source.keys()):
        mr = most_recent.get(src) or {}
        title = (mr.get("title") or "n/a").strip()
        url = (mr.get("url") or "").strip()
        dt = mr.get("published_at") or mr.get("parsed_at") or "n/a"

        title_esc = html_lib.escape(title)
        url_esc = html_lib.escape(url)
        dt_esc = html_lib.escape(str(dt))

        if url:
            title_cell = f'<a href="{url_esc}" target="_blank" rel="noopener noreferrer">{title_esc}</a>'
        else:
            title_cell = title_esc

        rows.append(f"<tr><td>{html_lib.escape(src)}</td><td>{title_cell}</td><td><code>{dt_esc}</code></td></tr>")

    return f"""
            <div class="panel span2">
            <div class="panel-title">Most recent item by source</div>
            <div style="overflow:auto;">
                <table class="tbl">
                <thead><tr><th>Source</th><th>Item</th><th>Date</th></tr></thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
                </table>
            </div>
            </div>
            """

def build_html(
    *,
    title: str,
    generated_at: str,
    kpis: dict[str, str],
    figs: list[go.Figure],
    notes: list[str] | None = None,
    extra_blocks: list[str] | None = None,
) -> str:
    
    plotly_cdn = "https://cdn.plot.ly/plotly-2.27.0.min.js"

    def card_html(label: str, value: str) -> str:
        return f"""
                <div class="kpi-card">
                <div class="kpi-label">{html_lib.escape(label)}</div>
                <div class="kpi-value">{html_lib.escape(str(value))}</div>
                </div>
                """

    parts = []
    parts.append("<!doctype html>")
    parts.append("<html>")
    parts.append("<head>")
    parts.append('<meta charset="utf-8" />')
    parts.append(f"<title>{html_lib.escape(title)}</title>")
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1" />')
    parts.append(f'<script src="{plotly_cdn}"></script>')
    parts.append(
        """
        <style>
        :root{
        --bg:#0b1220;
        --card:#0f1a2e;
        --card2:#111f36;
        --text:#e8eefc;
        --muted:#a9b7d0;
        --border:rgba(255,255,255,0.08);
        --accent:#7aa2ff;
        }

        body{
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
        background: radial-gradient(1200px 700px at 10% 0%, #152b52 0%, var(--bg) 55%);
        color: var(--text);
        margin: 0;
        padding: 26px;
        }

        .header{
        display:flex;
        align-items:flex-end;
        justify-content:space-between;
        gap:16px;
        margin-bottom: 16px;
        }

        h1{ margin:0; font-size: 28px; letter-spacing: 0.2px; }
        .meta{ color: var(--muted); font-size: 13px; }

        .kpi-grid{
        display:grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 16px 0 18px;
        }

        .kpi-card{
        background: linear-gradient(180deg, var(--card) 0%, var(--card2) 100%);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        }

        .kpi-label{ color: var(--muted); font-size: 12px; margin-bottom: 6px; }
        .kpi-value{ font-size: 22px; font-weight: 700; color: var(--text); }

        .note{
        background: rgba(122,162,255,0.10);
        border: 1px solid rgba(122,162,255,0.25);
        padding: 12px 14px;
        border-radius: 14px;
        margin-top: 10px;
        color: var(--text);
        }

        .grid{
        display:grid;
        grid-template-columns: 1fr 1fr;
        gap: 14px;
        margin-top: 12px;
        }

        .panel{
        background: linear-gradient(180deg, rgba(15,26,46,0.92) 0%, rgba(17,31,54,0.92) 100%);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 10px;
        box-shadow: 0 12px 30px rgba(0,0,0,0.24);
        }

        .panel-title{ color: var(--muted); font-size: 13px; margin: 6px 6px 10px; }

        .tbl{ width:100%; border-collapse: collapse; font-size: 13px; }
        .tbl th, .tbl td{ border-top: 1px solid var(--border); padding: 10px 10px; text-align: left; vertical-align: top; }
        .tbl th{ color: var(--muted); font-weight: 600; }
        .tbl a{ color: var(--accent); text-decoration: none; }
        .tbl a:hover{ text-decoration: underline; }

        .span2{ grid-column: span 2; }

        .footer{
        margin-top: 16px;
        color: var(--muted);
        font-size: 12px;
        }

        @media (max-width: 980px){
        .kpi-grid{ grid-template-columns: 1fr 1fr; }
        .grid{ grid-template-columns: 1fr; }
        .span2{ grid-column: span 1; }
        }
        </style>
        """
    )
    parts.append("</head>")
    parts.append("<body>")

    parts.append('<div class="header">')
    parts.append(f"<div><h1>{html_lib.escape(title)}</h1><div class='meta'>Generated at: <code>{html_lib.escape(generated_at)}</code></div></div>")
    parts.append("<div class='meta'>Static HTML • Plotly</div>")
    parts.append("</div>")

    # KPIs
    parts.append('<div class="kpi-grid">')
    for label, value in kpis.items():
        parts.append(card_html(label, value))
    parts.append("</div>")

    # Notes
    if notes:
        parts.append('<div class="note"><b>Notes</b><ul>')
        for n in notes:
            parts.append(f"<li>{html_lib.escape(n)}</li>")
        parts.append("</ul></div>")

    # Panels with plots
    parts.append('<div class="grid">')

    for i, fig in enumerate(figs):
        div_id = f"fig_{i}"
        cls = "panel"
        parts.append(f'<div class="{cls}"><div id="{div_id}"></div></div>')
        spec = fig.to_json()
        parts.append(
            f"""
            <script>
            const spec_{i} = {spec};
            Plotly.newPlot("{div_id}", spec_{i}.data, spec_{i}.layout, {{responsive: true, displayModeBar: false}});
            </script>
            """
        )
    
    if extra_blocks:
        for block in extra_blocks:
            parts.append(block)

    parts.append("</body></html>")

    return "\n".join(parts)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    metrics_path = project_root / "data" / "processed" / "metrics.json"

    metrics = read_json(metrics_path)
    generated_at = metrics.get("generated_at") or datetime.utcnow().isoformat()
    date_slug = safe_date_slug(generated_at)

    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / f"dashboard_{date_slug}.html"

    by_source = metrics.get("items_by_source", {}) or {}
    last7 = metrics.get("items_last_7d_by_source", {}) or {}
    cadence = metrics.get("cadence_last_30d", {}) or {}
    kw = metrics.get("keywords", {}) or {}
    most_recent = metrics.get("most_recent_item_by_source", {}) or {}

    # Figures
    figs: list[go.Figure] = []
    figs.append(bar_items_by_source(by_source))
    figs.append(bar_items_last7_by_source(last7, by_source))
    figs.append(cadence_stack_by_source(cadence, by_source))

    # Keywords panels
    figs.append(bar_top_keywords((kw.get("top_global") or [])[:18], "Top keywords (historical, titles)", value_field="count"))
    figs.append(bar_top_keywords((kw.get("trending_last_7d_vs_prev_7d_global") or [])[:18],
                                 "Trending keywords (last 7d vs previous 7d)",
                                 value_field="delta"))

    # Table
    most_recent_block = most_recent_html_table(most_recent, by_source)

    notes = []
    if not cadence.get("items_per_day_global"):
        notes.append("Cadence uses published_at when available and falls back to parsed_at. Add more historical runs for richer trends.")
    if not (kw.get("trending_last_7d_vs_prev_7d_global") or []):
        notes.append("Trending keywords may be empty if there is not enough week-over-week spread yet.")

    html = build_html(
        title=f"TravelTech Ops Monitor — Dashboard ({date_slug})",
        generated_at=generated_at,
        kpis=kpi_cards(metrics),
        figs=figs,
        notes=notes,
        extra_blocks=[most_recent_block],
    )

    out_path.write_text(html, encoding="utf-8")
    print(f"[OK] dashboard -> {out_path}")


if __name__ == "__main__":
    main()