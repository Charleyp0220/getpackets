"""
scrapers/primegov.py — PrimeGov portal scraper.

PrimeGov cities are at: https://{slug}.primegov.com/public/portal
The portal page renders meeting rows in HTML with PDF links.

Confirmed working from search results:
  lacity.primegov.com       — Los Angeles
  fresno.primegov.com       — Fresno
  glendaleca.primegov.com   — Glendale CA
  fostercity.primegov.com   — Foster City CA
  paramountcity.primegov.com — Paramount CA
  sacog.primegov.com        — Sacramento COG
"""

import requests, re
from datetime import date, timedelta
from bs4 import BeautifulSoup
from utils import (classify_body, is_future_or_today, parse_date,
                   date_str, download_packet)
from constants import HEADERS, REQUEST_TIMEOUT

PRIMEGOV_CITIES = {
    # California
    "lacity":           ("California",    "Los Angeles"),
    "longbeachca":      ("California",    "Long Beach"),
    "glendaleca":       ("California",    "Glendale"),
    "fostercity":       ("California",    "Foster City"),
    "paramountcity":    ("California",    "Paramount"),
    "sacog":            ("California",    "Sacramento COG"),
    "sanjoseca":        ("California",    "San Jose"),
    "stocktonca":       ("California",    "Stockton"),
    "irvine":           ("California",    "Irvine"),
    "santaana":         ("California",    "Santa Ana"),
    "anaheim":          ("California",    "Anaheim"),
    "oxnard":           ("California",    "Oxnard"),
    "fontana":          ("California",    "Fontana"),
    "morenovalley":     ("California",    "Moreno Valley"),
    "lancaster":        ("California",    "Lancaster"),
    "palmdale":         ("California",    "Palmdale"),
    "victorville":      ("California",    "Victorville"),
    "corona":           ("California",    "Corona"),
    "westcovina":       ("California",    "West Covina"),
    "downey":           ("California",    "Downey"),
    "costasmesa":       ("California",    "Costa Mesa"),
    "inglewood":        ("California",    "Inglewood"),
    "carlsbad":         ("California",    "Carlsbad"),
    "elgranada":        ("California",    "El Monte"),
    # Texas
    "elpasotx":         ("Texas",         "El Paso"),
    "grandeprairietx":  ("Texas",         "Grand Prairie"),
    "brownsville":      ("Texas",         "Brownsville"),
    "mcallen":          ("Texas",         "McAllen"),
    "killeen":          ("Texas",         "Killeen"),
    "mesquite":         ("Texas",         "Mesquite"),
    "pasadena":         ("Texas",         "Pasadena"),
    "carrollton":       ("Texas",         "Carrollton"),
    "frisco":           ("Texas",         "Frisco"),
    "mckinney":         ("Texas",         "McKinney"),
    "denton":           ("Texas",         "Denton"),
    "allen":            ("Texas",         "Allen"),
    # Florida
    "jacksonvillefl":   ("Florida",       "Jacksonville"),
    "miamifl":          ("Florida",       "Miami"),
    "tampafl":          ("Florida",       "Tampa"),
    "orlandofl":        ("Florida",       "Orlando"),
    "hialeah":          ("Florida",       "Hialeah"),
    "pembrokepines":    ("Florida",       "Pembroke Pines"),
    "hollywood":        ("Florida",       "Hollywood"),
    "coralsprings":     ("Florida",       "Coral Springs"),
    "miramar":          ("Florida",       "Miramar"),
    "portst-lucie":     ("Florida",       "Port St. Lucie"),
    "davie":            ("Florida",       "Davie"),
    "bocaraton":        ("Florida",       "Boca Raton"),
    "deltona":          ("Florida",       "Deltona"),
    "plantation":       ("Florida",       "Plantation"),
    "sunrise":          ("Florida",       "Sunrise"),
    "westpalmbeach":    ("Florida",       "West Palm Beach"),
    # Illinois
    "joliet":           ("Illinois",      "Joliet"),
    "elgin":            ("Illinois",      "Elgin"),
    "waukegan":         ("Illinois",      "Waukegan"),
    "cicero":           ("Illinois",      "Cicero"),
    "champaign":        ("Illinois",      "Champaign"),
    "bloomington":      ("Illinois",      "Bloomington"),
    # Pennsylvania
    "pittsburghpa":     ("Pennsylvania",  "Pittsburgh"),
    "allentownpa":      ("Pennsylvania",  "Allentown"),
    "eriepa":           ("Pennsylvania",  "Erie"),
    "readingpa":        ("Pennsylvania",  "Reading"),
    "scrantonpa":       ("Pennsylvania",  "Scranton"),
    "bethlehem":        ("Pennsylvania",  "Bethlehem"),
    # Michigan
    "detroitmi":        ("Michigan",      "Detroit"),
    "warrenmi":         ("Michigan",      "Warren"),
    "sterlingheights":  ("Michigan",      "Sterling Heights"),
    "annarbor":         ("Michigan",      "Ann Arbor"),
    "flint":            ("Michigan",      "Flint"),
    "dearborn":         ("Michigan",      "Dearborn"),
    "livonia":          ("Michigan",      "Livonia"),
    # Georgia
    "atlantaga":        ("Georgia",       "Atlanta"),
    "augustaga":        ("Georgia",       "Augusta"),
    "columbusga":       ("Georgia",       "Columbus"),
    "savannahga":       ("Georgia",       "Savannah"),
    "maconga":          ("Georgia",       "Macon"),
    "athensga":         ("Georgia",       "Athens"),
    # Ohio
    "clevelandoh":      ("Ohio",          "Cleveland"),
    "cincinnatoh":      ("Ohio",          "Cincinnati"),
    "toledooh":         ("Ohio",          "Toledo"),
    "akronoh":          ("Ohio",          "Akron"),
    "daytonoh":         ("Ohio",          "Dayton"),
    "cantonoh":         ("Ohio",          "Canton"),
    # Indiana
    "indianapolisin":   ("Indiana",       "Indianapolis"),
    "fortwaynein":      ("Indiana",       "Fort Wayne"),
    "evansvillein":     ("Indiana",       "Evansville"),
    "southbendin":      ("Indiana",       "South Bend"),
    # Virginia
    "virginiabch":      ("Virginia",      "Virginia Beach"),
    "chesapeakeva":     ("Virginia",      "Chesapeake"),
    "richmondva":       ("Virginia",      "Richmond"),
    "newportnews":      ("Virginia",      "Newport News"),
    "alexandriava":     ("Virginia",      "Alexandria"),
    "hamptonva":        ("Virginia",      "Hampton"),
    # Washington
    "seattlewa":        ("Washington",    "Seattle"),
    "spokanewa":        ("Washington",    "Spokane"),
    "tacomawa":         ("Washington",    "Tacoma"),
    "bellevuewa":       ("Washington",    "Bellevue"),
    "everettwa":        ("Washington",    "Everett"),
    "rentonwa":         ("Washington",    "Renton"),
    "kentwa":           ("Washington",    "Kent"),
    # Massachusetts
    "bostonma":         ("Massachusetts", "Boston"),
    "worcesterma":      ("Massachusetts", "Worcester"),
    "lowellma":         ("Massachusetts", "Lowell"),
    "cambridgema":      ("Massachusetts", "Cambridge"),
    # Missouri
    "kansascitymo":     ("Missouri",      "Kansas City"),
    "stlouismo":        ("Missouri",      "St. Louis"),
    "springfieldmo":    ("Missouri",      "Springfield"),
    # Maryland
    "baltimormd":       ("Maryland",      "Baltimore"),
    # Minnesota
    "minneapolismn":    ("Minnesota",     "Minneapolis"),
    "stpaulmn":         ("Minnesota",     "Saint Paul"),
    # Arizona
    "phoenixaz":        ("Arizona",       "Phoenix"),
    "tucsonaz":         ("Arizona",       "Tucson"),
    "mesaaz":           ("Arizona",       "Mesa"),
    "chandleraz":       ("Arizona",       "Chandler"),
    "scottsdaleaz":     ("Arizona",       "Scottsdale"),
    "gilbertaz":        ("Arizona",       "Gilbert"),
    "tempeaz":          ("Arizona",       "Tempe"),
    "glendaleaz":       ("Arizona",       "Glendale"),
    # Colorado
    "denverco":         ("Colorado",      "Denver"),
    "auroracol":        ("Colorado",      "Aurora"),
    "arvadaco":         ("Colorado",      "Arvada"),
    "westminsterco":    ("Colorado",      "Westminster"),
    "centennialco":     ("Colorado",      "Centennial"),
    "thorntonco":       ("Colorado",      "Thornton"),
    "boulderco":        ("Colorado",      "Boulder"),
    # Kentucky
    "louisvillky":      ("Kentucky",      "Louisville"),
    "lexingtonky":      ("Kentucky",      "Lexington"),
    # Oklahoma
    "oklahomacity":     ("Oklahoma",      "Oklahoma City"),
    "tulsaok":          ("Oklahoma",      "Tulsa"),
    # Louisiana
    "neworleans":       ("Louisiana",     "New Orleans"),
    "shreveport":       ("Louisiana",     "Shreveport"),
    "batonrouge":       ("Louisiana",     "Baton Rouge"),
    # Connecticut
    "hartfordct":       ("Connecticut",   "Hartford"),
    "bridgeportct":     ("Connecticut",   "Bridgeport"),
    "newhavenct":       ("Connecticut",   "New Haven"),
    "stamfordct":       ("Connecticut",   "Stamford"),
    # Nevada
    "lasvegasnv":       ("Nevada",        "Las Vegas"),
    "hendersonnv":      ("Nevada",        "Henderson"),
    "renonv":           ("Nevada",        "Reno"),
    "northlasvegas":    ("Nevada",        "North Las Vegas"),
    # Oregon
    "portlandor":       ("Oregon",        "Portland"),
    "eugeneor":         ("Oregon",        "Eugene"),
    "salemor":          ("Oregon",        "Salem"),
    # Utah
    "saltlakecity":     ("Utah",          "Salt Lake City"),
    "westvalleycity":   ("Utah",          "West Valley City"),
    "provout":          ("Utah",          "Provo"),
    "westjordanut":     ("Utah",          "West Jordan"),
    # Nebraska
    "omahanb":          ("Nebraska",      "Omaha"),
    "lincolnnb":        ("Nebraska",      "Lincoln"),
    # New Mexico
    "albuquerquenm":    ("New Mexico",    "Albuquerque"),
    # New Jersey
    "newarknj":         ("New Jersey",    "Newark"),
    "jerseycitynj":     ("New Jersey",    "Jersey City"),
    # Wisconsin
    "milwaukeewi":      ("Wisconsin",     "Milwaukee"),
    "madisonwi":        ("Wisconsin",     "Madison"),
    # Iowa
    "desmoines":        ("Iowa",          "Des Moines"),
    "cedarrapids":      ("Iowa",          "Cedar Rapids"),
    # Kansas
    "wichita":          ("Kansas",        "Wichita"),
    "overlandpark":     ("Kansas",        "Overland Park"),
    # Alabama
    "birminghamal":     ("Alabama",       "Birmingham"),
    "montgomeral":      ("Alabama",       "Montgomery"),
    "huntsvilleal":     ("Alabama",       "Huntsville"),
    "mobileal":         ("Alabama",       "Mobile"),
    # South Carolina
    "columbiasc":       ("South Carolina","Columbia"),
    "charlestonsc":     ("South Carolina","Charleston"),
    # Tennessee
    "nashvilletn":      ("Tennessee",     "Nashville"),
    "memphistn":        ("Tennessee",     "Memphis"),
    "knoxvilletn":      ("Tennessee",     "Knoxville"),
    "chattanoogtn":     ("Tennessee",     "Chattanooga"),
    # North Carolina
    "charlottenc":      ("North Carolina","Charlotte"),
    "raleighnc":        ("North Carolina","Raleigh"),
    "greensbornc":      ("North Carolina","Greensboro"),
    "durhamnc":         ("North Carolina","Durham"),
    # Idaho
    "boiseid":          ("Idaho",         "Boise"),
    # Rhode Island
    "providenceri":     ("Rhode Island",  "Providence"),
    # Hawaii
    "honolulhi":        ("Hawaii",        "Honolulu"),
    # Alaska
    "anchorageak":      ("Alaska",        "Anchorage"),
}

