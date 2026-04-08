"""
scrapers/boarddocs.py — BoardDocs scraper.

BoardDocs is used by hundreds of counties, school boards,
and special districts.

URL: https://go.boarddocs.com/{state}/{entity}/Board.nsf/Public
API: https://go.boarddocs.com/{state}/{entity}/Board.nsf/BD-GetMeetingsList?open&format=json
"""

import requests, re
from datetime import date, datetime
from utils import classify_body, is_future_or_today, parse_date, date_str, download_packet
from constants import HEADERS, REQUEST_TIMEOUT

BOARDDOCS_ENTITIES = [
    # Format: (state_code, entity_code, state, municipality)
    # California
    ("ca", "ca-sacramento-county",  "California",    "Sacramento County"),
    ("ca", "ca-san-bernardino",     "California",    "San Bernardino County"),
    ("ca", "ca-ventura-county",     "California",    "Ventura County"),
    ("ca", "ca-santa-cruz",         "California",    "Santa Cruz County"),
    ("ca", "ca-monterey",           "California",    "Monterey County"),
    ("ca", "ca-san-luis-obispo",    "California",    "San Luis Obispo County"),
    ("ca", "ca-napa-county",        "California",    "Napa County"),
    ("ca", "ca-sonoma-county",      "California",    "Sonoma County"),
    ("ca", "ca-marin",              "California",    "Marin County"),
    ("ca", "ca-placer",             "California",    "Placer County"),
    # Texas
    ("tx", "tx-travis-county",      "Texas",         "Travis County"),
    ("tx", "tx-williamson",         "Texas",         "Williamson County"),
    ("tx", "tx-comal",              "Texas",         "Comal County"),
    ("tx", "tx-hays",               "Texas",         "Hays County"),
    ("tx", "tx-bastrop",            "Texas",         "Bastrop County"),
    ("tx", "tx-bell",               "Texas",         "Bell County"),
    ("tx", "tx-brazoria",           "Texas",         "Brazoria County"),
    ("tx", "tx-galveston",          "Texas",         "Galveston County"),
    ("tx", "tx-fort-bend",          "Texas",         "Fort Bend County"),
    ("tx", "tx-montgomery-tx",      "Texas",         "Montgomery County"),
    # Florida
    ("fl", "fl-palm-beach-county",  "Florida",       "Palm Beach County"),
    ("fl", "fl-pasco",              "Florida",       "Pasco County"),
    ("fl", "fl-polk",               "Florida",       "Polk County"),
    ("fl", "fl-volusia",            "Florida",       "Volusia County"),
    ("fl", "fl-manatee",            "Florida",       "Manatee County"),
    ("fl", "fl-sarasota-county",    "Florida",       "Sarasota County"),
    ("fl", "fl-seminole",           "Florida",       "Seminole County"),
    ("fl", "fl-osceola",            "Florida",       "Osceola County"),
    ("fl", "fl-lake-county",        "Florida",       "Lake County"),
    # Georgia
    ("ga", "ga-cherokee",           "Georgia",       "Cherokee County"),
    ("ga", "ga-henry",              "Georgia",       "Henry County"),
    ("ga", "ga-forsyth",            "Georgia",       "Forsyth County"),
    ("ga", "ga-hall",               "Georgia",       "Hall County"),
    ("ga", "ga-bartow",             "Georgia",       "Bartow County"),
    ("ga", "ga-columbia",           "Georgia",       "Columbia County"),
    # North Carolina
    ("nc", "nc-union",              "North Carolina","Union County"),
    ("nc", "nc-cabarrus",           "North Carolina","Cabarrus County"),
    ("nc", "nc-iredell",            "North Carolina","Iredell County"),
    ("nc", "nc-rowan",              "North Carolina","Rowan County"),
    ("nc", "nc-davidson",           "North Carolina","Davidson County"),
    ("nc", "nc-alamance",           "North Carolina","Alamance County"),
    ("nc", "nc-henderson",          "North Carolina","Henderson County"),
    ("nc", "nc-new-hanover",        "North Carolina","New Hanover County"),
    ("nc", "nc-brunswick",          "North Carolina","Brunswick County"),
    # Virginia
    ("va", "va-prince-william",     "Virginia",      "Prince William County"),
    ("va", "va-chesterfield",       "Virginia",      "Chesterfield County"),
    ("va", "va-spotsylvania",       "Virginia",      "Spotsylvania County"),
    ("va", "va-stafford",           "Virginia",      "Stafford County"),
    ("va", "va-fauquier",           "Virginia",      "Fauquier County"),
    ("va", "va-augusta",            "Virginia",      "Augusta County"),
    ("va", "va-rockingham",         "Virginia",      "Rockingham County"),
    # Washington
    ("wa", "wa-clark",              "Washington",    "Clark County"),
    ("wa", "wa-thurston",           "Washington",    "Thurston County"),
    ("wa", "wa-whatcom",            "Washington",    "Whatcom County"),
    ("wa", "wa-skagit",             "Washington",    "Skagit County"),
    ("wa", "wa-benton",             "Washington",    "Benton County"),
    ("wa", "wa-yakima-county",      "Washington",    "Yakima County"),
    # Arizona
    ("az", "az-pinal",              "Arizona",       "Pinal County"),
    ("az", "az-yavapai",            "Arizona",       "Yavapai County"),
    ("az", "az-mohave",             "Arizona",       "Mohave County"),
    ("az", "az-coconino",           "Arizona",       "Coconino County"),
    ("az", "az-navajo",             "Arizona",       "Navajo County"),
    # Colorado
    ("co", "co-el-paso",            "Colorado",      "El Paso County"),
    ("co", "co-larimer",            "Colorado",      "Larimer County"),
    ("co", "co-weld",               "Colorado",      "Weld County"),
    ("co", "co-boulder-county",     "Colorado",      "Boulder County"),
    ("co", "co-douglas",            "Colorado",      "Douglas County"),
    # Ohio
    ("oh", "oh-butler",             "Ohio",          "Butler County"),
    ("oh", "oh-warren",             "Ohio",          "Warren County"),
    ("oh", "oh-licking",            "Ohio",          "Licking County"),
    ("oh", "oh-fairfield",          "Ohio",          "Fairfield County"),
    ("oh", "oh-delaware",           "Ohio",          "Delaware County"),
    ("oh", "oh-medina",             "Ohio",          "Medina County"),
    ("oh", "oh-lorain-county",      "Ohio",          "Lorain County"),
    ("oh", "oh-lake",               "Ohio",          "Lake County"),
    # Michigan
    ("mi", "mi-ottawa",             "Michigan",      "Ottawa County"),
    ("mi", "mi-washtenaw",          "Michigan",      "Washtenaw County"),
    ("mi", "mi-ingham",             "Michigan",      "Ingham County"),
    ("mi", "mi-kalamazoo-county",   "Michigan",      "Kalamazoo County"),
    ("mi", "mi-genesee",            "Michigan",      "Genesee County"),
    # Illinois
    ("il", "il-will",               "Illinois",      "Will County"),
    ("il", "il-lake-il",            "Illinois",      "Lake County"),
    ("il", "il-kane",               "Illinois",      "Kane County"),
    ("il", "il-mchenry",            "Illinois",      "McHenry County"),
    ("il", "il-winnebago",          "Illinois",      "Winnebago County"),
    ("il", "il-champaign-county",   "Illinois",      "Champaign County"),
    ("il", "il-madison",            "Illinois",      "Madison County"),
    ("il", "il-st-clair",           "Illinois",      "St. Clair County"),
    # Pennsylvania
    ("pa", "pa-chester",            "Pennsylvania",  "Chester County"),
    ("pa", "pa-york",               "Pennsylvania",  "York County"),
    ("pa", "pa-cumberland",         "Pennsylvania",  "Cumberland County"),
    ("pa", "pa-berks",              "Pennsylvania",  "Berks County"),
    ("pa", "pa-lancaster-county",   "Pennsylvania",  "Lancaster County"),
    ("pa", "pa-luzerne",            "Pennsylvania",  "Luzerne County"),
    ("pa", "pa-northampton",        "Pennsylvania",  "Northampton County"),
    # New Jersey
    ("nj", "nj-burlington",         "New Jersey",    "Burlington County"),
    ("nj", "nj-gloucester",         "New Jersey",    "Gloucester County"),
    ("nj", "nj-camden-county",      "New Jersey",    "Camden County"),
    ("nj", "nj-atlantic",           "New Jersey",    "Atlantic County"),
    ("nj", "nj-monmouth",           "New Jersey",    "Monmouth County"),
    ("nj", "nj-somerset",           "New Jersey",    "Somerset County"),
    ("nj", "nj-hunterdon",          "New Jersey",    "Hunterdon County"),
    # Maryland
    ("md", "md-frederick",          "Maryland",      "Frederick County"),
    ("md", "md-carroll",            "Maryland",      "Carroll County"),
    ("md", "md-washington-md",      "Maryland",      "Washington County"),
    ("md", "md-st-marys",           "Maryland",      "St. Mary's County"),
    ("md", "md-calvert",            "Maryland",      "Calvert County"),
    # Tennessee
    ("tn", "tn-williamson",         "Tennessee",     "Williamson County"),
    ("tn", "tn-rutherford",         "Tennessee",     "Rutherford County"),
    ("tn", "tn-montgomery-tn",      "Tennessee",     "Montgomery County"),
    ("tn", "tn-sumner",             "Tennessee",     "Sumner County"),
    ("tn", "tn-wilson",             "Tennessee",     "Wilson County"),
    # Indiana
    ("in", "in-hamilton-in",        "Indiana",       "Hamilton County"),
    ("in", "in-hendricks",          "Indiana",       "Hendricks County"),
    ("in", "in-johnson-in",         "Indiana",       "Johnson County"),
    ("in", "in-madison-in",         "Indiana",       "Madison County"),
    ("in", "in-delaware-in",        "Indiana",       "Delaware County"),
    # South Carolina
    ("sc", "sc-york",               "South Carolina","York County"),
    ("sc", "sc-berkeley",           "South Carolina","Berkeley County"),
    ("sc", "sc-dorchester",         "South Carolina","Dorchester County"),
    ("sc", "sc-lexington",          "South Carolina","Lexington County"),
    ("sc", "sc-horry",              "South Carolina","Horry County"),
    ("sc", "sc-beaufort",           "South Carolina","Beaufort County"),
    # Alabama
    ("al", "al-shelby",             "Alabama",       "Shelby County"),
    ("al", "al-st-clair-al",        "Alabama",       "St. Clair County"),
    ("al", "al-limestone",          "Alabama",       "Limestone County"),
    ("al", "al-baldwin",            "Alabama",       "Baldwin County"),
    # Utah
    ("ut", "ut-utah-county",        "Utah",          "Utah County"),
    ("ut", "ut-davis",              "Utah",          "Davis County"),
    ("ut", "ut-weber",              "Utah",          "Weber County"),
    ("ut", "ut-washington-ut",      "Utah",          "Washington County"),
    # Kansas
    ("ks", "ks-douglas",            "Kansas",        "Douglas County"),
    ("ks", "ks-riley",              "Kansas",        "Riley County"),
    ("ks", "ks-leavenworth",        "Kansas",        "Leavenworth County"),
    # Iowa
    ("ia", "ia-johnson-ia",         "Iowa",          "Johnson County"),
    ("ia", "ia-linn",               "Iowa",          "Linn County"),
    ("ia", "ia-scott",              "Iowa",          "Scott County"),
    ("ia", "ia-black-hawk",         "Iowa",          "Black Hawk County"),
    # Oregon
    ("or", "or-clackamas",          "Oregon",        "Clackamas County"),
    ("or", "or-marion",             "Oregon",        "Marion County"),
    ("or", "or-jackson",            "Oregon",        "Jackson County"),
    ("or", "or-linn-or",            "Oregon",        "Linn County"),
    ("or", "or-deschutes",          "Oregon",        "Deschutes County"),
    # Idaho
    ("id", "id-canyon",             "Idaho",         "Canyon County"),
    ("id", "id-bonneville",         "Idaho",         "Bonneville County"),
    ("id", "id-twin-falls",         "Idaho",         "Twin Falls County"),
    # Nevada
    ("nv", "nv-washoe-county",      "Nevada",        "Washoe County"),
    ("nv", "nv-lyon",               "Nevada",        "Lyon County"),
    # New Mexico
    ("nm", "nm-dona-ana",           "New Mexico",    "Doña Ana County"),
    ("nm", "nm-sandoval",           "New Mexico",    "Sandoval County"),
    ("nm", "nm-santa-fe-county",    "New Mexico",    "Santa Fe County"),
    # Montana
    ("mt", "mt-yellowstone",        "Montana",       "Yellowstone County"),
    ("mt", "mt-cascade",            "Montana",       "Cascade County"),
    ("mt", "mt-gallatin",           "Montana",       "Gallatin County"),
    # Minnesota
    ("mn", "mn-washington-mn",      "Minnesota",     "Washington County"),
    ("mn", "mn-scott",              "Minnesota",     "Scott County"),
    ("mn", "mn-carver",             "Minnesota",     "Carver County"),
    ("mn", "mn-wright-mn",          "Minnesota",     "Wright County"),
    ("mn", "mn-sherburne",          "Minnesota",     "Sherburne County"),
    # Wisconsin
    ("wi", "wi-waukesha-county",    "Wisconsin",     "Waukesha County"),
    ("wi", "wi-ozaukee",            "Wisconsin",     "Ozaukee County"),
    ("wi", "wi-washington-wi",      "Wisconsin",     "Washington County"),
    ("wi", "wi-brown",              "Wisconsin",     "Brown County"),
    ("wi", "wi-outagamie",          "Wisconsin",     "Outagamie County"),
]

