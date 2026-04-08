"""
scrapers/civicplus.py — CivicPlus AgendaCenter scraper.

CONFIRMED WORKING: Thousands of US cities use CivicPlus at:
  https://{state}-{city}.civicplus.com/AgendaCenter

The AgendaCenter page is plain HTML with agenda links — no JS needed.
PDF links follow the pattern:
  /AgendaCenter/ViewFile/Agenda/{id}?fileID={fileID}
  or /AgendaCenter/ViewFile/Item/{id}?fileID={fileID}

Examples confirmed from search:
  nc-durham.civicplus.com/AgendaCenter
  ca-eastpaloalto.civicplus.com/AgendaCenter
  va-hopewell.civicplus.com/AgendaCenter
  ms-starkville.civicplus.com/AgendaCenter
"""

import requests, re
from datetime import date
from bs4 import BeautifulSoup
from utils import (classify_body, is_future_or_today, parse_date,
                   date_str, download_packet)
from constants import HEADERS, REQUEST_TIMEOUT

# CivicPlus cities: "{state_abbr}-{slug}" -> (state_name, display_name)
CIVICPLUS_CITIES = {
    # North Carolina
    "nc-raleigh":         ("North Carolina", "Raleigh"),
    "nc-greensboro":      ("North Carolina", "Greensboro"),
    "nc-nashcounty":      ("North Carolina", "Nash County"),
    "nc-cary":            ("North Carolina", "Cary"),
    "nc-wilmington":      ("North Carolina", "Wilmington"),
    "nc-highpoint":       ("North Carolina", "High Point"),
    "nc-asheville":       ("North Carolina", "Asheville"),
    "nc-chapelhill":      ("North Carolina", "Chapel Hill"),
    "nc-gastonia":        ("North Carolina", "Gastonia"),
    # Virginia
    "va-hopewell":        ("Virginia",       "Hopewell"),
    "va-portsmouth":      ("Virginia",       "Portsmouth"),
    "va-lynchburg":       ("Virginia",       "Lynchburg"),
    "va-harrisonburg":    ("Virginia",       "Harrisonburg"),
    "va-charlottesville": ("Virginia",       "Charlottesville"),
    "va-fredericksburg":  ("Virginia",       "Fredericksburg"),
    "va-suffolk":         ("Virginia",       "Suffolk"),
    # California
    "ca-eastpaloalto":    ("California",     "East Palo Alto"),
    "ca-alpinecounty":    ("California",     "Alpine County"),
    "ca-anaheim":         ("California",     "Anaheim"),
    "ca-westlakevillage": ("California",     "Westlake Village"),
    "ca-clovis":          ("California",     "Clovis"),
    "ca-visalia":         ("California",     "Visalia"),
    "ca-chico":           ("California",     "Chico"),
    "ca-redding":         ("California",     "Redding"),
    "ca-roseville":       ("California",     "Roseville"),
    "ca-richmond":        ("California",     "Richmond"),
    "ca-daly-city":       ("California",     "Daly City"),
    "ca-hayward":         ("California",     "Hayward"),
    "ca-vallejo":         ("California",     "Vallejo"),
    "ca-berkeley":        ("California",     "Berkeley"),
    "ca-napa":            ("California",     "Napa"),
    "ca-petaluma":        ("California",     "Petaluma"),
    "ca-hemet":           ("California",     "Hemet"),
    "ca-antioch":         ("California",     "Antioch"),
    "ca-vacaville":       ("California",     "Vacaville"),
    "ca-murrieta":        ("California",     "Murrieta"),
    "ca-temecula":        ("California",     "Temecula"),
    "ca-santarosa":       ("California",     "Santa Rosa"),
    "ca-santabarbara":    ("California",     "Santa Barbara"),
    "ca-ventura":         ("California",     "Ventura"),
    # Mississippi
    "ms-starkville":      ("Mississippi",    "Starkville"),
    "ms-gulfport":        ("Mississippi",    "Gulfport"),
    "ms-southaven":       ("Mississippi",    "Southaven"),
    "ms-hattiesburg":     ("Mississippi",    "Hattiesburg"),
    "ms-biloxi":          ("Mississippi",    "Biloxi"),
    "ms-jackson":         ("Mississippi",    "Jackson"),
    # Texas
    "tx-amarillo":        ("Texas",          "Amarillo"),
    "tx-waco":            ("Texas",          "Waco"),
    "tx-abilene":         ("Texas",          "Abilene"),
    "tx-beaumont":        ("Texas",          "Beaumont"),
    "tx-midland":         ("Texas",          "Midland"),
    "tx-odessa":          ("Texas",          "Odessa"),
    "tx-tyler":           ("Texas",          "Tyler"),
    "tx-wichitafalls":    ("Texas",          "Wichita Falls"),
    "tx-sanmarcos":       ("Texas",          "San Marcos"),
    "tx-roundrock":       ("Texas",          "Round Rock"),
    "tx-lewisville":      ("Texas",          "Lewisville"),
    "tx-richardson":      ("Texas",          "Richardson"),
    "tx-pearland":        ("Texas",          "Pearland"),
    "tx-league-city":     ("Texas",          "League City"),
    "tx-sugar-land":      ("Texas",          "Sugar Land"),
    # Florida
    "fl-palmbayflorida":  ("Florida",        "Palm Bay"),
    "fl-sarasota":        ("Florida",        "Sarasota"),
    "fl-bradenton":       ("Florida",        "Bradenton"),
    "fl-ocala":           ("Florida",        "Ocala"),
    "fl-pensacola":       ("Florida",        "Pensacola"),
    "fl-daytona-beach":   ("Florida",        "Daytona Beach"),
    "fl-kissimmee":       ("Florida",        "Kissimmee"),
    "fl-lakeland":        ("Florida",        "Lakeland"),
    "fl-clearwater":      ("Florida",        "Clearwater"),
    "fl-fortmyers":       ("Florida",        "Fort Myers"),
    "fl-gainesville":     ("Florida",        "Gainesville"),
    # Georgia
    "ga-sandysprings":    ("Georgia",        "Sandy Springs"),
    "ga-roswell":         ("Georgia",        "Roswell"),
    "ga-albany":          ("Georgia",        "Albany"),
    "ga-warnerrobins":    ("Georgia",        "Warner Robins"),
    "ga-alpharetta":      ("Georgia",        "Alpharetta"),
    "ga-marietta":        ("Georgia",        "Marietta"),
    "ga-valdosta":        ("Georgia",        "Valdosta"),
    # Ohio
    "oh-parma":           ("Ohio",           "Parma"),
    "oh-lorain":          ("Ohio",           "Lorain"),
    "oh-hamilton":        ("Ohio",           "Hamilton"),
    "oh-kettering":       ("Ohio",           "Kettering"),
    "oh-springfield":     ("Ohio",           "Springfield"),
    "oh-newark":          ("Ohio",           "Newark"),
    "oh-mentor":          ("Ohio",           "Mentor"),
    "oh-euclid":          ("Ohio",           "Euclid"),
    # Michigan
    "mi-westland":        ("Michigan",       "Westland"),
    "mi-troy":            ("Michigan",       "Troy"),
    "mi-farmington-hills":("Michigan",       "Farmington Hills"),
    "mi-wyoming":         ("Michigan",       "Wyoming"),
    "mi-southfield":      ("Michigan",       "Southfield"),
    "mi-pontiac":         ("Michigan",       "Pontiac"),
    # South Carolina
    "sc-greenville":      ("South Carolina", "Greenville"),
    "sc-columbia":        ("South Carolina", "Columbia"),
    "sc-charleston":      ("South Carolina", "Charleston"),
    "sc-rockhill":        ("South Carolina", "Rock Hill"),
    "sc-summerville":     ("South Carolina", "Summerville"),
    "sc-spartanburg":     ("South Carolina", "Spartanburg"),
    # Indiana
    "in-muncie":          ("Indiana",        "Muncie"),
    "in-terre-haute":     ("Indiana",        "Terre Haute"),
    "in-anderson":        ("Indiana",        "Anderson"),
    "in-bloomington":     ("Indiana",        "Bloomington"),
    "in-lafayette":       ("Indiana",        "Lafayette"),
    # Missouri
    "mo-joplin":          ("Missouri",       "Joplin"),
    "mo-stcharles":       ("Missouri",       "St. Charles"),
    "mo-bluesprings":     ("Missouri",       "Blue Springs"),
    "mo-florissant":      ("Missouri",       "Florissant"),
    # Kansas
    "ks-manhattan":       ("Kansas",         "Manhattan"),
    "ks-shawnee":         ("Kansas",         "Shawnee"),
    # Vermont
    "vt-southburlington": ("Vermont",        "South Burlington"),
    "vt-burlington":      ("Vermont",        "Burlington"),
    "vt-rutland":         ("Vermont",        "Rutland"),
    # New Hampshire
    "nh-manchester":      ("New Hampshire",  "Manchester"),
    "nh-nashua":          ("New Hampshire",  "Nashua"),
    "nh-concord":         ("New Hampshire",  "Concord"),
    # Rhode Island
    "ri-providence":      ("Rhode Island",   "Providence"),
    "ri-cranston":        ("Rhode Island",   "Cranston"),
    "ri-pawtucket":       ("Rhode Island",   "Pawtucket"),
    # Maine
    "me-portland":        ("Maine",          "Portland"),
    "me-lewiston":        ("Maine",          "Lewiston"),
    "me-bangor":          ("Maine",          "Bangor"),
    # Delaware
    "de-dover":           ("Delaware",       "Dover"),
    "de-wilmington":      ("Delaware",       "Wilmington"),
    # Montana
    "mt-billings":        ("Montana",        "Billings"),
    "mt-missoula":        ("Montana",        "Missoula"),
    "mt-greatfalls":      ("Montana",        "Great Falls"),
    "mt-bozeman":         ("Montana",        "Bozeman"),
    # Wyoming
    "wy-cheyenne":        ("Wyoming",        "Cheyenne"),
    "wy-casper":          ("Wyoming",        "Casper"),
    # Idaho
    "id-boise":           ("Idaho",          "Boise"),
    "id-nampa":           ("Idaho",          "Nampa"),
    "id-meridian":        ("Idaho",          "Meridian"),
    "id-idahofalls":      ("Idaho",          "Idaho Falls"),
    "id-pocatello":       ("Idaho",          "Pocatello"),
    # Utah
    "ut-sandy":           ("Utah",           "Sandy"),
    "ut-ogden":           ("Utah",           "Ogden"),
    "ut-stgeorge":        ("Utah",           "St. George"),
    "ut-layton":          ("Utah",           "Layton"),
    # Nevada
    "nv-sparks":          ("Nevada",         "Sparks"),
    "nv-carsoncity":      ("Nevada",         "Carson City"),
    # Oregon
    "or-bend":            ("Oregon",         "Bend"),
    "or-medford":         ("Oregon",         "Medford"),
    "or-corvallis":       ("Oregon",         "Corvallis"),
    "or-albany":          ("Oregon",         "Albany"),
    "or-hillsboro":       ("Oregon",         "Hillsboro"),
    "or-beaverton":       ("Oregon",         "Beaverton"),
    "or-gresham":         ("Oregon",         "Gresham"),
    # Washington
    "wa-bellingham":      ("Washington",     "Bellingham"),
    "wa-yakima":          ("Washington",     "Yakima"),
    "wa-kennewick":       ("Washington",     "Kennewick"),
    "wa-olympia":         ("Washington",     "Olympia"),
    "wa-auburn":          ("Washington",     "Auburn"),
    "wa-marysville":      ("Washington",     "Marysville"),
    # Minnesota
    "mn-rochester":       ("Minnesota",      "Rochester"),
    "mn-duluth":          ("Minnesota",      "Duluth"),
    "mn-bloomington":     ("Minnesota",      "Bloomington"),
    "mn-brooklyn-park":   ("Minnesota",      "Brooklyn Park"),
    "mn-plymouth":        ("Minnesota",      "Plymouth"),
    "mn-stcloud":         ("Minnesota",      "St. Cloud"),
    "mn-eagan":           ("Minnesota",      "Eagan"),
    # Wisconsin
    "wi-green-bay":       ("Wisconsin",      "Green Bay"),
    "wi-kenosha":         ("Wisconsin",      "Kenosha"),
    "wi-racine":          ("Wisconsin",      "Racine"),
    "wi-appleton":        ("Wisconsin",      "Appleton"),
    "wi-oshkosh":         ("Wisconsin",      "Oshkosh"),
    "wi-waukesha":        ("Wisconsin",      "Waukesha"),
    "wi-eau-claire":      ("Wisconsin",      "Eau Claire"),
    "wi-janesville":      ("Wisconsin",      "Janesville"),
    # Iowa
    "ia-cedar-rapids":    ("Iowa",           "Cedar Rapids"),
    "ia-davenport":       ("Iowa",           "Davenport"),
    "ia-sioux-city":      ("Iowa",           "Sioux City"),
    "ia-iowa-city":       ("Iowa",           "Iowa City"),
    "ia-waterloo":        ("Iowa",           "Waterloo"),
    "ia-ames":            ("Iowa",           "Ames"),
    "ia-ankeny":          ("Iowa",           "Ankeny"),
    # Nebraska
    "ne-lincoln":         ("Nebraska",       "Lincoln"),
    "ne-bellevue":        ("Nebraska",       "Bellevue"),
    "ne-grandisland":     ("Nebraska",       "Grand Island"),
    # South Dakota
    "sd-siouxfalls":      ("South Dakota",   "Sioux Falls"),
    "sd-rapidcity":       ("South Dakota",   "Rapid City"),
    # North Dakota
    "nd-fargo":           ("North Dakota",   "Fargo"),
    "nd-bismarck":        ("North Dakota",   "Bismarck"),
    # Arkansas
    "ar-fortsmith":       ("Arkansas",       "Fort Smith"),
    "ar-fayetteville":    ("Arkansas",       "Fayetteville"),
    "ar-springdale":      ("Arkansas",       "Springdale"),
    "ar-jonesboro":       ("Arkansas",       "Jonesboro"),
    # Louisiana
    "la-lafayette":       ("Louisiana",      "Lafayette"),
    "la-lakecharles":     ("Louisiana",      "Lake Charles"),
    "la-kenner":          ("Louisiana",      "Kenner"),
    "la-bossiercity":     ("Louisiana",      "Bossier City"),
    # Alabama
    "al-tuscaloosa":      ("Alabama",        "Tuscaloosa"),
    "al-hoover":          ("Alabama",        "Hoover"),
    "al-dothan":          ("Alabama",        "Dothan"),
    "al-auburn":          ("Alabama",        "Auburn"),
    # Maryland
    "md-bowie":           ("Maryland",       "Bowie"),
    "md-hagerstown":      ("Maryland",       "Hagerstown"),
    "md-annapolis":       ("Maryland",       "Annapolis"),
    # Connecticut
    "ct-waterbury":       ("Connecticut",    "Waterbury"),
    "ct-danbury":         ("Connecticut",    "Danbury"),
    "ct-new-britain":     ("Connecticut",    "New Britain"),
    "ct-west-haven":      ("Connecticut",    "West Haven"),
    "ct-meriden":         ("Connecticut",    "Meriden"),
    # New Jersey
    "nj-trenton":         ("New Jersey",     "Trenton"),
    "nj-camden":          ("New Jersey",     "Camden"),
    "nj-elizabeth":       ("New Jersey",     "Elizabeth"),
    # West Virginia
    "wv-huntington":      ("West Virginia",  "Huntington"),
    "wv-morgantown":      ("West Virginia",  "Morgantown"),
    "wv-parkersburg":     ("West Virginia",  "Parkersburg"),
    # Hawaii
    "hi-hilo":            ("Hawaii",         "Hilo"),
    # Alaska
    "ak-fairbanks":       ("Alaska",         "Fairbanks"),
    "ak-juneau":          ("Alaska",         "Juneau"),
    # New Mexico
    "nm-las-cruces":      ("New Mexico",     "Las Cruces"),
    "nm-rio-rancho":      ("New Mexico",     "Rio Rancho"),
    "nm-santa-fe":        ("New Mexico",     "Santa Fe"),
    # Arizona
    "az-prescott":        ("Arizona",        "Prescott"),
    "az-flagstaff":       ("Arizona",        "Flagstaff"),
    "az-yuma":            ("Arizona",        "Yuma"),
    "az-goodyear":        ("Arizona",        "Goodyear"),
    "az-surprise":        ("Arizona",        "Surprise"),
    "az-avondale":        ("Arizona",        "Avondale"),
    # Tennessee
    "tn-murfreesboro":    ("Tennessee",      "Murfreesboro"),
    "tn-franklin":        ("Tennessee",      "Franklin"),
    "tn-jackson":         ("Tennessee",      "Jackson"),
    "tn-johnson-city":    ("Tennessee",      "Johnson City"),
    "tn-kingsport":       ("Tennessee",      "Kingsport"),
    # Oklahoma
    "ok-norman":          ("Oklahoma",       "Norman"),
    "ok-broken-arrow":    ("Oklahoma",       "Broken Arrow"),
    "ok-lawton":          ("Oklahoma",       "Lawton"),
    "ok-edmond":          ("Oklahoma",       "Edmond"),
    "ok-stillwater":      ("Oklahoma",       "Stillwater"),
    # Colorado
    "co-fortcollins":     ("Colorado",       "Fort Collins"),
    "co-pueblo":          ("Colorado",       "Pueblo"),
    "co-greeley":         ("Colorado",       "Greeley"),
    "co-longmont":        ("Colorado",       "Longmont"),
    "co-loveland":        ("Colorado",       "Loveland"),
    "co-broomfield":      ("Colorado",       "Broomfield"),
    "co-castle-rock":     ("Colorado",       "Castle Rock"),
}