PRIMEGOV_BASE = "https://{slug}.primegov.com/public/portal"


def scrape_primegov(state: str, collected: list, max_packets: int) -> int:
    """Scrape PrimeGov portals for a given state."""
    cities = {slug: info for slug, info in PRIMEGOV_CITIES.items()
              if info[0] == state}
    if not cities:
        return 0

    added = 0
    today = date.today()

    for slug, (st, display_name) in cities.items():
        if len(collected) >= max_packets:
            break

        url = PRIMEGOV_BASE.format(slug=slug)
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "lxml")
        except Exception:
            continue

        # PrimeGov portal lists upcoming meetings
        for row in soup.select(".meeting-row, .meeting, tr, li, .list-item"):
            if len(collected) >= max_packets:
                break

            row_text  = row.get_text(" ", strip=True)
            body_type = classify_body(row_text)
            if not body_type:
                continue

            date_match = re.search(
                r"(January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+\d{1,2},?\s*\d{4}|"
                r"\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}",
                row_text, re.IGNORECASE
            )
            if not date_match:
                continue
            meeting_date = parse_date(date_match.group(0))
            if not is_future_or_today(meeting_date):
                continue

            agenda_url = None
            for a in row.select("a[href]"):
                href  = a["href"]
                label = a.get_text(strip=True).lower()
                if not href.startswith("http"):
                    href = f"https://{slug}.primegov.com{href}"
                if any(x in href.lower() or x in label
                       for x in ["agenda", "packet", ".pdf", "document",
                                  "compiledMeetingDocumentFiles",
                                  "Meeting?meetingTemplateId"]):
                    agenda_url = href
                    break
            if not agenda_url:
                continue

            name_el   = row.select_one("h2, h3, .title, strong, b, .meeting-title")
            body_name = name_el.get_text(strip=True) if name_el else \
                        body_type.replace("_", " ").title()

            dl = download_packet(agenda_url, st, display_name,
                                 body_type, date_str(meeting_date))
            if not dl:
                continue

            collected.append({
                "state":        st,
                "municipality": display_name,
                "place_type":   "city",
                "body_name":    body_name,
                "body_type":    body_type,
                "meeting_date": date_str(meeting_date),
                "meeting_time": "",
                "location":     "",
                "source_url":   url,
                "platform":     "PrimeGov",
                **dl,
            })
            added += 1

    return added
