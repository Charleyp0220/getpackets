"""
scrapers/granicus.py — Granicus Peak Agenda scraper.

Granicus hosts meeting agendas at:
  https://{slug}.granicus.com/ViewPublisher.php?view_id={id}

The agenda PDFs are accessible at:
  https://legistar2.granicus.com/{slug}/meetings/{year}/{month}/{clip_id}_A_{title}.pdf
"""

import requests, re
from datetime import date
from bs4 import BeautifulSoup
from utils import classify_body, is_future_or_today, parse_date, date_str, download_packet
from constants import HEADERS, REQUEST_TIMEOUT

GRANICUS_CITIES = {
    # California
    "fresno":           ("California",     "Fresno",           1),
    "stockton":         ("California",     "Stockton",         1),
    "bakersfield":      ("California",     "Bakersfield",      1),
    "chula-vista":      ("California",     "Chula Vista",      1),
    "santa-barbara":    ("California",     "Santa Barbara",    1),
    "elk-grove":        ("California",     "Elk Grove",        1),
    "vallejo":          ("California",     "Vallejo",          1),
    "victorville":      ("California",     "Victorville",      1),
    "costa-mesa":       ("California",     "Costa Mesa",       1),
    "westcovina":       ("California",     "West Covina",      1),
    "downey":           ("California",     "Downey",           1),
    "inglewood":        ("California",     "Inglewood",        1),
    "el-monte":         ("California",     "El Monte",         1),
    "petaluma":         ("California",     "Petaluma",         1),
    "vacaville":        ("California",     "Vacaville",        1),
    "camarillo":        ("California",     "Camarillo",        1),
    "redding":          ("California",     "Redding",          1),
    "chico":            ("California",     "Chico",            1),
    "clovis":           ("California",     "Clovis",           1),
    "antioch":          ("California",     "Antioch",          1),
    "richmond":         ("California",     "Richmond",         1),
    "daly-city":        ("California",     "Daly City",        1),
    "san-mateo":        ("California",     "San Mateo",        1),
    "santa-clara":      ("California",     "Santa Clara",      1),
    "sunnyvale":        ("California",     "Sunnyvale",        1),
    "thousand-oaks":    ("California",     "Thousand Oaks",    1),
    "simi-valley":      ("California",     "Simi Valley",      1),
    "orange":           ("California",     "Orange",           1),
    "concord":          ("California",     "Concord",          1),
    "roseville":        ("California",     "Roseville",        1),
    # Texas
    "plano":            ("Texas",          "Plano",            1),
    "garland":          ("Texas",          "Garland",          1),
    "irving":           ("Texas",          "Irving",           1),
    "pearland":         ("Texas",          "Pearland",         1),
    "sugar-land":       ("Texas",          "Sugar Land",       1),
    "allen":            ("Texas",          "Allen",            1),
    "richardson":       ("Texas",          "Richardson",       1),
    "lewisville":       ("Texas",          "Lewisville",       1),
    "tyler":            ("Texas",          "Tyler",            1),
    "abilene":          ("Texas",          "Abilene",          1),
    "wichitafalls":     ("Texas",          "Wichita Falls",    1),
    # Florida
    "sarasota":         ("Florida",        "Sarasota",         1),
    "bradenton":        ("Florida",        "Bradenton",        1),
    "lakeland":         ("Florida",        "Lakeland",         1),
    "kissimmee":        ("Florida",        "Kissimmee",        1),
    "daytona-beach":    ("Florida",        "Daytona Beach",    1),
    "ocala":            ("Florida",        "Ocala",            1),
    "palm-bay":         ("Florida",        "Palm Bay",         1),
    "pompano-beach":    ("Florida",        "Pompano Beach",    1),
    "boca-raton":       ("Florida",        "Boca Raton",       1),
    # Georgia
    "columbus-ga":      ("Georgia",        "Columbus",         1),
    "savannah":         ("Georgia",        "Savannah",         1),
    "macon":            ("Georgia",        "Macon",            1),
    "athens":           ("Georgia",        "Athens",           1),
    "sandy-springs":    ("Georgia",        "Sandy Springs",    1),
    "warner-robins":    ("Georgia",        "Warner Robins",    1),
    # North Carolina
    "wilmington":       ("North Carolina", "Wilmington",       1),
    "high-point":       ("North Carolina", "High Point",       1),
    "concord-nc":       ("North Carolina", "Concord",          1),
    "greenville-nc":    ("North Carolina", "Greenville",       1),
    "asheville":        ("North Carolina", "Asheville",        1),
    "chapel-hill":      ("North Carolina", "Chapel Hill",      1),
    "gastonia":         ("North Carolina", "Gastonia",         1),
    # Ohio
    "parma":            ("Ohio",           "Parma",            1),
    "youngstown":       ("Ohio",           "Youngstown",       1),
    "lorain":           ("Ohio",           "Lorain",           1),
    "hamilton-oh":      ("Ohio",           "Hamilton",         1),
    "kettering":        ("Ohio",           "Kettering",        1),
    "elyria":           ("Ohio",           "Elyria",           1),
    "springfield-oh":   ("Ohio",           "Springfield",      1),
    "cuyahoga-falls":   ("Ohio",           "Cuyahoga Falls",   1),
    # Michigan
    "sterling-heights": ("Michigan",       "Sterling Heights", 1),
    "ann-arbor":        ("Michigan",       "Ann Arbor",        1),
    "livonia":          ("Michigan",       "Livonia",          1),
    "dearborn":         ("Michigan",       "Dearborn",         1),
    "westland":         ("Michigan",       "Westland",         1),
    "wyoming-mi":       ("Michigan",       "Wyoming",          1),
    "southfield":       ("Michigan",       "Southfield",       1),
    "rochester-hills":  ("Michigan",       "Rochester Hills",  1),
    # Washington
    "vancouver":        ("Washington",     "Vancouver",        1),
    "bellingham":       ("Washington",     "Bellingham",       1),
    "yakima":           ("Washington",     "Yakima",           1),
    "federal-way":      ("Washington",     "Federal Way",      1),
    "marysville":       ("Washington",     "Marysville",       1),
    "auburn":           ("Washington",     "Auburn",           1),
    "kennewick":        ("Washington",     "Kennewick",        1),
    "lacey":            ("Washington",     "Lacey",            1),
    "richland":         ("Washington",     "Richland",         1),
    "spokane-valley":   ("Washington",     "Spokane Valley",   1),
    # Colorado
    "colorado-springs": ("Colorado",       "Colorado Springs", 1),
    "thornton":         ("Colorado",       "Thornton",         1),
    "westminster":      ("Colorado",       "Westminster",      1),
    "centennial":       ("Colorado",       "Centennial",       1),
    "broomfield":       ("Colorado",       "Broomfield",       1),
    "castle-rock":      ("Colorado",       "Castle Rock",      1),
    "commerce-city":    ("Colorado",       "Commerce City",    1),
    "loveland":         ("Colorado",       "Loveland",         1),
    # Arizona
    "surprise":         ("Arizona",        "Surprise",         1),
    "avondale":         ("Arizona",        "Avondale",         1),
    "flagstaff":        ("Arizona",        "Flagstaff",        1),
    "yuma":             ("Arizona",        "Yuma",             1),
    "prescott":         ("Arizona",        "Prescott",         1),
    "peoria-az":        ("Arizona",        "Peoria",           1),
    # Nevada
    "north-las-vegas":  ("Nevada",         "North Las Vegas",  1),
    "sparks":           ("Nevada",         "Sparks",           1),
    "carson-city":      ("Nevada",         "Carson City",      1),
    # Oregon
    "bend":             ("Oregon",         "Bend",             1),
    "medford":          ("Oregon",         "Medford",          1),
    "corvallis":        ("Oregon",         "Corvallis",        1),
    "springfield-or":   ("Oregon",         "Springfield",      1),
    "albany-or":        ("Oregon",         "Albany",           1),
    "gresham":          ("Oregon",         "Gresham",          1),
    # Minnesota
    "rochester-mn":     ("Minnesota",      "Rochester",        1),
    "bloomington-mn":   ("Minnesota",      "Bloomington",      1),
    "brooklyn-park":    ("Minnesota",      "Brooklyn Park",    1),
    "plymouth-mn":      ("Minnesota",      "Plymouth",         1),
    "maple-grove":      ("Minnesota",      "Maple Grove",      1),
    "woodbury":         ("Minnesota",      "Woodbury",         1),
    "st-cloud":         ("Minnesota",      "St. Cloud",        1),
    "eagan":            ("Minnesota",      "Eagan",            1),
    # Indiana
    "carmel":           ("Indiana",        "Carmel",           1),
    "fishers":          ("Indiana",        "Fishers",          1),
    "bloomington-in":   ("Indiana",        "Bloomington",      1),
    "hammond":          ("Indiana",        "Hammond",          1),
    "gary":             ("Indiana",        "Gary",             1),
    "muncie":           ("Indiana",        "Muncie",           1),
    "terre-haute":      ("Indiana",        "Terre Haute",      1),
    "noblesville":      ("Indiana",        "Noblesville",      1),
    # Missouri
    "lees-summit":      ("Missouri",       "Lee's Summit",     1),
    "ofallon":          ("Missouri",       "O'Fallon",         1),
    "st-joseph":        ("Missouri",       "St. Joseph",       1),
    "columbia-mo":      ("Missouri",       "Columbia",         1),
    "blue-springs":     ("Missouri",       "Blue Springs",     1),
    "florissant":       ("Missouri",       "Florissant",       1),
    "joplin":           ("Missouri",       "Joplin",           1),
    # Wisconsin
    "appleton":         ("Wisconsin",      "Appleton",         1),
    "oshkosh":          ("Wisconsin",      "Oshkosh",          1),
    "eau-claire":       ("Wisconsin",      "Eau Claire",       1),
    "janesville":       ("Wisconsin",      "Janesville",       1),
    "west-allis":       ("Wisconsin",      "West Allis",       1),
    "la-crosse":        ("Wisconsin",      "La Crosse",        1),
    "sheboygan":        ("Wisconsin",      "Sheboygan",        1),
    # South Carolina
    "north-charleston": ("South Carolina", "North Charleston", 1),
    "mount-pleasant":   ("South Carolina", "Mount Pleasant",   1),
    "rock-hill":        ("South Carolina", "Rock Hill",        1),
    "summerville":      ("South Carolina", "Summerville",      1),
    "spartanburg":      ("South Carolina", "Spartanburg",      1),
    # Virginia
    "roanoke":          ("Virginia",       "Roanoke",          1),
    "portsmouth":       ("Virginia",       "Portsmouth",       1),
    "suffolk":          ("Virginia",       "Suffolk",          1),
    "lynchburg":        ("Virginia",       "Lynchburg",        1),
    "harrisonburg":     ("Virginia",       "Harrisonburg",     1),
    "charlottesville":  ("Virginia",       "Charlottesville",  1),
    "fredericksburg":   ("Virginia",       "Fredericksburg",   1),
    # New Jersey
    "paterson":         ("New Jersey",     "Paterson",         1),
    "elizabeth":        ("New Jersey",     "Elizabeth",        1),
    "trenton":          ("New Jersey",     "Trenton",          1),
    "camden":           ("New Jersey",     "Camden",           1),
    "clifton":          ("New Jersey",     "Clifton",          1),
    # Maryland
    "rockville":        ("Maryland",       "Rockville",        1),
    "gaithersburg":     ("Maryland",       "Gaithersburg",     1),
    "bowie":            ("Maryland",       "Bowie",            1),
    "hagerstown":       ("Maryland",       "Hagerstown",       1),
    "annapolis":        ("Maryland",       "Annapolis",        1),
    # Utah
    "west-valley-city": ("Utah",           "West Valley City", 1),
    "ogden":            ("Utah",           "Ogden",            1),
    "st-george":        ("Utah",           "St. George",       1),
    "layton":           ("Utah",           "Layton",           1),
    "south-jordan":     ("Utah",           "South Jordan",     1),
    "orem":             ("Utah",           "Orem",             1),
    "sandy":            ("Utah",           "Sandy",            1),
    # Kansas
    "olathe":           ("Kansas",         "Olathe",           1),
    "overland-park":    ("Kansas",         "Overland Park",    1),
    "topeka":           ("Kansas",         "Topeka",           1),
    "lawrence":         ("Kansas",         "Lawrence",         1),
    "shawnee":          ("Kansas",         "Shawnee",          1),
    "manhattan-ks":     ("Kansas",         "Manhattan",        1),
    # Iowa
    "cedar-rapids":     ("Iowa",           "Cedar Rapids",     1),
    "davenport":        ("Iowa",           "Davenport",        1),
    "sioux-city":       ("Iowa",           "Sioux City",       1),
    "iowa-city":        ("Iowa",           "Iowa City",        1),
    "waterloo":         ("Iowa",           "Waterloo",         1),
    "ames":             ("Iowa",           "Ames",             1),
    "west-des-moines":  ("Iowa",           "West Des Moines",  1),
    "dubuque":          ("Iowa",           "Dubuque",          1),
    # Nebraska
    "lincoln":          ("Nebraska",       "Lincoln",          1),
    "bellevue-ne":      ("Nebraska",       "Bellevue",         1),
    "grand-island":     ("Nebraska",       "Grand Island",     1),
    # Louisiana
    "baton-rouge":      ("Louisiana",      "Baton Rouge",      1),
    "lafayette-la":     ("Louisiana",      "Lafayette",        1),
    "lake-charles":     ("Louisiana",      "Lake Charles",     1),
    "kenner":           ("Louisiana",      "Kenner",           1),
    "bossier-city":     ("Louisiana",      "Bossier City",     1),
    # Mississippi
    "jackson-ms":       ("Mississippi",    "Jackson",          1),
    "gulfport":         ("Mississippi",    "Gulfport",         1),
    "southaven":        ("Mississippi",    "Southaven",        1),
    "hattiesburg":      ("Mississippi",    "Hattiesburg",      1),
    "biloxi":           ("Mississippi",    "Biloxi",           1),
    # Alabama
    "mobile":           ("Alabama",        "Mobile",           1),
    "tuscaloosa":       ("Alabama",        "Tuscaloosa",       1),
    "hoover":           ("Alabama",        "Hoover",           1),
    "dothan":           ("Alabama",        "Dothan",           1),
    "auburn-al":        ("Alabama",        "Auburn",           1),
    # Arkansas
    "little-rock":      ("Arkansas",       "Little Rock",      1),
    "fort-smith":       ("Arkansas",       "Fort Smith",       1),
    "fayetteville-ar":  ("Arkansas",       "Fayetteville",     1),
    "springdale":       ("Arkansas",       "Springdale",       1),
    # New Mexico
    "las-cruces":       ("New Mexico",     "Las Cruces",       1),
    "rio-rancho":       ("New Mexico",     "Rio Rancho",       1),
    "santa-fe":         ("New Mexico",     "Santa Fe",         1),
    # Idaho
    "nampa":            ("Idaho",          "Nampa",            1),
    "meridian":         ("Idaho",          "Meridian",         1),
    "idaho-falls":      ("Idaho",          "Idaho Falls",      1),
    "pocatello":        ("Idaho",          "Pocatello",        1),
    "caldwell":         ("Idaho",          "Caldwell",         1),
    # Montana
    "missoula":         ("Montana",        "Missoula",         1),
    "great-falls":      ("Montana",        "Great Falls",      1),
    "bozeman":          ("Montana",        "Bozeman",          1),
    "butte":            ("Montana",        "Butte",            1),
    # New Hampshire
    "nashua":           ("New Hampshire",  "Nashua",           1),
    "concord-nh":       ("New Hampshire",  "Concord",          1),
    "derry":            ("New Hampshire",  "Derry",            1),
    # Maine
    "portland-me":      ("Maine",          "Portland",         1),
    "lewiston":         ("Maine",          "Lewiston",         1),
    "bangor":           ("Maine",          "Bangor",           1),
    # Vermont
    "burlington-vt":    ("Vermont",        "Burlington",       1),
    "south-burlington": ("Vermont",        "South Burlington", 1),
    # West Virginia
    "huntington":       ("West Virginia",  "Huntington",       1),
    "morgantown":       ("West Virginia",  "Morgantown",       1),
    "parkersburg":      ("West Virginia",  "Parkersburg",      1),
    # Delaware
    "dover":            ("Delaware",       "Dover",            1),
    "newark-de":        ("Delaware",       "Newark",           1),
    # Rhode Island
    "cranston":         ("Rhode Island",   "Cranston",         1),
    "pawtucket":        ("Rhode Island",   "Pawtucket",        1),
    # Kentucky
    "bowling-green":    ("Kentucky",       "Bowling Green",    1),
    "owensboro":        ("Kentucky",       "Owensboro",        1),
    "covington":        ("Kentucky",       "Covington",        1),
    # Oklahoma
    "norman":           ("Oklahoma",       "Norman",           1),
    "broken-arrow":     ("Oklahoma",       "Broken Arrow",     1),
    "lawton":           ("Oklahoma",       "Lawton",           1),
    "edmond":           ("Oklahoma",       "Edmond",           1),
    "moore":            ("Oklahoma",       "Moore",            1),
    # Tennessee extra
    "murfreesboro":     ("Tennessee",      "Murfreesboro",     1),
    "franklin-tn":      ("Tennessee",      "Franklin",         1),
    "jackson-tn":       ("Tennessee",      "Jackson",          1),
    "johnson-city":     ("Tennessee",      "Johnson City",     1),
    "kingsport":        ("Tennessee",      "Kingsport",        1),
    # Pennsylvania extra
    "scranton":         ("Pennsylvania",   "Scranton",         1),
    "reading":          ("Pennsylvania",   "Reading",          1),
    "bethlehem":        ("Pennsylvania",   "Bethlehem",        1),
    "lancaster-pa":     ("Pennsylvania",   "Lancaster",        1),
    "harrisburg":       ("Pennsylvania",   "Harrisburg",       1),
    # New York extra
    "yonkers":          ("New York",       "Yonkers",          1),
    "mount-vernon":     ("New York",       "Mount Vernon",     1),
    "new-rochelle":     ("New York",       "New Rochelle",     1),
    "white-plains":     ("New York",       "White Plains",     1),
    "utica":            ("New York",       "Utica",            1),
    "schenectady":      ("New York",       "Schenectady",      1),
    "troy-ny":          ("New York",       "Troy",             1),
}

