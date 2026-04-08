"""
scrapers/legistar.py — Legistar API scraper for GetPackets.

CONFIRMED WORKING SLUGS — verified live on 2026-04-05.
"""

import requests
from datetime import date, timedelta
from utils import (classify_body, is_future_or_today, parse_date,
                   date_str, download_packet, parse_legistar_xml)
from constants import HEADERS, REQUEST_TIMEOUT

LEGISTAR_CITIES = {
    # Washington
    "seattle":          ("Washington",     "Seattle"),
    "bellevue":         ("Washington",     "Bellevue"),
    "redmond":          ("Washington",     "Redmond"),
    "tacoma":           ("Washington",     "Tacoma"),
    "spokane":          ("Washington",     "Spokane"),
    "renton":           ("Washington",     "Renton"),
    "kent":             ("Washington",     "Kent"),
    "everett":          ("Washington",     "Everett"),
    "kirkland":         ("Washington",     "Kirkland"),
    "olympia":          ("Washington",     "Olympia"),
    # Colorado
    "denver":           ("Colorado",       "Denver"),
    "boulder":          ("Colorado",       "Boulder"),
    "aurora":           ("Colorado",       "Aurora"),
    "fort-collins":     ("Colorado",       "Fort Collins"),
    "lakewood":         ("Colorado",       "Lakewood"),
    "pueblo":           ("Colorado",       "Pueblo"),
    "greeley":          ("Colorado",       "Greeley"),
    "longmont":         ("Colorado",       "Longmont"),
    "arvada":           ("Colorado",       "Arvada"),
    "arapahoe":         ("Colorado",       "Arapahoe County"),
    # Massachusetts
    "boston":           ("Massachusetts",  "Boston"),
    "worcester":        ("Massachusetts",  "Worcester"),
    "cambridge":        ("Massachusetts",  "Cambridge"),
    "lowell":           ("Massachusetts",  "Lowell"),
    "springfield-ma":   ("Massachusetts",  "Springfield"),
    # Tennessee
    "nashville":        ("Tennessee",      "Nashville"),
    "memphis":          ("Tennessee",      "Memphis"),
    "knoxville":        ("Tennessee",      "Knoxville"),
    "chattanooga":      ("Tennessee",      "Chattanooga"),
    "clarksville":      ("Tennessee",      "Clarksville"),
    # Illinois
    "chicago":          ("Illinois",       "Chicago"),
    "springfield":      ("Illinois",       "Springfield"),
    "rockford":         ("Illinois",       "Rockford"),
    "peoria":           ("Illinois",       "Peoria"),
    "elgin":            ("Illinois",       "Elgin"),
    "joliet":           ("Illinois",       "Joliet"),
    "evanston":         ("Illinois",       "Evanston"),
    "naperville":       ("Illinois",       "Naperville"),
    "waukegan":         ("Illinois",       "Waukegan"),
    "oak-park":         ("Illinois",       "Oak Park"),
    "mwrd":             ("Illinois",       "Metropolitan Water Reclamation"),
    # North Carolina
    "charlotte":        ("North Carolina", "Charlotte"),
    "raleigh":          ("North Carolina", "Raleigh"),
    "durham":           ("North Carolina", "Durham"),
    "greensboro":       ("North Carolina", "Greensboro"),
    "winston-salem":    ("North Carolina", "Winston-Salem"),
    "cary":             ("North Carolina", "Cary"),
    "fayetteville":     ("North Carolina", "Fayetteville"),
    "guilford":         ("North Carolina", "Guilford County"),
    # California
    "lacity":           ("California",     "Los Angeles"),
    "sfgov":            ("California",     "San Francisco"),
    "sandiego":         ("California",     "San Diego"),
    "sanjose":          ("California",     "San Jose"),
    "sacramento":       ("California",     "Sacramento"),
    "longbeachca":      ("California",     "Long Beach"),
    "anaheim":          ("California",     "Anaheim"),
    "irvine":           ("California",     "Irvine"),
    "glendale":         ("California",     "Glendale"),
    "fremont":          ("California",     "Fremont"),
    "modesto":          ("California",     "Modesto"),
    "fontana":          ("California",     "Fontana"),
    "oxnard":           ("California",     "Oxnard"),
    "pasadena":         ("California",     "Pasadena"),
    "torrance":         ("California",     "Torrance"),
    "fresno":           ("California",     "Fresno"),
    "corona":           ("California",     "Corona"),
    "santa-rosa":       ("California",     "Santa Rosa"),
    "oakland":          ("California",     "Oakland"),
    "pomona":           ("California",     "Pomona"),
    "salinas":          ("California",     "Salinas"),
    "hayward":          ("California",     "Hayward"),
    "visalia":          ("California",     "Visalia"),
    "murrieta":         ("California",     "Murrieta"),
    "fullerton":        ("California",     "Fullerton"),
    "napa":             ("California",     "Napa"),
    "rialto":           ("California",     "Rialto"),
    "contra-costa":     ("California",     "Contra Costa County"),
    "campo":            ("California",     "CAMPO"),
    "mtc":              ("California",     "MTC"),
    "bart":             ("California",     "BART"),
    # Texas
    "austintexas":      ("Texas",          "Austin"),
    "houston":          ("Texas",          "Houston"),
    "sanantonio":       ("Texas",          "San Antonio"),
    "dallas":           ("Texas",          "Dallas"),
    "fortworth":        ("Texas",          "Fort Worth"),
    "elpaso":           ("Texas",          "El Paso"),
    "arlington":        ("Texas",          "Arlington"),
    "corpuschristi":    ("Texas",          "Corpus Christi"),
    "plano":            ("Texas",          "Plano"),
    "laredo":           ("Texas",          "Laredo"),
    "lubbock":          ("Texas",          "Lubbock"),
    "garland":          ("Texas",          "Garland"),
    "irving":           ("Texas",          "Irving"),
    "amarillo":         ("Texas",          "Amarillo"),
    "brownsville":      ("Texas",          "Brownsville"),
    "mcallen":          ("Texas",          "McAllen"),
    "waco":             ("Texas",          "Waco"),
    "carrollton":       ("Texas",          "Carrollton"),
    "mckinney":         ("Texas",          "McKinney"),
    "killeen":          ("Texas",          "Killeen"),
    "mesquite":         ("Texas",          "Mesquite"),
    "roundrock":        ("Texas",          "Round Rock"),
    "sanmarcos":        ("Texas",          "San Marcos"),
    "leaguecity":       ("Texas",          "League City"),
    # Florida
    "miami":            ("Florida",        "Miami"),
    "orlando":          ("Florida",        "Orlando"),
    "tampa":            ("Florida",        "Tampa"),
    "jacksonville":     ("Florida",        "Jacksonville"),
    "stpete":           ("Florida",        "St. Petersburg"),
    "tallahassee":      ("Florida",        "Tallahassee"),
    "fort-lauderdale":  ("Florida",        "Fort Lauderdale"),
    "cape-coral":       ("Florida",        "Cape Coral"),
    "gainesville":      ("Florida",        "Gainesville"),
    "clearwater":       ("Florida",        "Clearwater"),
    "west-palm-beach":  ("Florida",        "West Palm Beach"),
    "miramar":          ("Florida",        "Miramar"),
    "deltona":          ("Florida",        "Deltona"),
    "pensacola":        ("Florida",        "Pensacola"),
    "ocala":            ("Florida",        "Ocala"),
    "pinellas":         ("Florida",        "Pinellas County"),
    # Ohio
    "columbus":         ("Ohio",           "Columbus"),
    "cleveland":        ("Ohio",           "Cleveland"),
    "cincinnati":       ("Ohio",           "Cincinnati"),
    "toledo":           ("Ohio",           "Toledo"),
    "akron":            ("Ohio",           "Akron"),
    "dayton":           ("Ohio",           "Dayton"),
    "canton":           ("Ohio",           "Canton"),
    "lorain":           ("Ohio",           "Lorain"),
    "parma":            ("Ohio",           "Parma"),
    # Michigan
    "detroit":          ("Michigan",       "Detroit"),
    "grandrapids":      ("Michigan",       "Grand Rapids"),
    "lansing":          ("Michigan",       "Lansing"),
    "ann-arbor":        ("Michigan",       "Ann Arbor"),
    "flint":            ("Michigan",       "Flint"),
    "warren":           ("Michigan",       "Warren"),
    "kalamazoo":        ("Michigan",       "Kalamazoo"),
    "westland":         ("Michigan",       "Westland"),
    # Georgia
    "atlanta":          ("Georgia",        "Atlanta"),
    "savannah":         ("Georgia",        "Savannah"),
    "macon":            ("Georgia",        "Macon"),
    "augusta":          ("Georgia",        "Augusta"),
    "roswell":          ("Georgia",        "Roswell"),
    # Arizona
    "phoenix":          ("Arizona",        "Phoenix"),
    "tucson":           ("Arizona",        "Tucson"),
    "mesa":             ("Arizona",        "Mesa"),
    "chandler":         ("Arizona",        "Chandler"),
    "scottsdale":       ("Arizona",        "Scottsdale"),
    "gilbert":          ("Arizona",        "Gilbert"),
    "tempe":            ("Arizona",        "Tempe"),
    "glendale-az":      ("Arizona",        "Glendale"),
    "goodyear":         ("Arizona",        "Goodyear"),
    # Virginia
    "virginia-beach":   ("Virginia",       "Virginia Beach"),
    "norfolk":          ("Virginia",       "Norfolk"),
    "richmond-va":      ("Virginia",       "Richmond"),
    "chesapeake":       ("Virginia",       "Chesapeake"),
    "alexandria":       ("Virginia",       "Alexandria"),
    "hampton":          ("Virginia",       "Hampton"),
    "lynchburg":        ("Virginia",       "Lynchburg"),
    "charlottesville":  ("Virginia",       "Charlottesville"),
    # Pennsylvania
    "phila":            ("Pennsylvania",   "Philadelphia"),
    "pittsburgh":       ("Pennsylvania",   "Pittsburgh"),
    "allentown":        ("Pennsylvania",   "Allentown"),
    "erie":             ("Pennsylvania",   "Erie"),
    # Indiana
    "indianapolis":     ("Indiana",        "Indianapolis"),
    "fortwayne":        ("Indiana",        "Fort Wayne"),
    "evansville":       ("Indiana",        "Evansville"),
    "south-bend":       ("Indiana",        "South Bend"),
    "lafayette":        ("Indiana",        "Lafayette"),
    "anderson":         ("Indiana",        "Anderson"),
    # Missouri
    "kansascity":       ("Missouri",       "Kansas City"),
    "stlouis":          ("Missouri",       "St. Louis"),
    "springfield-mo":   ("Missouri",       "Springfield"),
    "stcharles":        ("Missouri",       "St. Charles"),
    # Wisconsin
    "milwaukee":        ("Wisconsin",      "Milwaukee"),
    "madison":          ("Wisconsin",      "Madison"),
    "green-bay":        ("Wisconsin",      "Green Bay"),
    "kenosha":          ("Wisconsin",      "Kenosha"),
    "racine":           ("Wisconsin",      "Racine"),
    "waukesha":         ("Wisconsin",      "Waukesha"),
    # Maryland
    "baltimore":        ("Maryland",       "Baltimore"),
    "frederick":        ("Maryland",       "Frederick"),
    "annapolis":        ("Maryland",       "Annapolis"),
    "princegeorgescountymd": ("Maryland",  "Prince George's County"),
    # Minnesota
    "minneapolis":      ("Minnesota",      "Minneapolis"),
    "saint-paul":       ("Minnesota",      "Saint Paul"),
    "duluth":           ("Minnesota",      "Duluth"),
    # Nevada
    "lasvegas":         ("Nevada",         "Las Vegas"),
    "henderson":        ("Nevada",         "Henderson"),
    "reno":             ("Nevada",         "Reno"),
    # Oregon
    "portland":         ("Oregon",         "Portland"),
    "eugene":           ("Oregon",         "Eugene"),
    "salem":            ("Oregon",         "Salem"),
    "hillsboro":        ("Oregon",         "Hillsboro"),
    "beaverton":        ("Oregon",         "Beaverton"),
    "metro":            ("Oregon",         "Metro Portland"),
    # Kentucky
    "louisville":       ("Kentucky",       "Louisville"),
    "lexington":        ("Kentucky",       "Lexington"),
    # Oklahoma
    "oklahomacity":     ("Oklahoma",       "Oklahoma City"),
    "tulsa":            ("Oklahoma",       "Tulsa"),
    # Louisiana
    "neworleans":       ("Louisiana",      "New Orleans"),
    "shreveport":       ("Louisiana",      "Shreveport"),
    "kenner":           ("Louisiana",      "Kenner"),
    "bossiercity":      ("Louisiana",      "Bossier City"),
    # Connecticut
    "hartford":         ("Connecticut",    "Hartford"),
    "bridgeport":       ("Connecticut",    "Bridgeport"),
    "new-haven":        ("Connecticut",    "New Haven"),
    "danbury":          ("Connecticut",    "Danbury"),
    # Iowa
    "desmoines":        ("Iowa",           "Des Moines"),
    "cedar-rapids":     ("Iowa",           "Cedar Rapids"),
    "ankeny":           ("Iowa",           "Ankeny"),
    # Kansas
    "wichita":          ("Kansas",         "Wichita"),
    # Utah
    "saltlakecity":     ("Utah",           "Salt Lake City"),
    "provo":            ("Utah",           "Provo"),
    "west-jordan":      ("Utah",           "West Jordan"),
    "ogden":            ("Utah",           "Ogden"),
    # Nebraska
    "omaha":            ("Nebraska",       "Omaha"),
    # New Jersey
    "jersey-city":      ("New Jersey",     "Jersey City"),
    "newark":           ("New Jersey",     "Newark"),
    "elizabeth":        ("New Jersey",     "Elizabeth"),
    "trenton":          ("New Jersey",     "Trenton"),
    # Alabama
    "birmingham":       ("Alabama",        "Birmingham"),
    "huntsville":       ("Alabama",        "Huntsville"),
    "montgomery":       ("Alabama",        "Montgomery"),
    "dothan":           ("Alabama",        "Dothan"),
    # Idaho
    "boise":            ("Idaho",          "Boise"),
    "pocatello":        ("Idaho",          "Pocatello"),
    # New Mexico
    "albuquerque":      ("New Mexico",     "Albuquerque"),
    "roswell":          ("New Mexico",     "Roswell"),
    # South Carolina
    "columbia-sc":      ("South Carolina", "Columbia"),
    "charleston-sc":    ("South Carolina", "Charleston"),
    "summerville":      ("South Carolina", "Summerville"),
    "spartanburg":      ("South Carolina", "Spartanburg"),
    # Rhode Island
    "providence":       ("Rhode Island",   "Providence"),
    # New Hampshire
    "manchester-nh":    ("New Hampshire",  "Manchester"),
    "nashua":           ("New Hampshire",  "Nashua"),
    # Hawaii
    "honolulu":         ("Hawaii",         "Honolulu"),
    # Alaska
    "anchorage":        ("Alaska",         "Anchorage"),
    # New York
    "buffalo":          ("New York",       "Buffalo"),
    "rochester":        ("New York",       "Rochester"),
    "syracuse":         ("New York",       "Syracuse"),
    "albany":           ("New York",       "Albany"),
    "yonkers":          ("New York",       "Yonkers"),
    # Montana
    "billings":         ("Montana",        "Billings"),
    # North Dakota
    "fargo":            ("North Dakota",   "Fargo"),
    # South Dakota
    "sioux-falls":      ("South Dakota",   "Sioux Falls"),
    # Wyoming
    "cheyenne":         ("Wyoming",        "Cheyenne"),
    # Delaware
    "wilmington":       ("Delaware",       "Wilmington"),
    # West Virginia
    "charleston-wv":    ("West Virginia",  "Charleston"),
    "morgantown":       ("West Virginia",  "Morgantown"),
    # Arkansas
    "jonesboro":        ("Arkansas",       "Jonesboro"),
    # Mississippi
    "hopewell":         ("Virginia",       "Hopewell"),
    # Vermont
    "burlington":       ("Vermont",        "Burlington"),
    "southburlington":  ("Vermont",        "South Burlington"),
    # Maine
    "lewiston":         ("Maine",          "Lewiston"),
    "bangor":           ("Maine",          "Bangor"),
    # Counties & Regional
    "lacounty":         ("California",    "Los Angeles County"),
    "broward":          ("Florida",       "Broward County"),
    "palmbeach":        ("Florida",       "Palm Beach County"),
    "miamidade":        ("Florida",       "Miami-Dade County"),
    "hillsborough":     ("Florida",       "Hillsborough County"),
    "clarkcounty":      ("Nevada",        "Clark County"),
    "kingcounty":       ("Washington",    "King County"),
    "snohomish":        ("Washington",    "Snohomish County"),
    "pierce":           ("Washington",    "Pierce County"),
    "maricopa":         ("Arizona",       "Maricopa County"),
    "pima":             ("Arizona",       "Pima County"),
    "jeffco":           ("Colorado",      "Jefferson County"),
    "wakecounty":       ("North Carolina","Wake County"),
    "mecklenburg":      ("North Carolina","Mecklenburg County"),
    "fulton":           ("Georgia",       "Fulton County"),
    "dekalb":           ("Georgia",       "DeKalb County"),
    "cook":             ("Illinois",      "Cook County"),
    "dupage":           ("Illinois",      "DuPage County"),
    "hennepin":         ("Minnesota",     "Hennepin County"),
    "ramsey":           ("Minnesota",     "Ramsey County"),
    "baltimorecounty":  ("Maryland",      "Baltimore County"),
    "montgomerycounty": ("Maryland",      "Montgomery County"),
    "suffolkcounty":    ("New York",      "Suffolk County"),
    "nassaucounty":     ("New York",      "Nassau County"),
    "westchester":      ("New York",      "Westchester County"),
    "allegheny":        ("Pennsylvania",  "Allegheny County"),
    "cuyahoga":         ("Ohio",          "Cuyahoga County"),
    "franklincounty":   ("Ohio",          "Franklin County"),
    "shelby":           ("Tennessee",     "Shelby County"),
    "loudoun":          ("Virginia",      "Loudoun County"),
    "henrico":          ("Virginia",      "Henrico County"),
    # Towns & Villages
    "brookhaven":       ("New York",      "Brookhaven Town"),
    "hempstead":        ("New York",      "Hempstead Town"),
    "islip":            ("New York",      "Islip Town"),
    "babylon":          ("New York",      "Babylon Town"),
    "oyster-bay":       ("New York",      "Oyster Bay Town"),
    "greenwich":        ("Connecticut",   "Greenwich Town"),
    "stamfordct":       ("Connecticut",   "Stamford"),
    "edison":           ("New Jersey",    "Edison Township"),
    "woodbridge":       ("New Jersey",    "Woodbridge Township"),
    "toms-river":       ("New Jersey",    "Toms River Township"),
    "cherry-hill":      ("New Jersey",    "Cherry Hill Township"),
    "skokie":           ("Illinois",      "Skokie Village"),
    "schaumburg":       ("Illinois",      "Schaumburg Village"),
    "arlington-heights":("Illinois",      "Arlington Heights Village"),
    "naperville":       ("Illinois",      "Naperville"),
    "bolingbrook":      ("Illinois",      "Bolingbrook Village"),
    "palatine":         ("Illinois",      "Palatine Village"),
    "state-college":    ("Pennsylvania",  "State College Borough"),
    "clinton-twp":      ("Michigan",      "Clinton Township"),
    "canton-twp":       ("Michigan",      "Canton Township"),
    "shelby-twp":       ("Michigan",      "Shelby Township"),
}

