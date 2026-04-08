"""
scrapers/municode.py — Municode Meetings scraper.
Municode hosts thousands of US city agenda packets.
URL pattern: https://www.municode.com/meetings/{state}/{city-slug}
"""

import requests, re
from datetime import date
from bs4 import BeautifulSoup
from utils import classify_body, is_future_or_today, parse_date, date_str, download_packet
from constants import HEADERS, REQUEST_TIMEOUT

MUNICODE_CITIES = {
    "alabama/auburn":           ("Alabama",        "Auburn"),
    "alabama/birmingham":       ("Alabama",        "Birmingham"),
    "alabama/huntsville":       ("Alabama",        "Huntsville"),
    "alabama/mobile":           ("Alabama",        "Mobile"),
    "alabama/montgomery":       ("Alabama",        "Montgomery"),
    "arizona/chandler":         ("Arizona",        "Chandler"),
    "arizona/gilbert":          ("Arizona",        "Gilbert"),
    "arizona/mesa":             ("Arizona",        "Mesa"),
    "arizona/phoenix":          ("Arizona",        "Phoenix"),
    "arizona/scottsdale":       ("Arizona",        "Scottsdale"),
    "arizona/tempe":            ("Arizona",        "Tempe"),
    "arizona/tucson":           ("Arizona",        "Tucson"),
    "arkansas/fayetteville":    ("Arkansas",       "Fayetteville"),
    "arkansas/little-rock":     ("Arkansas",       "Little Rock"),
    "california/anaheim":       ("California",     "Anaheim"),
    "california/bakersfield":   ("California",     "Bakersfield"),
    "california/corona":        ("California",     "Corona"),
    "california/elk-grove":     ("California",     "Elk Grove"),
    "california/fontana":       ("California",     "Fontana"),
    "california/fremont":       ("California",     "Fremont"),
    "california/hayward":       ("California",     "Hayward"),
    "california/long-beach":    ("California",     "Long Beach"),
    "california/modesto":       ("California",     "Modesto"),
    "california/moreno-valley": ("California",     "Moreno Valley"),
    "california/ontario":       ("California",     "Ontario"),
    "california/oxnard":        ("California",     "Oxnard"),
    "california/pasadena":      ("California",     "Pasadena"),
    "california/riverside":     ("California",     "Riverside"),
    "california/roseville":     ("California",     "Roseville"),
    "california/sacramento":    ("California",     "Sacramento"),
    "california/salinas":       ("California",     "Salinas"),
    "california/santa-ana":     ("California",     "Santa Ana"),
    "california/santa-clara":   ("California",     "Santa Clara"),
    "california/stockton":      ("California",     "Stockton"),
    "california/sunnyvale":     ("California",     "Sunnyvale"),
    "california/torrance":      ("California",     "Torrance"),
    "california/victorville":   ("California",     "Victorville"),
    "california/visalia":       ("California",     "Visalia"),
    "colorado/aurora":          ("Colorado",       "Aurora"),
    "colorado/boulder":         ("Colorado",       "Boulder"),
    "colorado/colorado-springs":("Colorado",       "Colorado Springs"),
    "colorado/fort-collins":    ("Colorado",       "Fort Collins"),
    "colorado/greeley":         ("Colorado",       "Greeley"),
    "colorado/lakewood":        ("Colorado",       "Lakewood"),
    "colorado/thornton":        ("Colorado",       "Thornton"),
    "colorado/westminster":     ("Colorado",       "Westminster"),
    "florida/cape-coral":       ("Florida",        "Cape Coral"),
    "florida/coral-springs":    ("Florida",        "Coral Springs"),
    "florida/fort-lauderdale":  ("Florida",        "Fort Lauderdale"),
    "florida/gainesville":      ("Florida",        "Gainesville"),
    "florida/hialeah":          ("Florida",        "Hialeah"),
    "florida/hollywood":        ("Florida",        "Hollywood"),
    "florida/lakeland":         ("Florida",        "Lakeland"),
    "florida/miramar":          ("Florida",        "Miramar"),
    "florida/pembroke-pines":   ("Florida",        "Pembroke Pines"),
    "florida/port-st-lucie":    ("Florida",        "Port St. Lucie"),
    "florida/tallahassee":      ("Florida",        "Tallahassee"),
    "florida/west-palm-beach":  ("Florida",        "West Palm Beach"),
    "georgia/albany":           ("Georgia",        "Albany"),
    "georgia/athens":           ("Georgia",        "Athens"),
    "georgia/atlanta":          ("Georgia",        "Atlanta"),
    "georgia/augusta":          ("Georgia",        "Augusta"),
    "georgia/columbus":         ("Georgia",        "Columbus"),
    "georgia/macon":            ("Georgia",        "Macon"),
    "georgia/savannah":         ("Georgia",        "Savannah"),
    "illinois/bloomington":     ("Illinois",       "Bloomington"),
    "illinois/champaign":       ("Illinois",       "Champaign"),
    "illinois/elgin":           ("Illinois",       "Elgin"),
    "illinois/joliet":          ("Illinois",       "Joliet"),
    "illinois/peoria":          ("Illinois",       "Peoria"),
    "illinois/rockford":        ("Illinois",       "Rockford"),
    "illinois/springfield":     ("Illinois",       "Springfield"),
    "indiana/evansville":       ("Indiana",        "Evansville"),
    "indiana/fort-wayne":       ("Indiana",        "Fort Wayne"),
    "indiana/indianapolis":     ("Indiana",        "Indianapolis"),
    "indiana/south-bend":       ("Indiana",        "South Bend"),
    "kansas/olathe":            ("Kansas",         "Olathe"),
    "kansas/overland-park":     ("Kansas",         "Overland Park"),
    "kansas/topeka":            ("Kansas",         "Topeka"),
    "kansas/wichita":           ("Kansas",         "Wichita"),
    "kentucky/lexington":       ("Kentucky",       "Lexington"),
    "kentucky/louisville":      ("Kentucky",       "Louisville"),
    "louisiana/baton-rouge":    ("Louisiana",      "Baton Rouge"),
    "louisiana/new-orleans":    ("Louisiana",      "New Orleans"),
    "louisiana/shreveport":     ("Louisiana",      "Shreveport"),
    "michigan/ann-arbor":       ("Michigan",       "Ann Arbor"),
    "michigan/detroit":         ("Michigan",       "Detroit"),
    "michigan/flint":           ("Michigan",       "Flint"),
    "michigan/grand-rapids":    ("Michigan",       "Grand Rapids"),
    "michigan/lansing":         ("Michigan",       "Lansing"),
    "minnesota/duluth":         ("Minnesota",      "Duluth"),
    "minnesota/minneapolis":    ("Minnesota",      "Minneapolis"),
    "minnesota/rochester":      ("Minnesota",      "Rochester"),
    "minnesota/saint-paul":     ("Minnesota",      "Saint Paul"),
    "mississippi/gulfport":     ("Mississippi",    "Gulfport"),
    "mississippi/jackson":      ("Mississippi",    "Jackson"),
    "missouri/columbia":        ("Missouri",       "Columbia"),
    "missouri/independence":    ("Missouri",       "Independence"),
    "missouri/kansas-city":     ("Missouri",       "Kansas City"),
    "missouri/springfield":     ("Missouri",       "Springfield"),
    "missouri/st-louis":        ("Missouri",       "St. Louis"),
    "nebraska/lincoln":         ("Nebraska",       "Lincoln"),
    "nebraska/omaha":           ("Nebraska",       "Omaha"),
    "nevada/henderson":         ("Nevada",         "Henderson"),
    "nevada/las-vegas":         ("Nevada",         "Las Vegas"),
    "nevada/reno":              ("Nevada",         "Reno"),
    "new-jersey/jersey-city":   ("New Jersey",     "Jersey City"),
    "new-jersey/newark":        ("New Jersey",     "Newark"),
    "new-mexico/albuquerque":   ("New Mexico",     "Albuquerque"),
    "new-mexico/las-cruces":    ("New Mexico",     "Las Cruces"),
    "new-mexico/rio-rancho":    ("New Mexico",     "Rio Rancho"),
    "new-york/buffalo":         ("New York",       "Buffalo"),
    "new-york/rochester":       ("New York",       "Rochester"),
    "new-york/syracuse":        ("New York",       "Syracuse"),
    "new-york/yonkers":         ("New York",       "Yonkers"),
    "north-carolina/asheville": ("North Carolina", "Asheville"),
    "north-carolina/cary":      ("North Carolina", "Cary"),
    "north-carolina/charlotte": ("North Carolina", "Charlotte"),
    "north-carolina/durham":    ("North Carolina", "Durham"),
    "north-carolina/fayetteville":("North Carolina","Fayetteville"),
    "north-carolina/greensboro":("North Carolina", "Greensboro"),
    "north-carolina/raleigh":   ("North Carolina", "Raleigh"),
    "north-carolina/wilmington":("North Carolina", "Wilmington"),
    "north-carolina/winston-salem":("North Carolina","Winston-Salem"),
    "ohio/akron":               ("Ohio",           "Akron"),
    "ohio/cincinnati":          ("Ohio",           "Cincinnati"),
    "ohio/cleveland":           ("Ohio",           "Cleveland"),
    "ohio/columbus":            ("Ohio",           "Columbus"),
    "ohio/dayton":              ("Ohio",           "Dayton"),
    "ohio/toledo":              ("Ohio",           "Toledo"),
    "oklahoma/broken-arrow":    ("Oklahoma",       "Broken Arrow"),
    "oklahoma/norman":          ("Oklahoma",       "Norman"),
    "oklahoma/oklahoma-city":   ("Oklahoma",       "Oklahoma City"),
    "oklahoma/tulsa":           ("Oklahoma",       "Tulsa"),
    "oregon/bend":              ("Oregon",         "Bend"),
    "oregon/eugene":            ("Oregon",         "Eugene"),
    "oregon/gresham":           ("Oregon",         "Gresham"),
    "oregon/hillsboro":         ("Oregon",         "Hillsboro"),
    "oregon/portland":          ("Oregon",         "Portland"),
    "oregon/salem":             ("Oregon",         "Salem"),
    "pennsylvania/allentown":   ("Pennsylvania",   "Allentown"),
    "pennsylvania/erie":        ("Pennsylvania",   "Erie"),
    "pennsylvania/philadelphia":("Pennsylvania",   "Philadelphia"),
    "pennsylvania/pittsburgh":  ("Pennsylvania",   "Pittsburgh"),
    "south-carolina/charleston":("South Carolina", "Charleston"),
    "south-carolina/columbia":  ("South Carolina", "Columbia"),
    "south-carolina/greenville":("South Carolina", "Greenville"),
    "tennessee/chattanooga":    ("Tennessee",      "Chattanooga"),
    "tennessee/clarksville":    ("Tennessee",      "Clarksville"),
    "tennessee/knoxville":      ("Tennessee",      "Knoxville"),
    "tennessee/memphis":        ("Tennessee",      "Memphis"),
    "tennessee/murfreesboro":   ("Tennessee",      "Murfreesboro"),
    "tennessee/nashville":      ("Tennessee",      "Nashville"),
    "texas/abilene":            ("Texas",          "Abilene"),
    "texas/amarillo":           ("Texas",          "Amarillo"),
    "texas/arlington":          ("Texas",          "Arlington"),
    "texas/austin":             ("Texas",          "Austin"),
    "texas/beaumont":           ("Texas",          "Beaumont"),
    "texas/brownsville":        ("Texas",          "Brownsville"),
    "texas/carrollton":         ("Texas",          "Carrollton"),
    "texas/corpus-christi":     ("Texas",          "Corpus Christi"),
    "texas/dallas":             ("Texas",          "Dallas"),
    "texas/denton":             ("Texas",          "Denton"),
    "texas/el-paso":            ("Texas",          "El Paso"),
    "texas/fort-worth":         ("Texas",          "Fort Worth"),
    "texas/frisco":             ("Texas",          "Frisco"),
    "texas/garland":            ("Texas",          "Garland"),
    "texas/grand-prairie":      ("Texas",          "Grand Prairie"),
    "texas/houston":            ("Texas",          "Houston"),
    "texas/irving":             ("Texas",          "Irving"),
    "texas/killeen":            ("Texas",          "Killeen"),
    "texas/laredo":             ("Texas",          "Laredo"),
    "texas/lubbock":            ("Texas",          "Lubbock"),
    "texas/mcallen":            ("Texas",          "McAllen"),
    "texas/mckinney":           ("Texas",          "McKinney"),
    "texas/mesquite":           ("Texas",          "Mesquite"),
    "texas/midland":            ("Texas",          "Midland"),
    "texas/pasadena":           ("Texas",          "Pasadena"),
    "texas/plano":              ("Texas",          "Plano"),
    "texas/round-rock":         ("Texas",          "Round Rock"),
    "texas/san-antonio":        ("Texas",          "San Antonio"),
    "texas/waco":               ("Texas",          "Waco"),
    "utah/provo":               ("Utah",           "Provo"),
    "utah/salt-lake-city":      ("Utah",           "Salt Lake City"),
    "utah/st-george":           ("Utah",           "St. George"),
    "utah/west-jordan":         ("Utah",           "West Jordan"),
    "virginia/alexandria":      ("Virginia",       "Alexandria"),
    "virginia/chesapeake":      ("Virginia",       "Chesapeake"),
    "virginia/hampton":         ("Virginia",       "Hampton"),
    "virginia/newport-news":    ("Virginia",       "Newport News"),
    "virginia/norfolk":         ("Virginia",       "Norfolk"),
    "virginia/richmond":        ("Virginia",       "Richmond"),
    "virginia/virginia-beach":  ("Virginia",       "Virginia Beach"),
    "washington/bellevue":      ("Washington",     "Bellevue"),
    "washington/everett":       ("Washington",     "Everett"),
    "washington/kent":          ("Washington",     "Kent"),
    "washington/kirkland":      ("Washington",     "Kirkland"),
    "washington/renton":        ("Washington",     "Renton"),
    "washington/seattle":       ("Washington",     "Seattle"),
    "washington/spokane":       ("Washington",     "Spokane"),
    "washington/tacoma":        ("Washington",     "Tacoma"),
    "wisconsin/green-bay":      ("Wisconsin",      "Green Bay"),
    "wisconsin/kenosha":        ("Wisconsin",      "Kenosha"),
    "wisconsin/madison":        ("Wisconsin",      "Madison"),
    "wisconsin/milwaukee":      ("Wisconsin",      "Milwaukee"),
    "wisconsin/oshkosh":        ("Wisconsin",      "Oshkosh"),
    "wisconsin/racine":         ("Wisconsin",      "Racine"),
}

