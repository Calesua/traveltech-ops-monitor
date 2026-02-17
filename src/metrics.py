# src/metrics.py
from __future__ import annotations

from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
import json
import re


STOPWORDS_ES_EN = {
    # EN
    "the","a","an","and","or","to","of","in","for","on","with","from","by","at","as",
    "is","are","be","this","that","these","those","it","its","you","your","we","our",
    "into","over","under","up","down","out","about","after","before","between","during",
    "best", "top", "new", "latest", "travel", "trip", "guide", "destination", "tourism",
    "visit", "holiday", "why", "how", "things", "one", "them", 
}

WORD_RE = re.compile(r"[A-Za-zÀ-ÿ']{3,}")


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def try_parse_date(s: str | None) -> datetime | None:
    """
    Intenta parsear fechas típicas:
    - ISO 8601 (parsed_at)
    - RSS pubDate: 'Wed, 11 Feb 2026 09:07:10 GMT'
    Devuelve datetime en UTC o None.
    """
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None

    # 1) ISO
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # 2) RSS pubDate (GMT / +0000)
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue

    return None


def effective_dt(item: dict) -> datetime | None:
    """published_at if date was parsed; if not, parsed_at is used."""
    dt = try_parse_date(item.get("published_at"))
    if not dt:
        dt = try_parse_date(item.get("parsed_at"))
    return dt


def tokenize_title(title: str) -> list[str]:
    words = [w.lower() for w in WORD_RE.findall(title or "")]
    return [w for w in words if w not in STOPWORDS_ES_EN]


def top_terms(counter: Counter, n: int = 15) -> list[dict]:
    return [{"term": k, "count": v} for k, v in counter.most_common(n)]

def terms_delta(counter: Counter, n: int = 15) -> list[dict]:
    return [{"term": k, "delta": v} for k, v in counter.most_common(n)]


def compute_metrics(items: list[dict]) -> dict:
    now = datetime.now(timezone.utc)
    d7 = now - timedelta(days=7)
    d14 = now - timedelta(days=14)
    d30 = now - timedelta(days=30)

    total = len(items)

    # Volume
    items_by_source = Counter()

    # Duplicates
    url_counts = Counter()
    title_norm_counts = Counter()

    # Recency / cadence
    items_last_7d_by_source = Counter()
    items_per_day_global = Counter()
    items_per_day_by_source: dict[str, Counter] = defaultdict(Counter)

    # Most recent (store item + effective timestamp fields)
    most_recent_item_by_source: dict[str, dict] = {}

    # Keywords (historical)
    kw_global = Counter()
    kw_by_source: dict[str, Counter] = defaultdict(Counter)

    # Trending keywords (last 7d vs prev 7d)
    kw_last7_global = Counter()
    kw_prev7_global = Counter()
    kw_last7_by_source: dict[str, Counter] = defaultdict(Counter)
    kw_prev7_by_source: dict[str, Counter] = defaultdict(Counter)

    # Debug-like counters
    n_pub_ok = 0
    n_parsed_ok = 0
    n_dt_ok = 0

    for item in items:
        source = item.get("source") or "unknown"
        items_by_source[source] += 1

        # duplicates
        url = (item.get("url") or "").strip()
        if url:
            url_counts[url] += 1

        title = (item.get("title") or "").strip()
        if title:
            tnorm = re.sub(r"\s+", " ", title.lower())
            title_norm_counts[tnorm] += 1

        pub_dt = try_parse_date(item.get("published_at"))
        if pub_dt:
            n_pub_ok += 1
        parsed_dt = try_parse_date(item.get("parsed_at"))
        if parsed_dt:
            n_parsed_ok += 1

        dt = pub_dt or parsed_dt
        if dt:
            n_dt_ok += 1

        # Recency / cadence
        if dt:
            if dt >= d7:
                items_last_7d_by_source[source] += 1

            if dt >= d30:
                day = dt.date().isoformat()
                items_per_day_global[day] += 1
                items_per_day_by_source[source][day] += 1

        # Most recent by source (safe compare)
        mr = most_recent_item_by_source.get(source)
        mr_dt = None
        if mr is not None:
            mr_dt = try_parse_date(mr.get("published_at")) or try_parse_date(mr.get("parsed_at"))

        if mr is None or (dt is not None and (mr_dt is None or dt > mr_dt)):
            most_recent_item_by_source[source] = {
                "title": item.get("title"),
                "url": item.get("url"),
                "published_at": item.get("published_at"),
                "parsed_at": item.get("parsed_at"),
            }

        # Keywords (historical + trending windows)
        tokens = tokenize_title(title)
        if tokens:
            kw_global.update(tokens)
            kw_by_source[source].update(tokens)

            if dt:
                if dt >= d7:
                    kw_last7_global.update(tokens)
                    kw_last7_by_source[source].update(tokens)
                elif d14 <= dt < d7:
                    kw_prev7_global.update(tokens)
                    kw_prev7_by_source[source].update(tokens)

    # Trending: positive deltas only
    kw_delta_global = kw_last7_global - kw_prev7_global
    kw_delta_by_source = {source: (kw_last7_by_source[source] - kw_prev7_by_source[source]) for source in items_by_source.keys()}

    duplicates = {
        "duplicate_urls": sum(1 for _, c in url_counts.items() if c > 1),
        "duplicate_titles": sum(1 for _, c in title_norm_counts.items() if c > 1),
        "top_duplicate_urls": [u for u, c in url_counts.most_common(10) if c > 1],
        "top_duplicate_titles": [t for t, c in title_norm_counts.most_common(10) if c > 1],
    }

    metrics = {
        "generated_at": now.isoformat(),
        "items_total": total,
        "items_by_source": dict(items_by_source),
        "items_last_7d_by_source": dict(items_last_7d_by_source),
        "most_recent_item_by_source": most_recent_item_by_source,
        "cadence_last_30d": {
            "items_per_day_global": dict(items_per_day_global),
            "items_per_day_by_source": {k: dict(v) for k, v in items_per_day_by_source.items()},
        },
        "keywords": {
            "top_global": top_terms(kw_global, 20),
            "top_by_source": {k: top_terms(v, 15) for k, v in kw_by_source.items()},
            "trending_last_7d_vs_prev_7d_global": terms_delta(kw_delta_global, 20),
            "trending_last_7d_vs_prev_7d_by_source": {
                k: terms_delta(v, 15) for k, v in kw_delta_by_source.items()
            },
        },
        "duplicates": duplicates,
        "debug": {
            "published_at_parsed": n_pub_ok,
            "parsed_at_parsed": n_parsed_ok,
            "effective_dt_parsed": n_dt_ok,
        },
    }
    return metrics


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]

    in_path = project_root / "data" / "processed" / "parsed_items.jsonl"
    out_path = project_root / "data" / "processed" / "metrics.json"

    items = read_jsonl(in_path)
    metrics = compute_metrics(items)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] metrics -> {out_path}")


if __name__ == "__main__":
    main()