"""
scrapers/texas_open_meetings.py — Texas Open Meetings Portal scraper.

Texas law requires ALL government bodies to post meeting notices to:
https://www.comptroller.texas.gov/transparency/open-government/search/notice/

This covers every city, county, school board, water district,
and special district in Texas — thousands of entities.
"""

import requests, re
from datetime import date, timedelta
from bs4 import BeautifulSoup
from utils import classify_body, parse_date, date_str, download_packet, is_future_or_today
from constants import HEADERS, REQUEST_TIMEOUT

TEXAS_PORTAL = "https://www.comptroller.texas.gov/transparency/open-government/search/notice/"
TEXAS_API    = "https://www.comptroller.texas.gov/transparency/open-government/search/notice/results/"

# Body type keywords to filter for planning/zoning/council meetings
RELEVANT_BODIES = [
    "city council", "planning", "zoning", "board of adjustment",
    "commissioners court", "county commission", "board of trustees",
    "city commission", "town council", "village council",
    "development", "historic", "environmental", "subdivision",
    "transportation", "redevelopment", "housing",
]


def scrape_texas_open_meetings(state: str, collected: list, max_packets: int) -> int:
    """Scrape Texas open meetings portal for agenda packets."""
    if state != "Texas":
        return 0

    added  = 0
    today  = date.today()
    start  = (today - timedelta(days=7)).strftime("%m/%d/%Y")
    end    = (today + timedelta(days=60)).strftime("%m/%d/%Y")

    # Search parameters
    params = {
        "startDate": start,
        "endDate":   end,
        "pageSize":  200,
        "page":      1,
    }

    try:
        r = requests.get(TEXAS_API, params=params, headers=HEADERS,
                        timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return 0
        data = r.json()
    except Exception:
        # Fall back to HTML scraping
        return _scrape_texas_html(collected, max_packets, start, end)

    meetings = data.get("results", data.get("items", []))
    if not meetings:
        return _scrape_texas_html(collected, max_packets, start, end)

    for m in meetings:
        if len(collected) >= max_packets:
            break

        body_name = m.get("entityName", "") or m.get("name", "")
        if not any(kw in body_name.lower() for kw in RELEVANT_BODIES):
            continue

        body_type = classify_body(body_name)
        if not body_type:
            body_type = "city_council"

        meeting_date = parse_date(m.get("meetingDate", "") or m.get("date", ""))
        if not meeting_date:
            continue

        # Get agenda PDF
        agenda_url = m.get("agendaUrl") or m.get("agenda_url") or m.get("fileUrl")
        if not agenda_url:
            continue

        municipality = (m.get("city", "") or
                       m.get("entityCity", "") or
                       re.sub(r"\s+(city|town|county|district).*", "",
                              body_name, flags=re.IGNORECASE).strip())
        if not municipality:
            municipality = body_name[:40]

        dl = download_packet(agenda_url, "Texas", municipality,
                            body_type, date_str(meeting_date))
        if not dl or dl.get("failed"):
            continue

        collected.append({
            "state": "Texas", "municipality": municipality,
            "place_type": "city", "body_name": body_name,
            "body_type": body_type, "meeting_date": date_str(meeting_date),
            "meeting_time": m.get("meetingTime", ""),
            "location": m.get("location", ""),
            "source_url": TEXAS_PORTAL, "platform": "TX-OpenMeetings",
            **dl,
        })
        added += 1

    return added


def _scrape_texas_html(collected, max_packets, start, end):
    """HTML fallback scraper for Texas open meetings portal."""
    added = 0
    try:
        params = {"startDate": start, "endDate": end}
        r = requests.get(TEXAS_PORTAL, params=params,
                        headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return 0
        soup = BeautifulSoup(r.text, "lxml")
    except Exception:
        return 0

    for row in soup.select("tr, .result-row, .meeting-item, li"):
        if len(collected) >= max_packets:
            break

        row_text = row.get_text(" ", strip=True)
        if not any(kw in row_text.lower() for kw in RELEVANT_BODIES):
            continue

        body_type = classify_body(row_text)
        if not body_type:
            continue

        date_match = re.search(
            r"\d{1,2}/\d{1,2}/\d{4}|"
            r"(January|February|March|April|May|June|July|August|"
            r"September|October|November|December)\s+\d{1,2},?\s*\d{4}",
            row_text, re.IGNORECASE
        )
        if not date_match:
            continue
        meeting_date = parse_date(date_match.group(0))
        if not is_future_or_today(meeting_date):
            continue

        agenda_url = None
        for a in row.select("a[href]"):
            href = a["href"]
            label = a.get_text(strip=True).lower()
            if not href.startswith("http"):
                href = "https://www.comptroller.texas.gov" + href
            if any(x in href.lower() or x in label
                   for x in [".pdf", "agenda", "notice", "packet"]):
                agenda_url = href
                break
        if not agenda_url:
            continue

        # Extract city/entity name
        name_el = row.select_one("td:first-child, .entity-name, strong")
        body_name = name_el.get_text(strip=True) if name_el else "Texas Government"
        municipality = re.sub(r"\s+(planning|zoning|council|commission|board).*",
                              "", body_name, flags=re.IGNORECASE).strip()

        dl = download_packet(agenda_url, "Texas", municipality or body_name[:30],
                            body_type, date_str(meeting_date))
        if not dl or dl.get("failed"):
            continue

        collected.append({
            "state": "Texas", "municipality": municipality or body_name[:30],
            "place_type": "city", "body_name": body_name,
            "body_type": body_type, "meeting_date": date_str(meeting_date),
            "meeting_time": "", "location": "",
            "source_url": TEXAS_PORTAL, "platform": "TX-OpenMeetings",
            **dl,
        })
        added += 1

    return added
