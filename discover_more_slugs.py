"""
discover_more_slugs.py — second pass slug discovery.

Tests alternate slug formats that the first pass missed:
- cityof{name} prefixes
- {name}city suffixes  
- county slugs
- regional agencies
- alternate spellings

Run: python discover_more_slugs.py
"""

import sys, os, requests, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)
from scrapers.legistar import LEGISTAR_CITIES

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0.0.0"}
TIMEOUT = 6
existing = set(LEGISTAR_CITIES.keys())

# Second pass — alternate formats for cities we know + new ones
CANDIDATES = []

# Generate cityof/townof/countyof variants for all existing cities
for slug, (state, name) in list(LEGISTAR_CITIES.items()):
    base = slug.replace("-", "").replace(" ", "").lower()
    for prefix in ["cityof", "townof", "villageof"]:
        CANDIDATES.append((f"{prefix}{base}", state, name))
    CANDIDATES.append((f"{base}city", state, name))
    CANDIDATES.append((f"{base}gov", state, name))

# Additional specific candidates not in first pass
EXTRA = [
    # Major cities with unusual slugs
    ("nyc",              "New York",       "New York City"),
    ("newyorkcity",      "New York",       "New York City"),
    ("cityofnewyork",    "New York",       "New York City"),
    ("nyccouncil",       "New York",       "NYC Council"),
    ("lacity",           "California",     "Los Angeles"),
    ("cityofla",         "California",     "Los Angeles"),
    ("lacityclerk",      "California",     "Los Angeles"),
    ("sfgov",            "California",     "San Francisco"),
    ("sfcity",           "California",     "San Francisco"),
    ("cityofsf",         "California",     "San Francisco"),
    ("sandiegoca",       "California",     "San Diego"),
    ("cityofsandiego",   "California",     "San Diego"),
    ("sanjoseca",        "California",     "San Jose"),
    ("cityofsanjose",    "California",     "San Jose"),
    ("oaklandca",        "California",     "Oakland"),
    ("cityofoakland",    "California",     "Oakland"),
    ("cityofberkeley",   "California",     "Berkeley"),
    ("cityofstockton",   "California",     "Stockton"),
    ("cityoffresno",     "California",     "Fresno"),
    ("cityofriverside",  "California",     "Riverside"),
    ("cityofanaheim",    "California",     "Anaheim"),
    ("cityofirvine",     "California",     "Irvine"),
    ("cityofchula",      "California",     "Chula Vista"),
    ("cityoffremont",    "California",     "Fremont"),
    ("cityofmodesto",    "California",     "Modesto"),
    ("cityoffontana",    "California",     "Fontana"),
    ("cityofoxnard",     "California",     "Oxnard"),
    ("cityofpasadena",   "California",     "Pasadena"),
    ("cityoftorrance",   "California",     "Torrance"),
    # Texas
    ("cityofaustin",     "Texas",          "Austin"),
    ("cityofhouston",    "Texas",          "Houston"),
    ("cityofdallas",     "Texas",          "Dallas"),
    ("cityofsanantonio", "Texas",          "San Antonio"),
    ("cityoffortworth",  "Texas",          "Fort Worth"),
    ("cityofelpaso",     "Texas",          "El Paso"),
    ("cityofarlington",  "Texas",          "Arlington"),
    ("cityofcorpuschristi","Texas",        "Corpus Christi"),
    ("cityofplano",      "Texas",          "Plano"),
    ("cityoflaredo",     "Texas",          "Laredo"),
    ("cityoflubbock",    "Texas",          "Lubbock"),
    ("cityofgarland",    "Texas",          "Garland"),
    ("cityofirving",     "Texas",          "Irving"),
    ("cityofamarillo",   "Texas",          "Amarillo"),
    ("cityofmcallen",    "Texas",          "McAllen"),
    ("cityofwaco",       "Texas",          "Waco"),
    ("cityofbrownsville","Texas",          "Brownsville"),
    ("cityofmidland",    "Texas",          "Midland"),
    ("cityofodessa",     "Texas",          "Odessa"),
    ("cityoftyler",      "Texas",          "Tyler"),
    ("cityofkilleen",    "Texas",          "Killeen"),
    ("cityofpearland",   "Texas",          "Pearland"),
    # Florida  
    ("cityofmiami",      "Florida",        "Miami"),
    ("cityoforlando",    "Florida",        "Orlando"),
    ("cityoftampa",      "Florida",        "Tampa"),
    ("cityofjacksonville","Florida",       "Jacksonville"),
    ("cityofstpete",     "Florida",        "St. Petersburg"),
    ("cityoftallahassee","Florida",        "Tallahassee"),
    ("cityofgainesville","Florida",        "Gainesville"),
    ("cityofclearwater", "Florida",        "Clearwater"),
    ("cityofsarasota",   "Florida",        "Sarasota"),
    ("cityofpensacola",  "Florida",        "Pensacola"),
    ("cityoflakeland",   "Florida",        "Lakeland"),
    ("cityofocala",      "Florida",        "Ocala"),
    # Ohio
    ("cityofcolumbus",   "Ohio",           "Columbus"),
    ("cityofcleveland",  "Ohio",           "Cleveland"),
    ("cityofcincinnati", "Ohio",           "Cincinnati"),
    ("cityoftoledo",     "Ohio",           "Toledo"),
    ("cityofakron",      "Ohio",           "Akron"),
    ("cityofdayton",     "Ohio",           "Dayton"),
    ("cityofparma",      "Ohio",           "Parma"),
    ("cityofcanton",     "Ohio",           "Canton"),
    ("cityofyoungstown", "Ohio",           "Youngstown"),
    ("cityoflorain",     "Ohio",           "Lorain"),
    # Georgia
    ("cityofatlanta",    "Georgia",        "Atlanta"),
    ("cityofsavannah",   "Georgia",        "Savannah"),
    ("cityofcolumbus",   "Georgia",        "Columbus"),
    ("cityofmacon",      "Georgia",        "Macon"),
    ("cityofathens",     "Georgia",        "Athens"),
    # North Carolina
    ("cityofcharlotte",  "North Carolina", "Charlotte"),
    ("cityofraleigh",    "North Carolina", "Raleigh"),
    ("cityofdurham",     "North Carolina", "Durham"),
    ("cityofgreensboro", "North Carolina", "Greensboro"),
    ("cityofwinstonsalem","North Carolina","Winston-Salem"),
    ("townofcary",       "North Carolina", "Cary"),
    ("cityofasheville",  "North Carolina", "Asheville"),
    ("cityofwilmington", "North Carolina", "Wilmington"),
    # Virginia
    ("cityofvirginiabeach","Virginia",     "Virginia Beach"),
    ("cityofnorfolk",    "Virginia",       "Norfolk"),
    ("cityofchesapeake", "Virginia",       "Chesapeake"),
    ("cityofrichmond",   "Virginia",       "Richmond"),
    ("cityofalexandria", "Virginia",       "Alexandria"),
    ("cityofhampton",    "Virginia",       "Hampton"),
    ("cityofroanoke",    "Virginia",       "Roanoke"),
    # Pennsylvania
    ("cityofphiladelphia","Pennsylvania",  "Philadelphia"),
    ("cityofpittsburgh", "Pennsylvania",   "Pittsburgh"),
    ("cityofallentown",  "Pennsylvania",   "Allentown"),
    ("cityoferie",       "Pennsylvania",   "Erie"),
    ("cityofscranton",   "Pennsylvania",   "Scranton"),
    # Michigan
    ("cityofdetroit",    "Michigan",       "Detroit"),
    ("cityofgrandrapids","Michigan",       "Grand Rapids"),
    ("cityoflansing",    "Michigan",       "Lansing"),
    ("cityofannarbor",   "Michigan",       "Ann Arbor"),
    ("cityofflint",      "Michigan",       "Flint"),
    ("cityofwarren",     "Michigan",       "Warren"),
    # Illinois
    ("cityofchicago",    "Illinois",       "Chicago"),
    ("cityofaurora",     "Illinois",       "Aurora"),
    ("cityofjoliet",     "Illinois",       "Joliet"),
    ("cityofrockford",   "Illinois",       "Rockford"),
    ("cityofspringfield","Illinois",       "Springfield"),
    ("cityofelgin",      "Illinois",       "Elgin"),
    ("cityofpeoria",     "Illinois",       "Peoria"),
    ("cityofnaperville", "Illinois",       "Naperville"),
    ("cityofwaukegan",   "Illinois",       "Waukegan"),
    # Massachusetts
    ("cityofboston",     "Massachusetts",  "Boston"),
    ("cityofworcester",  "Massachusetts",  "Worcester"),
    ("cityofcambridge",  "Massachusetts",  "Cambridge"),
    ("cityoflowell",     "Massachusetts",  "Lowell"),
    ("cityofspringfield","Massachusetts",  "Springfield"),
    ("cityofnewbedford", "Massachusetts",  "New Bedford"),
    # Arizona
    ("cityofphoenix",    "Arizona",        "Phoenix"),
    ("cityoftucson",     "Arizona",        "Tucson"),
    ("cityofmesa",       "Arizona",        "Mesa"),
    ("cityofchandler",   "Arizona",        "Chandler"),
    ("cityofscottsdale", "Arizona",        "Scottsdale"),
    ("townofgilbert",    "Arizona",        "Gilbert"),
    ("cityoftempe",      "Arizona",        "Tempe"),
    ("cityofglendale",   "Arizona",        "Glendale"),
    ("cityofflagstaff",  "Arizona",        "Flagstaff"),
    ("cityofyuma",       "Arizona",        "Yuma"),
    ("cityofprescott",   "Arizona",        "Prescott"),
    ("cityofsurprise",   "Arizona",        "Surprise"),
    ("cityofgoodyear",   "Arizona",        "Goodyear"),
    # Washington
    ("cityofseattle",    "Washington",     "Seattle"),
    ("cityofspokane",    "Washington",     "Spokane"),
    ("cityoftacoma",     "Washington",     "Tacoma"),
    ("cityofvancouver",  "Washington",     "Vancouver"),
    ("cityofbellevue",   "Washington",     "Bellevue"),
    ("cityofeverett",    "Washington",     "Everett"),
    ("cityofrenton",     "Washington",     "Renton"),
    ("cityofkirkland",   "Washington",     "Kirkland"),
    ("cityofkent",       "Washington",     "Kent"),
    ("cityofbellingham", "Washington",     "Bellingham"),
    ("cityofyakima",     "Washington",     "Yakima"),
    ("cityofolympia",    "Washington",     "Olympia"),
    ("cityofredmond",    "Washington",     "Redmond"),
    # Colorado
    ("cityofdenver",     "Colorado",       "Denver"),
    ("cityofaurora",     "Colorado",       "Aurora"),
    ("cityoffortcollins","Colorado",       "Fort Collins"),
    ("cityoflakewood",   "Colorado",       "Lakewood"),
    ("cityofthornton",   "Colorado",       "Thornton"),
    ("cityofarvada",     "Colorado",       "Arvada"),
    ("cityofwestminster","Colorado",       "Westminster"),
    ("cityofpueblo",     "Colorado",       "Pueblo"),
    ("cityofboulder",    "Colorado",       "Boulder"),
    ("cityofgreeley",    "Colorado",       "Greeley"),
    ("cityoflongmont",   "Colorado",       "Longmont"),
    ("cityofloveland",   "Colorado",       "Loveland"),
    # County slugs
    ("losangelescounty", "California",     "Los Angeles County"),
    ("sandiegocounty",   "California",     "San Diego County"),
    ("orangecounty",     "California",     "Orange County"),
    ("riversidecounty",  "California",     "Riverside County"),
    ("contracostacounty","California",     "Contra Costa County"),
    ("alamedacounty",    "California",     "Alameda County"),
    ("santaclaracounty", "California",     "Santa Clara County"),
    ("sacramentocounty", "California",     "Sacramento County"),
    ("dallasfcount",     "Texas",          "Dallas County"),
    ("harriscounty",     "Texas",          "Harris County"),
    ("traviscounty",     "Texas",          "Travis County"),
    ("bexarcounty",      "Texas",          "Bexar County"),
    ("tarrantcounty",    "Texas",          "Tarrant County"),
    ("collincounty",     "Texas",          "Collin County"),
    ("dallascounty",     "Texas",          "Dallas County"),
    ("fortbend",         "Texas",          "Fort Bend County"),
    ("browardcounty",    "Florida",        "Broward County"),
    ("palmbeachcounty",  "Florida",        "Palm Beach County"),
    ("miamidadecounty",  "Florida",        "Miami-Dade County"),
    ("hillsboroughcounty","Florida",       "Hillsborough County"),
    ("pinellascounty",   "Florida",        "Pinellas County"),
    ("wakecounty",       "North Carolina", "Wake County"),
    ("mecklenburgcounty","North Carolina", "Mecklenburg County"),
    ("guildfordcounty",  "North Carolina", "Guilford County"),
    ("forsythcounty",    "North Carolina", "Forsyth County"),
    ("cumberlandcounty", "North Carolina", "Cumberland County"),
    ("fultoncounty",     "Georgia",        "Fulton County"),
    ("gwinnetcounty",    "Georgia",        "Gwinnett County"),
    ("dekalbcounty",     "Georgia",        "DeKalb County"),
    ("cobbcounty",       "Georgia",        "Cobb County"),
    ("chathamcounty",    "Georgia",        "Chatham County"),
    ("fairfaxcounty",    "Virginia",       "Fairfax County"),
    ("loudouncounty",    "Virginia",       "Loudoun County"),
    ("princewilliam",    "Virginia",       "Prince William County"),
    ("chesterfieldcounty","Virginia",      "Chesterfield County"),
    ("maricopacounty",   "Arizona",        "Maricopa County"),
    ("pimacounty",       "Arizona",        "Pima County"),
    ("kingcounty",       "Washington",     "King County"),
    ("clarkcountynv",    "Nevada",         "Clark County"),
    ("washoecounty",     "Nevada",         "Washoe County"),
    ("cookcounty",       "Illinois",       "Cook County"),
    ("dupagecounty",     "Illinois",       "DuPage County"),
    ("willcounty",       "Illinois",       "Will County"),
    ("kanecounty",       "Illinois",       "Kane County"),
    ("hennepincounty",   "Minnesota",      "Hennepin County"),
    ("ramseycounty",     "Minnesota",      "Ramsey County"),
    ("milwaukeecounty",  "Wisconsin",      "Milwaukee County"),
    ("danecounty",       "Wisconsin",      "Dane County"),
    ("allegheny",        "Pennsylvania",   "Allegheny County"),
    ("philadelphiacounty","Pennsylvania",  "Philadelphia County"),
    ("franklincounty",   "Ohio",           "Franklin County"),
    ("cuyahogacounty",   "Ohio",           "Cuyahoga County"),
    ("hamiltoncountyoh", "Ohio",           "Hamilton County"),
    ("baltimorecounty",  "Maryland",       "Baltimore County"),
    ("montgomerycountymd","Maryland",      "Montgomery County"),
    ("suffolkcountyny",  "New York",       "Suffolk County"),
    ("nassaucountyny",   "New York",       "Nassau County"),
    ("westchestercounty","New York",       "Westchester County"),
    ("ericountyny",      "New York",       "Erie County"),
    ("monroecountyny",   "New York",       "Monroe County"),
    ("middlesexcounty",  "Massachusetts",  "Middlesex County"),
    # Regional agencies
    ("lametro",          "California",     "LA Metro"),
    ("scag",             "California",     "SCAG"),
    ("sandag",           "California",     "SANDAG"),
    ("sacog",            "California",     "SACOG"),
    ("abag",             "California",     "ABAG"),
    ("sfcta",            "California",     "SFCTA"),
    ("mwrd",             "Illinois",       "MWRD"),
    ("rtd",              "Colorado",       "RTD Denver"),
    ("metro",            "Oregon",         "Metro Portland"),
    ("sound-transit",    "Washington",     "Sound Transit"),
    ("soundtransit",     "Washington",     "Sound Transit"),
    ("translink",        "Washington",     "TransLink"),
    ("nctcog",           "Texas",          "NCTCOG"),
    ("campo",            "Texas",          "CAMPO"),
    ("hgac",             "Texas",          "HGAC"),
    ("alamo",            "Texas",          "Alamo Area MPO"),
    ("capmetro",         "Texas",          "Capital Metro"),
    ("trimet",           "Oregon",         "TriMet"),
    ("valleymetro",      "Arizona",        "Valley Metro"),
    ("sunline",          "California",     "SunLine Transit"),
    ("octa",             "California",     "OCTA"),
    ("mts",              "California",     "MTS San Diego"),
    ("vta",              "California",     "VTA"),
    ("ac-transit",       "California",     "AC Transit"),
    ("samtrans",         "California",     "SamTrans"),
    ("caltrain",         "California",     "Caltrain"),
    ("lacmta",           "California",     "LACMTA"),
    ("metro-nashville",  "Tennessee",      "Nashville Metro"),
    ("nashvillemetro",   "Tennessee",      "Nashville Metro"),
    ("unifiedgovernment","Kansas",         "Unified Government WyCo"),
    ("louisvillemetro",  "Kentucky",       "Louisville Metro"),
    ("lexingtonky",      "Kentucky",       "Lexington-Fayette"),
    ("jacksonvillefl",   "Florida",        "Jacksonville"),
    ("consolidatedgov",  "Georgia",        "Columbus Consolidated"),
    ("augustaga",        "Georgia",        "Augusta-Richmond"),
]

