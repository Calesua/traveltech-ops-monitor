from pathlib import Path
from datetime import datetime
import json

OFFTOPIC_TERMS = {
    "medium_travel": {"truck", "tata", "intra", "vehicle", "commercial"},
    "lonelyplanet": {},
    "nomadicmatt": {},
}

def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows

def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)

def build_executive_summary(metrics: dict) -> list[str]:
    total = metrics.get("items_total", 0)
    by_source = metrics.get("items_by_source", {})
    last7 = metrics.get("items_last_7d_by_source", {})
    top_kw = (metrics.get("keywords", {}) or {}).get("top_global", [])[:5]

    # silent source rule: if 0 items in last 7 days (could be missing dates or truly no recent items)
    silent = [source for source, count in last7.items() if count == 0]
    top_kw_str = ", ".join([f"{x['term']}({x['count']})" for x in top_kw]) if top_kw else "n/a"

    bullets = [
        f"Collected **{total}** items across {len(by_source)} sources.",
        f"Top title keywords: **{top_kw_str}**.",
    ]
    if silent:
        bullets.append(f"⚠️ No recent items in last 7 days for: **{', '.join(silent)}** (or missing dates).")
    return bullets

def build_recommendations(metrics: dict) -> list[str]:
    recs = []

    # Content creation
    recs.append("**Content strategy**")
    trending = (metrics.get("keywords", {})
                    .get("trending_last_7d_vs_prev_7d_global") or [])[:5]

    if trending:
        terms = ", ".join(x["term"] for x in trending)
        recs.append(
            f"- Emerging keyword momentum detected: **{terms}**. "
            "Consider prioritizing these topics in upcoming content or SEO pages to capture demand."
        )
    else:
        recs.append(
            "- No clear week-over-week keyword momentum detected yet. "
            "- Trending signals will strengthen as historical data accumulates."
        )

    # Duplicates
    recs.append("")
    recs.append("**Data quality: duplicates and noise**")
    dup = (metrics.get("duplicates") or {})
    if dup.get("duplicate_urls", 0) > 0:
        recs.append("- Investigate duplicate URLs: possible pagination repeats or parsing duplicates.")
    else:
        recs.append("- No URL duplicates detected: parsing + caching look healthy.")

    # Spam keywords
    top_terms = [x["term"] for x in ((metrics.get("keywords") or {}).get("top_global") or [])]
    for source, spam_set in OFFTOPIC_TERMS.items():
        if any(t in spam_set for t in top_terms):
            recs.append(f"- ⚠️ Potential off-topic noise detected in top keywords for source '{source}'. Consider reviewing source quality or adding filters.")
            break
        offtopic = OFFTOPIC_TERMS.get(source, set())
        if any(t in offtopic for t in top_terms):
            recs.append(f"- ⚠️ Possible off-topic noise detected in '{source}'. Consider adding a title-based filter or source quality score.")
        else:
            recs.append(f"- Keyword distribution looks on-topic for '{source}' (heuristic).")

    return recs

def select_example_items(items: list[dict], source: str, n: int = 5) -> list[dict]:
    out = [it for it in items if it.get("source") == source]
    return out[:n]

def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    metrics_path = project_root / "data" / "processed" / "metrics.json"
    items_path = project_root / "data" / "processed" / "parsed_items.jsonl"

    metrics = read_json(metrics_path)
    items = read_jsonl(items_path) if items_path.exists() else []

    generated_at = metrics.get("generated_at") or datetime.utcnow().isoformat()
    date_slug = generated_at[:10]
    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / f"report_{date_slug}.md"

    by_source = metrics.get("items_by_source", {})
    last7 = metrics.get("items_last_7d_by_source", {})
    most_recent = metrics.get("most_recent_item_by_source", {})
    kw = metrics.get("keywords", {})

    lines: list[str] = []
    lines.append(f"# TravelTech Ops Monitor — Report ({date_slug})")
    lines.append("")
    lines.append(f"Generated at: `{generated_at}`")
    lines.append("")

    # Executive summary
    lines.append("## Executive summary")
    for b in build_executive_summary(metrics):
        lines.append(f"- {b}")
    lines.append("")

    # Volume by source
    lines.append("## Volume by source")
    rows = []
    for src, cnt in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        rows.append([src, str(cnt), str(last7.get(src, 0))])
    lines.append(md_table(["Source", "Items (total)", "Items (last 7d)"], rows))
    lines.append("")

    # Most recent by source
    lines.append("## Most recent item by source")
    rows = []
    for src in sorted(by_source.keys()):
        mr = most_recent.get(src) or {}
        title = (mr.get("title") or "").replace("|", "\\|")
        url = mr.get("url") or ""
        pub = mr.get("published_at") or "n/a"
        title_md = f"[{title}]({url})" if url and title else (title or "n/a")
        rows.append([src, title_md, pub])
    lines.append(md_table(["Source", "Item", "Published at"], rows))
    lines.append("")

    # Keywords
    lines.append("## Top keywords (titles)")
    top_global = (kw.get("top_global") or [])[:15]
    lines.append("**Global**: " + ", ".join([f"`{x['term']}`({x['count']})" for x in top_global]) if top_global else "n/a")
    lines.append("")
    lines.append("**By source**")
    for src, top_list in (kw.get("top_by_source") or {}).items():
        top_list = top_list[:12]
        lines.append(f"- **{src}**: " + (", ".join([f"`{x['term']}`({x['count']})" for x in top_list]) if top_list else "n/a"))
    lines.append("")

    # Trending keywords
    trending_global = (kw.get("trending_last_7d_vs_prev_7d_global") or [])[:15]
    trending_by_source = kw.get("trending_last_7d_vs_prev_7d_by_source") or {}

    lines.append("## Trending keywords (last 7d vs previous 7d)")
    lines.append("Signals: positive deltas in title keyword frequency.")
    lines.append("")

    if trending_global:
        lines.append("**Global (top increases)**: " + ", ".join([f"`{x['term']}`(+{x['delta']})" for x in trending_global]))
    else:
        lines.append("**Global (top increases)**: n/a (not enough historical spread yet)")
    lines.append("")

    lines.append("**By source**")
    for src in sorted(by_source.keys()):
        top_list = (trending_by_source.get(src) or [])[:12]
        if top_list:
            lines.append(f"- **{src}**: " + ", ".join([f"`{x['term']}`(+{x['delta']})" for x in top_list]))
        else:
            lines.append(f"- **{src}**: n/a")
    lines.append("")

    # Recommendations
    lines.append("## Recommendations / actions")
    for r in build_recommendations(metrics):
        lines.append(r)
    lines.append("")

    # Examples
    if items:
        lines.append("## Sample items")
        for src in sorted(by_source.keys()):
            ex = select_example_items(items, src, n=5)
            if not ex:
                continue
            lines.append(f"### {src}")
            for it in ex:
                istitle = (it.get("title") or "").strip()
                isurl = (it.get("url") or "").strip()
                pub = it.get("published_at") or "n/a"
                if istitle and isurl:
                    lines.append(f"- [{istitle}]({isurl}) — `{pub}`")
                elif istitle:
                    lines.append(f"- {istitle} — `{pub}`")
            lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] report -> {out_path}")

if __name__ == "__main__":
    main()