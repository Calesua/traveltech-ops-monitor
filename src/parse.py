'''
Normalize and parse the fetched raw data.
Keep in mind that Medium provides an RSS feed, while the other two sources are HTML pages.
'''

from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

def parse_medium_rss(path) -> list[dict]:
    root = ET.parse(path).getroot()
    items = []
    for item in root.iter("item"):
        items.append({
            "title": item.find("title").text if item.find("title") is not None else None,
            "link": item.find("link").text if item.find("link") is not None else None,
            "description": item.find("description").text if item.find("description") is not None else None,
        })
    return items

def parse_lonelyplanet_html(path) -> list[dict]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

        

def parse_nomadicmatt_html(path) -> list[dict]:
    return

def parse_all(raw_dir) -> list[dict]:
    return

def write_jsonl(items, out_path):
    return