'''
Fetch data from multiple sources, which at the moment are the following:
- Medium.com - Offers a wide range of travel-related articles, including personal travel stories, tips, and destination guides.
- Lonely Planet - Provides travel news, destination guides, and travel tips from experts in the field.
- Nomadic Matt - A popular travel blog that offers travel tips, destination guides, and personal travel stories from the perspective of a budget traveler.
'''

from pathlib import Path
import time
from http import HTTPStatus
import requests
from requests.exceptions import RequestException

url1 = "https://medium.com/feed/tag/travel"
url2 = "https://www.lonelyplanet.com/articles"
url3 = "https://www.nomadicmatt.com/travel-blog/"

sources = {
    "medium_travel": (url1, "xml"),
    "lonelyplanet_articles": (url2, "html"),
    "nomadicmatt_blog": (url3, "html"),
}

retries = 3
retry_codes = [
    HTTPStatus.TOO_MANY_REQUESTS,
    HTTPStatus.INTERNAL_SERVER_ERROR,
    HTTPStatus.BAD_GATEWAY,
    HTTPStatus.SERVICE_UNAVAILABLE,
    HTTPStatus.GATEWAY_TIMEOUT,
]



project_root = Path(__file__).resolve().parents[1]
raw_pages_dir = project_root / "data" / "raw"

def fetch(url):
    for n in range(retries):
        try:
            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "traveltech-ops-monitor/0.1",
                    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
                },
                )
            response.raise_for_status()
            ct = response.headers.get("Content-Type", "")
            print("Fetched URL: {}, Content-Type: {}".format(url, ct))
            return response
        except RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
                
            if status is not None and status in retry_codes and n < retries - 1:
                # retry after n+1 seconds
                print(f"[RETRY] status={status}, sleeping {n+1}s...")
                time.sleep(n+1)
                continue

            print(f"[ERROR] {exc}")
            raise

def save_to_file(response, filename):
    try:
        Path(raw_pages_dir / filename).write_text(response.text, encoding="utf-8", errors="ignore")
        print(f"Saved {filename} to file.")
    except Exception as exc:
        print(f"Error writing to file: {exc}")

if __name__ == "__main__":
    for name, (url, extension) in sources.items():
        try:
            response = fetch(url)
            save_to_file(response, f"{name}.{extension}")
        except Exception as exc:
            print(f"Failed to fetch {url}: {exc}")