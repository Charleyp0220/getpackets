"""
scrapers/novus.py — Novus Agenda scraper.
Used by many Texas, Oklahoma, Southeast cities.
URL: https://{slug}.novusagenda.com/agendapublic/
"""

import requests, re
from datetime import date
from bs4 import BeautifulSoup
from utils import classify_body, is_future_or_today, parse_date, date_str, download_packet
from constants import HEADERS, REQUEST_TIMEOUT

NOVUS_CITIES = {
    "pearlandtx":      ("Texas",        "Pearland"),
    "leaguecitytx":    ("Texas",        "League City"),
    "sugarlandtx":     ("Texas",        "Sugar Land"),
    "allentx":         ("Texas",        "Allen"),
    "richardsontx":    ("Texas",        "Richardson"),
    "lewisvilletx":    ("Texas",        "Lewisville"),
    "wichitatx":       ("Texas",        "Wichita Falls"),
    "abilenetx":       ("Texas",        "Abilene"),
    "midlandtx":       ("Texas",        "Midland"),
    "odessatx":        ("Texas",        "Odessa"),
    "tylertx":         ("Texas",        "Tyler"),
    "sanmarcostx":     ("Texas",        "San Marcos"),
    "roundrocktx":     ("Texas",        "Round Rock"),
    "edinburgtx":      ("Texas",        "Edinburg"),
    "stilwellok":      ("Oklahoma",     "Stillwater"),
    "edmondok":        ("Oklahoma",     "Edmond"),
    "lawtonok":        ("Oklahoma",     "Lawton"),
    "mooreok":         ("Oklahoma",     "Moore"),
    "birminghamal":    ("Alabama",      "Birmingham"),
    "mobileac":        ("Alabama",      "Mobile"),
    "tuscaloosaal":    ("Alabama",      "Tuscaloosa"),
    "gulfportms":      ("Mississippi",  "Gulfport"),
    "hattiesburgms":   ("Mississippi",  "Hattiesburg"),
    "meridianms":      ("Mississippi",  "Meridian"),
    "columbiasc":      ("South Carolina","Columbia"),
    "greenvillesc":    ("South Carolina","Greenville"),
    "spartanburgsc":   ("South Carolina","Spartanburg"),
    "chesterfield":    ("Virginia",     "Chesterfield"),
    "suffolkva":       ("Virginia",     "Suffolk"),
    "roanokevc":       ("Virginia",     "Roanoke"),
    "lynchburgva":     ("Virginia",     "Lynchburg"),
    "boulderco":       ("Colorado",     "Boulder"),
    "ftcollinsco":     ("Colorado",     "Fort Collins"),
    "greeleync":       ("Colorado",     "Greeley"),
    "lovelandco":      ("Colorado",     "Loveland"),
    "pueblo":          ("Colorado",     "Pueblo"),
    "spokanewa":       ("Washington",   "Spokane"),
    "yakimawa":        ("Washington",   "Yakima"),
    "bellinghamwa":    ("Washington",   "Bellingham"),
    "kennewickwa":     ("Washington",   "Kennewick"),
    "olympiawa":       ("Washington",   "Olympia"),
    "auroraor":        ("Oregon",       "Aurora"),
    "bendor":          ("Oregon",       "Bend"),
    "corvallisore":    ("Oregon",       "Corvallis"),
    "medfordor":       ("Oregon",       "Medford"),
}

NOVUS_BASE = "https://{slug}.novusagenda.com/agendapublic/"


def scrape_novus(state: str, collected: list, max_packets: int) -> int:
    cities = {slug: info for slug, info in NOVUS_CITIES.items()
              if info[0] == state}
    if not cities:
        return 0

    added = 0
    today = date.today()

    for slug, (st, municipality) in cities.items():
        if len(collected) >= max_packets:
            break
        url = NOVUS_BASE.format(slug=slug)
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "lxml")
        except Exception:
            continue

        for row in soup.select("tr, li, .meeting, .agenda-row, div[class*='meeting']"):
            if len(collected) >= max_packets:
                break
            row_text = row.get_text(" ", strip=True)
            body_type = classify_body(row_text)
            if not body_type:
                continue

            date_match = re.search(
                r"(January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+\d{1,2},?\s*\d{4}|"
                r"\d{1,2}/\d{1,2}/\d{4}",
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
                if not href.startswith("http"):
                    href = f"https://{slug}.novusagenda.com{href}"
                label = a.get_text(strip=True).lower()
                if any(x in href.lower() or x in label
                       for x in [".pdf", "agenda", "packet", "view"]):
                    agenda_url = href
                    break
            if not agenda_url:
                continue

            name_el = row.select_one("td:first-child, .body-name, strong")
            body_name = name_el.get_text(strip=True) if name_el else municipality

            dl = download_packet(agenda_url, st, municipality,
                                 body_type, date_str(meeting_date))
            if not dl or dl.get("failed"):
                continue

            collected.append({
                "state": st, "municipality": municipality,
                "place_type": "city", "body_name": body_name,
                "body_type": body_type, "meeting_date": date_str(meeting_date),
                "meeting_time": "", "location": "",
                "source_url": url, "platform": "Novus",
                **dl,
            })
            added += 1

    return added
