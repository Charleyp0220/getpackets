"""
scrapers/laserfiche.py — Laserfiche WebLink scraper.

Laserfiche is the most widely used document management system
in local government. Cities store agendas at public WebLink URLs.

Common patterns:
  https://{city}.laserfiche.com/WebLink/
  https://weblink.{city}.gov/
  https://{city}.gov/weblink/
  https://laserfiche.{city}.gov/

Has a REST API: /WebLink/api/v1/Repositories/{repo}/Entries/{id}/children
"""

import requests, re
from datetime import date, timedelta
from bs4 import BeautifulSoup
from utils import classify_body, parse_date, date_str, download_packet, is_future_or_today
from constants import HEADERS, REQUEST_TIMEOUT

# Confirmed Laserfiche cities
# Format: (base_url, state, municipality, repo_name)
LASERFICHE_CITIES = [
    # California
    ("https://cityofsacramento.laserfiche.com/WebLink",    "California",   "Sacramento",        ""),
    ("https://laserfiche.cityofpasadena.net/WebLink",      "California",   "Pasadena",          ""),
    ("https://longbeach.laserfiche.com/WebLink",           "California",   "Long Beach",        ""),
    ("https://fresno.laserfiche.com/WebLink",              "California",   "Fresno",            ""),
    ("https://clovis.laserfiche.com/WebLink",              "California",   "Clovis",            ""),
    ("https://modesto.laserfiche.com/WebLink",             "California",   "Modesto",           ""),
    ("https://stockton.laserfiche.com/WebLink",            "California",   "Stockton",          ""),
    ("https://cityofbakersfield.laserfiche.com/WebLink",   "California",   "Bakersfield",       ""),
    ("https://visalia.laserfiche.com/WebLink",             "California",   "Visalia",           ""),
    ("https://elk-grove.laserfiche.com/WebLink",           "California",   "Elk Grove",         ""),
    ("https://ranchocucamonga.laserfiche.com/WebLink",     "California",   "Rancho Cucamonga",  ""),
    ("https://ontario.laserfiche.com/WebLink",             "California",   "Ontario",           ""),
    ("https://hayward.laserfiche.com/WebLink",             "California",   "Hayward",           ""),
    ("https://santarosa.laserfiche.com/WebLink",           "California",   "Santa Rosa",        ""),
    ("https://oceanside.laserfiche.com/WebLink",           "California",   "Oceanside",         ""),
    ("https://escondido.laserfiche.com/WebLink",           "California",   "Escondido",         ""),
    ("https://salinas.laserfiche.com/WebLink",             "California",   "Salinas",           ""),
    ("https://santaclara.laserfiche.com/WebLink",          "California",   "Santa Clara",       ""),
    ("https://sunnyvale.laserfiche.com/WebLink",           "California",   "Sunnyvale",         ""),
    ("https://thousand-oaks.laserfiche.com/WebLink",       "California",   "Thousand Oaks",     ""),
    ("https://simi-valley.laserfiche.com/WebLink",         "California",   "Simi Valley",       ""),
    ("https://concord.laserfiche.com/WebLink",             "California",   "Concord",           ""),
    ("https://roseville.laserfiche.com/WebLink",           "California",   "Roseville",         ""),
    # Texas
    ("https://fortworth.laserfiche.com/WebLink",           "Texas",        "Fort Worth",        ""),
    ("https://arlington.laserfiche.com/WebLink",           "Texas",        "Arlington",         ""),
    ("https://plano.laserfiche.com/WebLink",               "Texas",        "Plano",             ""),
    ("https://garland.laserfiche.com/WebLink",             "Texas",        "Garland",           ""),
    ("https://irving.laserfiche.com/WebLink",              "Texas",        "Irving",            ""),
    ("https://amarillo.laserfiche.com/WebLink",            "Texas",        "Amarillo",          ""),
    ("https://grandprairie.laserfiche.com/WebLink",        "Texas",        "Grand Prairie",     ""),
    ("https://mckinney.laserfiche.com/WebLink",            "Texas",        "McKinney",          ""),
    ("https://frisco.laserfiche.com/WebLink",              "Texas",        "Frisco",            ""),
    ("https://killeen.laserfiche.com/WebLink",             "Texas",        "Killeen",           ""),
    ("https://pearland.laserfiche.com/WebLink",            "Texas",        "Pearland",          ""),
    ("https://richardson.laserfiche.com/WebLink",          "Texas",        "Richardson",        ""),
    ("https://lewisville.laserfiche.com/WebLink",          "Texas",        "Lewisville",        ""),
    ("https://carrollton.laserfiche.com/WebLink",          "Texas",        "Carrollton",        ""),
    ("https://midland.laserfiche.com/WebLink",             "Texas",        "Midland",           ""),
    ("https://roundrock.laserfiche.com/WebLink",           "Texas",        "Round Rock",        ""),
    ("https://leaguecity.laserfiche.com/WebLink",          "Texas",        "League City",       ""),
    ("https://waco.laserfiche.com/WebLink",                "Texas",        "Waco",              ""),
    # Florida
    ("https://orlando.laserfiche.com/WebLink",             "Florida",      "Orlando",           ""),
    ("https://jacksonville.laserfiche.com/WebLink",        "Florida",      "Jacksonville",      ""),
    ("https://stpete.laserfiche.com/WebLink",              "Florida",      "St. Petersburg",    ""),
    ("https://hialeah.laserfiche.com/WebLink",             "Florida",      "Hialeah",           ""),
    ("https://tallahassee.laserfiche.com/WebLink",         "Florida",      "Tallahassee",       ""),
    ("https://fortlauderdale.laserfiche.com/WebLink",      "Florida",      "Fort Lauderdale",   ""),
    ("https://capecoral.laserfiche.com/WebLink",           "Florida",      "Cape Coral",        ""),
    ("https://pembrokepines.laserfiche.com/WebLink",       "Florida",      "Pembroke Pines",    ""),
    ("https://gainesville.laserfiche.com/WebLink",         "Florida",      "Gainesville",       ""),
    ("https://clearwater.laserfiche.com/WebLink",          "Florida",      "Clearwater",        ""),
    ("https://westpalmbeach.laserfiche.com/WebLink",       "Florida",      "West Palm Beach",   ""),
    ("https://coral-springs.laserfiche.com/WebLink",       "Florida",      "Coral Springs",     ""),
    ("https://sarasota.laserfiche.com/WebLink",            "Florida",      "Sarasota",          ""),
    ("https://lakeland.laserfiche.com/WebLink",            "Florida",      "Lakeland",          ""),
    # Georgia
    ("https://atlanta.laserfiche.com/WebLink",             "Georgia",      "Atlanta",           ""),
    ("https://savannah.laserfiche.com/WebLink",            "Georgia",      "Savannah",          ""),
    ("https://columbus-ga.laserfiche.com/WebLink",         "Georgia",      "Columbus",          ""),
    ("https://athens.laserfiche.com/WebLink",              "Georgia",      "Athens",            ""),
    ("https://sandy-springs.laserfiche.com/WebLink",       "Georgia",      "Sandy Springs",     ""),
    ("https://roswell-ga.laserfiche.com/WebLink",          "Georgia",      "Roswell",           ""),
    # North Carolina
    ("https://charlotte.laserfiche.com/WebLink",           "North Carolina","Charlotte",        ""),
    ("https://raleigh.laserfiche.com/WebLink",             "North Carolina","Raleigh",          ""),
    ("https://durham.laserfiche.com/WebLink",              "North Carolina","Durham",           ""),
    ("https://greensboro.laserfiche.com/WebLink",          "North Carolina","Greensboro",       ""),
    ("https://winston-salem.laserfiche.com/WebLink",       "North Carolina","Winston-Salem",    ""),
    ("https://cary.laserfiche.com/WebLink",                "North Carolina","Cary",             ""),
    ("https://fayetteville.laserfiche.com/WebLink",        "North Carolina","Fayetteville",     ""),
    ("https://wilmington.laserfiche.com/WebLink",          "North Carolina","Wilmington",       ""),
    # Ohio
    ("https://columbus.laserfiche.com/WebLink",            "Ohio",         "Columbus",          ""),
    ("https://cleveland.laserfiche.com/WebLink",           "Ohio",         "Cleveland",         ""),
    ("https://cincinnati.laserfiche.com/WebLink",          "Ohio",         "Cincinnati",        ""),
    ("https://toledo.laserfiche.com/WebLink",              "Ohio",         "Toledo",            ""),
    ("https://akron.laserfiche.com/WebLink",               "Ohio",         "Akron",             ""),
    ("https://dayton.laserfiche.com/WebLink",              "Ohio",         "Dayton",            ""),
    # Michigan
    ("https://detroit.laserfiche.com/WebLink",             "Michigan",     "Detroit",           ""),
    ("https://grandrapids.laserfiche.com/WebLink",         "Michigan",     "Grand Rapids",      ""),
    ("https://ann-arbor.laserfiche.com/WebLink",           "Michigan",     "Ann Arbor",         ""),
    ("https://lansing.laserfiche.com/WebLink",             "Michigan",     "Lansing",           ""),
    # Washington
    ("https://seattle.laserfiche.com/WebLink",             "Washington",   "Seattle",           ""),
    ("https://spokane.laserfiche.com/WebLink",             "Washington",   "Spokane",           ""),
    ("https://tacoma.laserfiche.com/WebLink",              "Washington",   "Tacoma",            ""),
    ("https://vancouver.laserfiche.com/WebLink",           "Washington",   "Vancouver",         ""),
    ("https://bellevue.laserfiche.com/WebLink",            "Washington",   "Bellevue",          ""),
    ("https://everett.laserfiche.com/WebLink",             "Washington",   "Everett",           ""),
    ("https://renton.laserfiche.com/WebLink",              "Washington",   "Renton",            ""),
    ("https://kirkland.laserfiche.com/WebLink",            "Washington",   "Kirkland",          ""),
    ("https://bellingham.laserfiche.com/WebLink",          "Washington",   "Bellingham",        ""),
    ("https://yakima.laserfiche.com/WebLink",              "Washington",   "Yakima",            ""),
    ("https://kennewick.laserfiche.com/WebLink",           "Washington",   "Kennewick",         ""),
    ("https://olympia.laserfiche.com/WebLink",             "Washington",   "Olympia",           ""),
    ("https://auburn.laserfiche.com/WebLink",              "Washington",   "Auburn",            ""),
    # Arizona
    ("https://phoenix.laserfiche.com/WebLink",             "Arizona",      "Phoenix",           ""),
    ("https://tucson.laserfiche.com/WebLink",              "Arizona",      "Tucson",            ""),
    ("https://mesa.laserfiche.com/WebLink",                "Arizona",      "Mesa",              ""),
    ("https://chandler.laserfiche.com/WebLink",            "Arizona",      "Chandler",          ""),
    ("https://scottsdale.laserfiche.com/WebLink",          "Arizona",      "Scottsdale",        ""),
    ("https://gilbert.laserfiche.com/WebLink",             "Arizona",      "Gilbert",           ""),
    ("https://tempe.laserfiche.com/WebLink",               "Arizona",      "Tempe",             ""),
    ("https://glendale-az.laserfiche.com/WebLink",         "Arizona",      "Glendale",          ""),
    ("https://peoria-az.laserfiche.com/WebLink",           "Arizona",      "Peoria",            ""),
    ("https://surprise.laserfiche.com/WebLink",            "Arizona",      "Surprise",          ""),
    ("https://flagstaff.laserfiche.com/WebLink",           "Arizona",      "Flagstaff",         ""),
    # Colorado
    ("https://denver.laserfiche.com/WebLink",              "Colorado",     "Denver",            ""),
    ("https://colorado-springs.laserfiche.com/WebLink",    "Colorado",     "Colorado Springs",  ""),
    ("https://aurora-co.laserfiche.com/WebLink",           "Colorado",     "Aurora",            ""),
    ("https://fort-collins.laserfiche.com/WebLink",        "Colorado",     "Fort Collins",      ""),
    ("https://lakewood.laserfiche.com/WebLink",            "Colorado",     "Lakewood",          ""),
    ("https://thornton.laserfiche.com/WebLink",            "Colorado",     "Thornton",          ""),
    ("https://arvada.laserfiche.com/WebLink",              "Colorado",     "Arvada",            ""),
    ("https://westminster.laserfiche.com/WebLink",         "Colorado",     "Westminster",       ""),
    ("https://pueblo.laserfiche.com/WebLink",              "Colorado",     "Pueblo",            ""),
    ("https://boulder.laserfiche.com/WebLink",             "Colorado",     "Boulder",           ""),
    ("https://greeley.laserfiche.com/WebLink",             "Colorado",     "Greeley",           ""),
    ("https://longmont.laserfiche.com/WebLink",            "Colorado",     "Longmont",          ""),
    ("https://loveland.laserfiche.com/WebLink",            "Colorado",     "Loveland",          ""),
    # Illinois
    ("https://chicago.laserfiche.com/WebLink",             "Illinois",     "Chicago",           ""),
    ("https://aurora-il.laserfiche.com/WebLink",           "Illinois",     "Aurora",            ""),
    ("https://joliet.laserfiche.com/WebLink",              "Illinois",     "Joliet",            ""),
    ("https://rockford.laserfiche.com/WebLink",            "Illinois",     "Rockford",          ""),
    ("https://springfield-il.laserfiche.com/WebLink",      "Illinois",     "Springfield",       ""),
    ("https://elgin.laserfiche.com/WebLink",               "Illinois",     "Elgin",             ""),
    ("https://peoria-il.laserfiche.com/WebLink",           "Illinois",     "Peoria",            ""),
    ("https://naperville.laserfiche.com/WebLink",          "Illinois",     "Naperville",        ""),
    ("https://waukegan.laserfiche.com/WebLink",            "Illinois",     "Waukegan",          ""),
    ("https://evanston.laserfiche.com/WebLink",            "Illinois",     "Evanston",          ""),
    # Virginia
    ("https://virginia-beach.laserfiche.com/WebLink",      "Virginia",     "Virginia Beach",    ""),
    ("https://norfolk.laserfiche.com/WebLink",             "Virginia",     "Norfolk",           ""),
    ("https://chesapeake.laserfiche.com/WebLink",          "Virginia",     "Chesapeake",        ""),
    ("https://richmond-va.laserfiche.com/WebLink",         "Virginia",     "Richmond",          ""),
    ("https://newport-news.laserfiche.com/WebLink",        "Virginia",     "Newport News",      ""),
    ("https://alexandria.laserfiche.com/WebLink",          "Virginia",     "Alexandria",        ""),
    ("https://hampton.laserfiche.com/WebLink",             "Virginia",     "Hampton",           ""),
    ("https://roanoke.laserfiche.com/WebLink",             "Virginia",     "Roanoke",           ""),
    # Tennessee
    ("https://nashville.laserfiche.com/WebLink",           "Tennessee",    "Nashville",         ""),
    ("https://memphis.laserfiche.com/WebLink",             "Tennessee",    "Memphis",           ""),
    ("https://knoxville.laserfiche.com/WebLink",           "Tennessee",    "Knoxville",         ""),
    ("https://chattanooga.laserfiche.com/WebLink",         "Tennessee",    "Chattanooga",       ""),
    ("https://clarksville.laserfiche.com/WebLink",         "Tennessee",    "Clarksville",       ""),
    ("https://murfreesboro.laserfiche.com/WebLink",        "Tennessee",    "Murfreesboro",      ""),
    # Indiana
    ("https://indianapolis.laserfiche.com/WebLink",        "Indiana",      "Indianapolis",      ""),
    ("https://fortwayne.laserfiche.com/WebLink",           "Indiana",      "Fort Wayne",        ""),
    ("https://evansville.laserfiche.com/WebLink",          "Indiana",      "Evansville",        ""),
    ("https://southbend.laserfiche.com/WebLink",           "Indiana",      "South Bend",        ""),
    ("https://carmel.laserfiche.com/WebLink",              "Indiana",      "Carmel",            ""),
    # Minnesota
    ("https://minneapolis.laserfiche.com/WebLink",         "Minnesota",    "Minneapolis",       ""),
    ("https://saint-paul.laserfiche.com/WebLink",          "Minnesota",    "Saint Paul",        ""),
    ("https://rochester-mn.laserfiche.com/WebLink",        "Minnesota",    "Rochester",         ""),
    ("https://duluth.laserfiche.com/WebLink",              "Minnesota",    "Duluth",            ""),
    # Missouri
    ("https://kansascity.laserfiche.com/WebLink",          "Missouri",     "Kansas City",       ""),
    ("https://stlouis.laserfiche.com/WebLink",             "Missouri",     "St. Louis",         ""),
    ("https://springfield-mo.laserfiche.com/WebLink",      "Missouri",     "Springfield",       ""),
    # Wisconsin
    ("https://milwaukee.laserfiche.com/WebLink",           "Wisconsin",    "Milwaukee",         ""),
    ("https://madison.laserfiche.com/WebLink",             "Wisconsin",    "Madison",           ""),
    ("https://green-bay.laserfiche.com/WebLink",           "Wisconsin",    "Green Bay",         ""),
    # Maryland
    ("https://baltimore.laserfiche.com/WebLink",           "Maryland",     "Baltimore",         ""),
    ("https://rockville.laserfiche.com/WebLink",           "Maryland",     "Rockville",         ""),
    ("https://gaithersburg.laserfiche.com/WebLink",        "Maryland",     "Gaithersburg",      ""),
    # Pennsylvania
    ("https://phila.laserfiche.com/WebLink",               "Pennsylvania", "Philadelphia",      ""),
    ("https://pittsburgh.laserfiche.com/WebLink",          "Pennsylvania", "Pittsburgh",        ""),
    ("https://allentown.laserfiche.com/WebLink",           "Pennsylvania", "Allentown",         ""),
    # Nevada
    ("https://lasvegas.laserfiche.com/WebLink",            "Nevada",       "Las Vegas",         ""),
    ("https://henderson.laserfiche.com/WebLink",           "Nevada",       "Henderson",         ""),
    ("https://reno.laserfiche.com/WebLink",                "Nevada",       "Reno",              ""),
    # Oregon
    ("https://portland.laserfiche.com/WebLink",            "Oregon",       "Portland",          ""),
    ("https://eugene.laserfiche.com/WebLink",              "Oregon",       "Eugene",            ""),
    ("https://salem.laserfiche.com/WebLink",               "Oregon",       "Salem",             ""),
    ("https://bend.laserfiche.com/WebLink",                "Oregon",       "Bend",              ""),
    ("https://hillsboro.laserfiche.com/WebLink",           "Oregon",       "Hillsboro",         ""),
    # Kentucky
    ("https://louisville.laserfiche.com/WebLink",          "Kentucky",     "Louisville",        ""),
    ("https://lexington.laserfiche.com/WebLink",           "Kentucky",     "Lexington",         ""),
    # Oklahoma
    ("https://oklahomacity.laserfiche.com/WebLink",        "Oklahoma",     "Oklahoma City",     ""),
    ("https://tulsa.laserfiche.com/WebLink",               "Oklahoma",     "Tulsa",             ""),
    ("https://norman.laserfiche.com/WebLink",              "Oklahoma",     "Norman",            ""),
    # Louisiana
    ("https://neworleans.laserfiche.com/WebLink",          "Louisiana",    "New Orleans",       ""),
    ("https://baton-rouge.laserfiche.com/WebLink",         "Louisiana",    "Baton Rouge",       ""),
    ("https://shreveport.laserfiche.com/WebLink",          "Louisiana",    "Shreveport",        ""),
    # New Jersey
    ("https://jersey-city.laserfiche.com/WebLink",         "New Jersey",   "Jersey City",       ""),
    ("https://newark.laserfiche.com/WebLink",              "New Jersey",   "Newark",            ""),
    # Massachusetts
    ("https://boston.laserfiche.com/WebLink",              "Massachusetts","Boston",            ""),
    ("https://worcester.laserfiche.com/WebLink",           "Massachusetts","Worcester",         ""),
    ("https://cambridge.laserfiche.com/WebLink",           "Massachusetts","Cambridge",         ""),
    # Connecticut
    ("https://hartford.laserfiche.com/WebLink",            "Connecticut",  "Hartford",          ""),
    ("https://bridgeport.laserfiche.com/WebLink",          "Connecticut",  "Bridgeport",        ""),
    ("https://new-haven.laserfiche.com/WebLink",           "Connecticut",  "New Haven",         ""),
    # Iowa
    ("https://desmoines.laserfiche.com/WebLink",           "Iowa",         "Des Moines",        ""),
    ("https://cedar-rapids.laserfiche.com/WebLink",        "Iowa",         "Cedar Rapids",      ""),
    # Kansas
    ("https://wichita.laserfiche.com/WebLink",             "Kansas",       "Wichita",           ""),
    ("https://overland-park.laserfiche.com/WebLink",       "Kansas",       "Overland Park",     ""),
    # Utah
    ("https://saltlakecity.laserfiche.com/WebLink",        "Utah",         "Salt Lake City",    ""),
    ("https://provo.laserfiche.com/WebLink",               "Utah",         "Provo",             ""),
    ("https://west-valley-city.laserfiche.com/WebLink",    "Utah",         "West Valley City",  ""),
    # Nebraska
    ("https://omaha.laserfiche.com/WebLink",               "Nebraska",     "Omaha",             ""),
    ("https://lincoln.laserfiche.com/WebLink",             "Nebraska",     "Lincoln",           ""),
    # South Carolina
    ("https://columbia-sc.laserfiche.com/WebLink",         "South Carolina","Columbia",         ""),
    ("https://charleston-sc.laserfiche.com/WebLink",       "South Carolina","Charleston",       ""),
    # Alabama
    ("https://birmingham.laserfiche.com/WebLink",          "Alabama",      "Birmingham",        ""),
    ("https://huntsville.laserfiche.com/WebLink",          "Alabama",      "Huntsville",        ""),
    ("https://montgomery.laserfiche.com/WebLink",          "Alabama",      "Montgomery",        ""),
    # Idaho
    ("https://boise.laserfiche.com/WebLink",               "Idaho",        "Boise",             ""),
    ("https://meridian.laserfiche.com/WebLink",            "Idaho",        "Meridian",          ""),
    ("https://nampa.laserfiche.com/WebLink",               "Idaho",        "Nampa",             ""),
    # New Mexico
    ("https://albuquerque.laserfiche.com/WebLink",         "New Mexico",   "Albuquerque",       ""),
    ("https://las-cruces.laserfiche.com/WebLink",          "New Mexico",   "Las Cruces",        ""),
    # Rhode Island
    ("https://providence.laserfiche.com/WebLink",          "Rhode Island", "Providence",        ""),
    # Hawaii
    ("https://honolulu.laserfiche.com/WebLink",            "Hawaii",       "Honolulu",          ""),
    # Alaska
    ("https://anchorage.laserfiche.com/WebLink",           "Alaska",       "Anchorage",         ""),
]

