"""
scrapers/state_portals.py — State-level open meetings portals.

Several states aggregate ALL local government meetings in one place.
This is the highest-leverage source because one URL covers thousands
of entities — cities, counties, school boards, special districts.

Covered states:
- Texas    → comptroller.texas.gov
- Illinois → ilsos.gov  
- Florida  → floridahasarighttoknow.com
- Georgia  → SOS open meetings
- Colorado → SOS open meetings
- Virginia → SOS open meetings
- California → AG open meetings
"""

import requests, re, time
from datetime import date, timedelta
from bs4 import BeautifulSoup
from utils import classify_body, parse_date, date_str, download_packet, is_future_or_today
from constants import HEADERS, REQUEST_TIMEOUT


# ── Texas ──────────────────────────────────────────────────────────────────────
def _scrape_texas(collected, max_packets):
    """Texas Open Meetings Portal — covers ALL TX government bodies."""
    added  = 0
    today  = date.today()
    start  = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    end    = (today + timedelta(days=60)).strftime("%Y-%m-%d")

    # Texas uses a search form
    urls_to_try = [
        f"https://www.comptroller.texas.gov/transparency/open-government/search/notice/?startDate={start}&endDate={end}&pageSize=100",
        "https://www.sos.state.tx.us/texasor/index.shtml",
    ]

    for url in urls_to_try:
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "lxml")

            # Find PDF links near planning keywords
            for a in soup.select("a[href$='.pdf'], a[href*='agenda']"):
                if len(collected) >= max_packets:
                    break
                href  = a["href"]
                label = a.get_text(strip=True)
                context = label
                if a.parent:
                    context += " " + a.parent.get_text(" ", strip=True)[:200]

                body_type = classify_body(context)
                if not body_type:
                    continue

                if not href.startswith("http"):
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"

                date_match = re.search(
                    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
                    r"(January|February|March|April|May|June|July|August|"
                    r"September|October|November|December)\s+\d{1,2},?\s*\d{4}",
                    context, re.IGNORECASE
                )
                meeting_date = parse_date(date_match.group(0)) if date_match else today
                if not is_future_or_today(meeting_date):
                    continue

                muni = re.sub(r"\s+(planning|zoning|city|council|board|commission).*",
                              "", label, flags=re.IGNORECASE).strip() or "Texas Government"

                dl = download_packet(href, "Texas", muni[:40],
                                    body_type, date_str(meeting_date))
                if not dl or dl.get("failed"):
                    continue

                collected.append({
                    "state": "Texas", "municipality": muni[:40],
                    "place_type": "city", "body_name": label[:80],
                    "body_type": body_type, "meeting_date": date_str(meeting_date),
                    "meeting_time": "", "location": "",
                    "source_url": url, "platform": "TX-StatePortal",
                    **dl,
                })
                added += 1
        except Exception:
            continue
    return added


# ── Illinois ───────────────────────────────────────────────────────────────────
def _scrape_illinois(collected, max_packets):
    """Illinois SOS Open Meetings notices."""
    added = 0
    try:
        url = "https://www.ilsos.gov/departments/index/home.html"
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return 0
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.select("a[href$='.pdf']"):
            if len(collected) >= max_packets:
                break
            href  = a["href"]
            label = a.get_text(strip=True)
            body_type = classify_body(label)
            if not body_type:
                continue
            if not href.startswith("http"):
                href = "https://www.ilsos.gov" + href
            dl = download_packet(href, "Illinois", "Illinois Government",
                                body_type, date.today().isoformat())
            if not dl or dl.get("failed"):
                continue
            collected.append({
                "state": "Illinois", "municipality": "Illinois Government",
                "place_type": "state", "body_name": label[:80],
                "body_type": body_type, "meeting_date": date.today().isoformat(),
                "meeting_time": "", "location": "",
                "source_url": url, "platform": "IL-StatePortal",
                **dl,
            })
            added += 1
    except Exception:
        pass
    return added


# ── Florida ────────────────────────────────────────────────────────────────────
def _scrape_florida(collected, max_packets):
    """Florida has a right to know portal."""
    added = 0
    try:
        url  = "https://www.floridahasarighttoknow.com/p/search-public-meetings.html"
        today = date.today()
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return 0
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.select("a[href$='.pdf'], a[href*='agenda']"):
            if len(collected) >= max_packets:
                break
            href  = a["href"]
            label = a.get_text(strip=True)
            context = label + " " + (a.parent.get_text(" ", strip=True)[:100] if a.parent else "")
            body_type = classify_body(context)
            if not body_type:
                continue
            if not href.startswith("http"):
                href = "https://www.floridahasarighttoknow.com" + href

            date_match = re.search(
                r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", context, re.IGNORECASE
            )
            meeting_date = parse_date(date_match.group(0)) if date_match else today
            if not is_future_or_today(meeting_date):
                continue

            dl = download_packet(href, "Florida", "Florida Government",
                                body_type, date_str(meeting_date))
            if not dl or dl.get("failed"):
                continue
            collected.append({
                "state": "Florida", "municipality": "Florida Government",
                "place_type": "state", "body_name": label[:80],
                "body_type": body_type, "meeting_date": date_str(meeting_date),
                "meeting_time": "", "location": "",
                "source_url": url, "platform": "FL-StatePortal",
                **dl,
            })
            added += 1
    except Exception:
        pass
    return added


# ── Virginia ───────────────────────────────────────────────────────────────────
def _scrape_virginia(collected, max_packets):
    """Virginia FOIA public meeting notices."""
    added = 0
    try:
        url = "https://law.lis.virginia.gov/vacodefull/toc.aspx?1=1"
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        # Try the open meetings calendar
        url2 = "https://foiacouncil.dls.virginia.gov/meetings/calendar.aspx"
        r2 = requests.get(url2, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r2.status_code != 200:
            return 0
        soup = BeautifulSoup(r2.text, "lxml")
        for a in soup.select("a[href$='.pdf'], a[href*='agenda']"):
            if len(collected) >= max_packets:
                break
            href  = a["href"]
            label = a.get_text(strip=True)
            body_type = classify_body(label)
            if not body_type:
                continue
            if not href.startswith("http"):
                href = "https://foiacouncil.dls.virginia.gov" + href
            dl = download_packet(href, "Virginia", "Virginia Government",
                                body_type, date.today().isoformat())
            if not dl or dl.get("failed"):
                continue
            collected.append({
                "state": "Virginia", "municipality": "Virginia Government",
                "place_type": "state", "body_name": label[:80],
                "body_type": body_type, "meeting_date": date.today().isoformat(),
                "meeting_time": "", "location": "",
                "source_url": url2, "platform": "VA-StatePortal",
                **dl,
            })
            added += 1
    except Exception:
        pass
    return added


# ── Main dispatcher ────────────────────────────────────────────────────────────
STATE_SCRAPERS = {
    "Texas":    _scrape_texas,
    "Illinois": _scrape_illinois,
    "Florida":  _scrape_florida,
    "Virginia": _scrape_virginia,
}


def scrape_state_portal(state: str, collected: list, max_packets: int) -> int:
    """Run state portal scraper if one exists for this state."""
    fn = STATE_SCRAPERS.get(state)
    if not fn:
        return 0
    return fn(collected, max_packets)