MUNICODE_BASE = "https://www.municode.com/meetings/{path}"


def scrape_municode(state: str, collected: list, max_packets: int) -> int:
    """Scrape Municode meetings for given state."""
    cities = {path: info for path, info in MUNICODE_CITIES.items()
              if info[0] == state}
    if not cities:
        return 0

    added = 0
    today = date.today()

    for path, (st, municipality) in cities.items():
        if len(collected) >= max_packets:
            break
        url = MUNICODE_BASE.format(path=path)
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "lxml")
        except Exception:
            continue

        for row in soup.select(".meeting-row, .meeting, tr, li, .list-group-item, article"):
            if len(collected) >= max_packets:
                break

            row_text = row.get_text(" ", strip=True)
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
                href = a["href"]
                label = a.get_text(strip=True).lower()
                if not href.startswith("http"):
                    href = f"https://www.municode.com{href}"
                if any(x in href.lower() or x in label
                       for x in [".pdf", "agenda", "packet", "download"]):
                    agenda_url = href
                    break
            if not agenda_url:
                continue

            name_el = row.select_one("h2,h3,.title,strong,b")
            body_name = name_el.get_text(strip=True) if name_el else body_type.replace("_", " ").title()

            dl = download_packet(agenda_url, st, municipality,
                                 body_type, date_str(meeting_date))
            if not dl or dl.get("failed"):
                continue

            collected.append({
                "state":        st,
                "municipality": municipality,
                "place_type":   "city",
                "body_name":    body_name,
                "body_type":    body_type,
                "meeting_date": date_str(meeting_date),
                "meeting_time": "",
                "location":     "",
                "source_url":   url,
                "platform":     "Municode",
                **dl,
            })
            added += 1

    return added