BOARDDOCS_API = "https://go.boarddocs.com/{state}/{entity}/Board.nsf/BD-GetMeetingsList?open&format=json"
BOARDDOCS_BASE = "https://go.boarddocs.com/{state}/{entity}/Board.nsf/Public"


def scrape_boarddocs(state: str, collected: list, max_packets: int) -> int:
    """Scrape BoardDocs for a given state."""
    entities = [(sc, ec, st, mn) for sc, ec, st, mn in BOARDDOCS_ENTITIES
                if st == state]
    if not entities:
        return 0

    added = 0
    today = date.today()

    for state_code, entity_code, st, municipality in entities:
        if len(collected) >= max_packets:
            break

        api_url = BOARDDOCS_API.format(state=state_code, entity=entity_code)
        try:
            r = requests.get(api_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                continue
            data = r.json()
        except Exception:
            continue

        meetings = data if isinstance(data, list) else data.get("meetings", [])

        for meeting in meetings:
            if len(collected) >= max_packets:
                break

            try:
                # Get date
                date_str_raw = meeting.get("date", "") or meeting.get("meeting_date", "")
                if not date_str_raw:
                    continue
                meeting_date = parse_date(date_str_raw)
                if not is_future_or_today(meeting_date):
                    continue

                # Get body name
                body_name = (meeting.get("name", "") or
                             meeting.get("board_name", "") or
                             municipality)
                body_type = classify_body(body_name)
                if not body_type:
                    body_type = classify_body(municipality + " council")

                # Get agenda URL
                unique_id = meeting.get("unique", "") or meeting.get("id", "")
                if not unique_id:
                    continue

                agenda_url = (f"https://go.boarddocs.com/{state_code}/{entity_code}"
                              f"/Board.nsf/goto?open&id={unique_id}")

                dl = download_packet(agenda_url, st, municipality,
                                     body_type or "advisory_board",
                                     date_str(meeting_date))
                if not dl or dl.get("failed"):
                    continue

                collected.append({
                    "state": st, "municipality": municipality,
                    "place_type": "county", "body_name": body_name,
                    "body_type": body_type or "advisory_board",
                    "meeting_date": date_str(meeting_date),
                    "meeting_time": "", "location": "",
                    "source_url": BOARDDOCS_BASE.format(
                        state=state_code, entity=entity_code),
                    "platform": "BoardDocs",
                    **dl,
                })
                added += 1
            except Exception:
                continue

    return added
