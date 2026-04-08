"""
scrapers/finder.py — finds government meeting pages.

Uses parallel requests to test all URL patterns simultaneously
instead of one by one. Much faster.
"""

import requests, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from constants import HEADERS, FINDER_TIMEOUT, MEETING_URL_PATTERNS

MEETING_KEYWORDS = [
    "agenda", "minutes", "meeting", "council", "commission",
    "board", "packet", "planning", "zoning", "public hearing",
]

BAD_KEYWORDS = [
    "page not found", "404", "error", "access denied",
    "under construction", "coming soon",
]


def _make_urls(place: dict) -> list[str]:
    name    = place["name"].lower()
    state   = place.get("state_abbr", "").lower()
    name_hyph  = re.sub(r"\s+", "-", name)
    name_under = re.sub(r"\s+", "_", name)
    name_raw   = re.sub(r"[\s\-]", "", name)
    urls = []
    for pattern in MEETING_URL_PATTERNS:
        url = (pattern
               .replace("{name}",    name_hyph)
               .replace("{name_}",   name_under)
               .replace("{nameraw}", name_raw)
               .replace("{state}",   state))
        urls.append(url)
    seen = set()
    result = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


def _try_url(url: str) -> tuple[str, bool]:
    """Try one URL. Returns (url, is_good)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=FINDER_TIMEOUT,
                        allow_redirects=True)
        if r.status_code != 200:
            return url, False
        text = r.text.lower()
        if any(bad in text for bad in BAD_KEYWORDS):
            return url, False
        if any(kw in text for kw in MEETING_KEYWORDS):
            return url, True
        return url, False
    except Exception:
        return url, False


def find_meeting_url(place: dict) -> str | None:
    """
    Try all URL patterns in parallel and return the first good match.
    Much faster than sequential — all requests fire at once.
    """
    urls = _make_urls(place)
    if not urls:
        return None

    # Fire all requests in parallel, return first good one
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_try_url, url): url for url in urls}
        for future in as_completed(futures):
            try:
                url, is_good = future.result()
                if is_good:
                    # Cancel remaining futures
                    for f in futures:
                        f.cancel()
                    return url
            except Exception:
                pass
    return None
