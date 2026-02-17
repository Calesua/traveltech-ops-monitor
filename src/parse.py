'''
Normalize and parse the fetched raw data.
Keep in mind that Medium provides an RSS feed, while the other two sources are HTML pages.
'''

from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def parse_medium_rss(path) -> list[dict]:
    root = ET.parse(path).getroot()
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        author = (item.findtext("creator") or "").strip()
        desc = (item.findtext("description") or "").strip()

        items.append({
            "source": "medium_travel",
            "title": title,
            "url": url,
            "published_at": pub or None,
            "author": author or None,
            "summary": desc or None,
            "raw_file": str(path),
            "parsed_at": now_utc_iso(),
        })
    return items

def parse_lonelyplanet_html(path) -> list[dict]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")
        items = []
        for a in soup.select('a[href*="/articles/"]'):
            href = a.get("href") or ""
            text = a.get_text(" ", strip=True) or ""
            if not href or not text:
                continue

            if len(text) < 8:
                continue

            if href.startswith("/"):
                url = "https://www.lonelyplanet.com" + href
            else:
                url = href

            items.append(
                {
                    "source": "lonelyplanet_articles",
                    "title": text,
                    "url": url,
                    "published_at": None,
                    "author": None,
                    "summary": None,
                    "raw_file": str(path),
                    "parsed_at": now_utc_iso(),
                }
            )
        return items



def parse_nomadicmatt_html(path) -> list[dict]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

        items = []
        for a in soup.select("h2 a[href]"):
            href = (a.get("href") or "").strip()
            title = (a.get_text(" ", strip=True) or "").strip()
            
            if not href or not title:
                continue

            if "nomadicmatt.com" not in href:
                continue

            if href.rstrip("/") == "https://www.nomadicmatt.com/travel-blog": # skip post listing page
                continue

            items.append(
                {
                    "source": "nomadicmatt_blog",
                    "title": title,
                    "url": href,
                    "published_at": None,
                    "author": None,
                    "summary": None,
                    "raw_file": str(path),
                    "parsed_at": now_utc_iso(),
                }
            )

        return items

def parse_all(raw_dir) -> list[dict]:
    rows: list[dict] = []

    medium_path = raw_dir / "medium_travel.xml"
    lp_path = raw_dir / "lonelyplanet_articles.html"
    nm_path = raw_dir / "nomadicmatt_blog.html"

    if medium_path.exists():
        rows.extend(parse_medium_rss(medium_path))
    if lp_path.exists():
        rows.extend(parse_lonelyplanet_html(lp_path))
    if nm_path.exists():
        rows.extend(parse_nomadicmatt_html(nm_path))

    return rows

def write_jsonl(items, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    raw_dir = project_root / "data" / "raw"
    out_path = project_root / "data" / "processed" / "parsed_items.jsonl"

    items = parse_all(raw_dir)
    write_jsonl(items, out_path)
    print(f"[OK] Parsed {len(items)} items -> {out_path}")