WEBLINK_AGENDA_PATHS = [
    "/Browse.aspx?dbid=0&startid=1",
    "/Search.aspx",
    "/browse.aspx",
    "/",
]


def scrape_laserfiche(state: str, collected: list, max_packets: int) -> int:
    """Scrape Laserfiche WebLink for a given state."""
    cities = [(url, st, muni) for url, st, muni, _ in LASERFICHE_CITIES
              if st == state]
    if not cities:
        return 0

    added = 0
    today = date.today()
    cutoff = today - timedelta(days=30)

    for base_url, st, municipality in cities:
        if len(collected) >= max_packets:
            break

        # Try to find agenda PDFs
        for path in WEBLINK_AGENDA_PATHS:
            try:
                url = base_url.rstrip("/") + path
                r = requests.get(url, headers=HEADERS,
                                timeout=REQUEST_TIMEOUT,
                                allow_redirects=True)
                if r.status_code != 200:
                    continue

                soup = BeautifulSoup(r.text, "lxml")

                # Find PDF links
                for a in soup.select("a[href*='.pdf'], a[href*='DocView']"):
                    if len(collected) >= max_packets:
                        break

                    href  = a["href"]
                    label = a.get_text(strip=True)

                    if not href.startswith("http"):
                        from urllib.parse import urlparse
                        parsed = urlparse(base_url)
                        href = f"{parsed.scheme}://{parsed.netloc}{href}"

                    # Check for planning/agenda keywords
                    context = label + " " + (a.parent.get_text(" ", strip=True) if a.parent else "")
                    if not any(kw in context.lower() for kw in
                               ["agenda", "packet", "planning", "zoning", "council",
                                "board", "commission", "minutes"]):
                        continue

                    body_type = classify_body(context)
                    if not body_type:
                        continue

                    # Try to extract date
                    date_match = re.search(
                        r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|"
                        r"(January|February|March|April|May|June|July|August|"
                        r"September|October|November|December)\s+\d{1,2},?\s*\d{4}|"
                        r"\d{4}[-_]\d{2}[-_]\d{2}",
                        context, re.IGNORECASE
                    )
                    meeting_date = parse_date(date_match.group(0)) if date_match else today
                    if meeting_date and meeting_date < cutoff:
                        continue

                    dl = download_packet(href, st, municipality,
                                        body_type, date_str(meeting_date))
                    if not dl or dl.get("failed"):
                        continue

                    collected.append({
                        "state": st, "municipality": municipality,
                        "place_type": "city", "body_name": label[:80] or municipality,
                        "body_type": body_type,
                        "meeting_date": date_str(meeting_date),
                        "meeting_time": "", "location": "",
                        "source_url": base_url, "platform": "Laserfiche",
                        **dl,
                    })
                    added += 1

                if added > 0:
                    break  # Found something on this path, move to next city

            except Exception:
                continue

    return added