CANDIDATES += EXTRA

def test_slug(args):
    slug, state, name = args
    if slug in existing:
        return None
    url = f"https://webapi.legistar.com/v1/{slug}/Events?$top=1"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200 and len(r.content) > 50:
            ct = r.headers.get("Content-Type", "")
            if "json" in ct or "xml" in ct:
                return (slug, state, name)
        return None
    except Exception:
        return None

# Deduplicate
seen = set()
unique = []
for c in CANDIDATES:
    if c[0] not in seen and c[0] not in existing:
        seen.add(c[0])
        unique.append(c)

print()
print(Fore.CYAN + "="*60)
print(Fore.CYAN + f"  Second pass slug discovery")
print(Fore.CYAN + f"  Testing {len(unique)} new candidates (20 parallel)")
print(Fore.CYAN + "="*60)
print()

found = []
with ThreadPoolExecutor(max_workers=20) as ex:
    futures = {ex.submit(test_slug, c): c for c in unique}
    done = 0
    for future in as_completed(futures):
        done += 1
        result = future.result()
        if result:
            slug, state, name = result
            found.append(result)
            print(Fore.GREEN + f"  FOUND  {slug:35s} ({name}, {state})")
        if done % 100 == 0:
            pct = done / len(unique) * 100
            print(Fore.CYAN + f"  {done}/{len(unique)} ({pct:.0f}%) — {len(found)} found")

print()
print(Fore.CYAN + "="*60)
print(Fore.GREEN + f"  Found {len(found)} new slugs!")
print(Fore.CYAN + "="*60)

if found:
    with open("scrapers/legistar.py", "r") as f:
        content = f.read()

    additions = "\n    # Second-pass discovered slugs\n"
    for slug, state, name in sorted(found, key=lambda x: x[1]):
        line = f'    "{slug}":{" "*(25-len(slug))}("{state}", "{name}"),\n'
        if f'"{slug}"' not in content:
            additions += line

    content = content.replace(
        "}\n\n# ── Lookup",
        additions + "}\n\n# ── Lookup"
    )
    with open("scrapers/legistar.py", "w") as f:
        f.write(content)

    print(Fore.GREEN + f"  Auto-added to scrapers/legistar.py")

print()