CIVICPLUS_BASE = "https://{slug}.civicplus.com/AgendaCenter"


def scrape_civicplus(state: str, collected: list, max_packets: int) -> int:
    """Scrape CivicPlus AgendaCenter sites for a given state."""
    cities = {slug: info for slug, info in CIVICPLUS_CITIES.items()
              if info[0] == state}
    if not cities:
        return 0

    added = 0
    today = date.today()

    for slug, (st, display_name) in cities.items():
        if len(collected) >= max_packets:
            break

        url = CIVICPLUS_BASE.format(slug=slug)
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "lxml")
        except Exception:
            continue

        # CivicPlus AgendaCenter renders a list of meetings
        # Each row has: committee name, meeting date, agenda link
        for row in soup.select("li.tContent, .catAgendaRow, tr, li"):
            if len(collected) >= max_packets:
                break

            row_text  = row.get_text(" ", strip=True)
            body_type = classify_body(row_text)
            if not body_type:
                continue

            # Find a date in the row
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

            # Find agenda PDF link
            agenda_url = None
            for a in row.select("a[href]"):
                href  = a["href"]
                label = a.get_text(strip=True).lower()
                if not href.startswith("http"):
                    href = f"https://{slug}.civicplus.com{href}"
                if any(x in href.lower() or x in label
                       for x in ["agenda", "packet", "viewfile", ".pdf"]):
                    agenda_url = href
                    break
            if not agenda_url:
                continue

            # Get body name from the row
            name_el   = row.select_one("h2, h3, .title, strong, b")
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
                "platform":     "CivicPlus",
                **dl,
            })
            added += 1

    return added