GRANICUS_BASE = "https://{slug}.granicus.com/ViewPublisher.php?view_id=1"


def scrape_granicus(state: str, collected: list, max_packets: int) -> int:
    """Scrape Granicus/Peak Agenda for a given state."""
    cities = {slug: info for slug, info in GRANICUS_CITIES.items()
              if info[0] == state}
    if not cities:
        return 0

    added = 0
    today = date.today()

    for slug, (st, municipality, view_id) in cities.items():
        if len(collected) >= max_packets:
            break
        url = f"https://{slug}.granicus.com/ViewPublisher.php?view_id={view_id}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "lxml")
        except Exception:
            continue

        # Find meeting rows
        for row in soup.select("tr, .row, .meeting-row, li[class*='meeting']"):
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

            # Find PDF link
            agenda_url = None
            for a in row.select("a[href]"):
                href = a["href"]
                label = a.get_text(strip=True).lower()
                if not href.startswith("http"):
                    href = f"https://{slug}.granicus.com{href}"
                if any(x in href.lower() or x in label
                       for x in [".pdf", "agenda", "packet", "download", "view"]):
                    agenda_url = href
                    break

            if not agenda_url:
                continue

            name_el = row.select_one("td:first-child, .event-name, strong, b")
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
                "source_url": url, "platform": "Granicus",
                **dl,
            })
            added += 1

    return added