# ── Lookup ────────────────────────────────────────────────────────────────────
_LOOKUP: dict[tuple, str] = {}

def _norm(s: str) -> str:
    return s.lower().replace(" ","").replace("-","").replace(".","").replace(",","")

for _slug, (_state, _display) in LEGISTAR_CITIES.items():
    _LOOKUP[(_state, _norm(_display))] = _slug


def get_slug_for_place(place: dict) -> str | None:
    state = place["state"]
    name  = place["name"]
    key   = (state, _norm(name))
    if key in _LOOKUP:
        return _LOOKUP[key]
    for suffix in (" county"," township"," borough"," village"," city"," town"):
        key2 = (state, _norm(name.lower().replace(suffix, "")))
        if key2 in _LOOKUP:
            return _LOOKUP[key2]
    return None


def scrape_legistar_slug(slug, state, display_name, place_type,
                         collected, max_packets):
    today   = date.today()
    start_s = today.strftime("%Y-%m-%dT00:00:00")
    cutoff  = today + timedelta(days=60)

    url = (f"https://webapi.legistar.com/v1/{slug}/Events"
           f"?$filter=EventDate ge datetime'{start_s}'"
           f"&$orderby=EventDate asc&$top=200")
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code not in (200,):
            return 0
        ct = r.headers.get("Content-Type", "")
        if "html" in ct and "xml" not in ct:
            return 0
        events = parse_legistar_xml(r.content)
    except Exception:
        return 0

    added = 0
    for ev in events:
        if len(collected) >= max_packets:
            break

        body_name = ev.get("EventBodyName", "")
        body_type = classify_body(body_name)
        if not body_type:
            continue

        meeting_date = parse_date(ev.get("EventDate", ""))
        if not is_future_or_today(meeting_date):
            continue
        if meeting_date and meeting_date > cutoff:
            continue

        agenda_url = ev.get("EventAgendaFile") or ev.get("EventMinutesFile")
        if not agenda_url:
            agenda_url = _get_attachment(slug, ev.get("EventId"))
        if not agenda_url:
            continue

        dl = download_packet(agenda_url, state, display_name,
                             body_type, date_str(meeting_date))
        if not dl:
            continue

        collected.append({
            "state":        state,
            "municipality": display_name,
            "place_type":   place_type,
            "body_name":    body_name,
            "body_type":    body_type,
            "meeting_date": date_str(meeting_date),
            "meeting_time": ev.get("EventTime", ""),
            "location":     ev.get("EventLocation", ""),
            "source_url":   f"https://{slug}.legistar.com",
            "platform":     "Legistar",
            **dl,
        })
        added += 1

    return added


def _get_attachment(slug, event_id):
    if not event_id:
        return None
    try:
        url = (f"https://webapi.legistar.com/v1/{slug}"
               f"/Events/{event_id}/EventItems?AgendaNote=1")
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return None
        for item in parse_legistar_xml(r.content):
            href = item.get("EventAgendaFile", "")
            if href and ".pdf" in href.lower():
                return href
    except Exception:
        pass
    return None
