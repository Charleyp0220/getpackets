"""
scrapers/custom_sites.py — scraper for custom government websites
that don't use Legistar, CivicPlus, or PrimeGov.

Each entry has a direct URL to the planning/zoning agenda page.
The scraper fetches the page and finds PDF links.
"""

import requests, re
from datetime import date
from bs4 import BeautifulSoup
from utils import (classify_body, is_future_or_today, parse_date,
                   date_str, download_packet)
from constants import HEADERS, REQUEST_TIMEOUT

# Direct planning/zoning agenda URLs
# Format: (state, municipality, place_type, agenda_url)
CUSTOM_SITES = [
    # Tennessee
    ("Tennessee",      "Knoxville",           "city",    "https://www.knoxvilletn.gov/government/boards_commissions/board_of_zoning_appeals/agendas__minutes___packets"),
    ("Tennessee",      "Knoxville Planning",  "city",    "https://knoxplanning.org/agenda/"),

    # Maryland
    ("Maryland",       "St. Michaels",        "town",    "https://www.stmichaelsmd.gov/planning-zoning"),
    ("Maryland",       "Easton",              "town",    "https://www.eastonmd.gov/agendas-minutes"),
    ("Maryland",       "Washington County",   "county",  "https://www.washco-md.net/planning-zoning/board-of-zoning-appeals/"),

    # Missouri
    ("Missouri",       "Chesterfield",        "city",    "https://www.chesterfield.mo.us/planning-zoning.html"),
    ("Missouri",       "Raytown",             "city",    "https://www.cityofraytown.mo.us/AgendaCenter"),
    ("Missouri",       "Pacific",             "city",    "https://www.pacificmo.gov/agendas"),
    ("Missouri",       "Harrisonville",       "city",    "https://www.cityofharrisonville.com/agendas"),

    # Oregon
    ("Oregon",         "Cannon Beach",        "city",    "https://ci.cannon-beach.or.us/planning"),
    ("Oregon",         "Albany",              "city",    "https://www.albanyoregon.gov/planning/agendas-minutes"),
    ("Oregon",         "McMinnville",         "city",    "https://www.mcminnvilleoregon.gov/planning"),
    ("Oregon",         "Scappoose",           "city",    "https://www.scappoose.gov/agendas"),
    ("Oregon",         "Dallas",              "city",    "https://www.dallasor.gov/agendas"),
    ("Oregon",         "Morrow County",       "county",  "https://www.co.morrow.or.us/planning"),

    # Wisconsin
    ("Wisconsin",      "De Pere",             "city",    "https://www.deperewi.gov/AgendaCenter"),
    ("Wisconsin",      "Richfield",           "township","https://www.richfieldwi.gov/agendas"),
    ("Wisconsin",      "Waupaca County",      "county",  "https://www.waupacacounty.com/planning"),
    ("Wisconsin",      "Merrill",             "city",    "https://www.ci.merrill.wi.us/agendas"),
    ("Wisconsin",      "Vinland Township",    "township","https://www.townofvinlandwi.gov/agendas"),
    ("Wisconsin",      "Williams Bay",        "village", "https://www.williamsbay.org/agendas"),

    # New York
    ("New York",       "Lewisboro",           "town",    "https://www.lewisborony.gov/planning"),
    ("New York",       "Port Chester",        "village", "https://www.portchesterny.gov/AgendaCenter"),

    # Nebraska
    ("Nebraska",       "Norfolk",             "city",    "https://www.norfolkne.gov/agendas"),

    # Utah
    ("Utah",           "St. George",          "city",    "https://www.sgcityutah.gov/agendas"),
    ("Utah",           "Park City",           "city",    "https://www.parkcity.org/agendas"),

    # Virginia
    ("Virginia",       "Williamsburg",        "city",    "https://www.williamsburgva.gov/agendas"),
    ("Virginia",       "Stafford County",     "county",  "https://www.staffordcountyva.gov/agendas"),
    ("Virginia",       "Pittsylvania County", "county",  "https://www.pittsylvaniacountyva.gov/agendas"),
    ("Virginia",       "Isle of Wight",       "county",  "https://www.isleofwightus.net/planning"),
    ("Virginia",       "Frederick County",    "county",  "https://www.fcva.us/agendas"),

    # North Carolina
    ("North Carolina", "Wake Forest",         "town",    "https://www.wakeforestnc.gov/agendas"),
    ("North Carolina", "Pender County",       "county",  "https://www.pendercountync.gov/planning"),
    ("North Carolina", "Carteret County",     "county",  "https://www.carteretcountync.gov/agendas"),
    ("North Carolina", "Cumberland County",   "county",  "https://www.cumberlandcountync.gov/agendas"),
    ("North Carolina", "Clayton",             "town",    "https://www.townofclayton.org/agendas"),
    ("North Carolina", "Anson County",        "county",  "https://www.ansoncountync.gov/agendas"),
    ("North Carolina", "Durham",              "city",    "https://www.durhamnc.gov/agendas"),

    # South Carolina
    ("South Carolina", "Kershaw County",      "county",  "https://www.kershaw.sc.gov/agendas"),
    ("South Carolina", "Ridgeland",           "town",    "https://www.ridgelandsc.gov/agendas"),
    ("South Carolina", "Anderson County",     "county",  "https://www.andersoncountysc.org/agendas"),
    ("South Carolina", "Hanahan",             "city",    "https://www.cityofhanahan.com/agendas"),

    # Georgia
    ("Georgia",        "Cartersville",        "city",    "https://www.cityofcartersville.org/agendas"),
    ("Georgia",        "Fayette County",      "county",  "https://www.fayettecountyga.gov/agendas"),
    ("Georgia",        "Carroll County",      "county",  "https://www.carrollcountyga.gov/agendas"),
    ("Georgia",        "Douglas County",      "county",  "https://www.douglascountyga.gov/agendas"),
    ("Georgia",        "Hall County",         "county",  "https://www.hallcounty.org/agendas"),
    ("Georgia",        "Coweta County",       "county",  "https://www.coweta.ga.us/agendas"),
    ("Georgia",        "Paulding County",     "county",  "https://www.paulding.gov/agendas"),
    ("Georgia",        "Mableton",            "city",    "https://www.mableton.gov/agendas"),
    ("Georgia",        "Daccula",             "city",    "https://www.daculaga.gov/agendas"),
    ("Georgia",        "Newnan",              "city",    "https://www.newnanga.gov/agendas"),
    ("Georgia",        "Peachtree City",      "city",    "https://www.peachtree-city.org/agendas"),
    ("Georgia",        "Putnam County",       "county",  "https://www.putnamcountygeorgia.com/agendas"),

    # Florida
    ("Florida",        "Martin County",       "county",  "https://www.martin.fl.us/agendas"),
    ("Florida",        "Belle Isle",          "city",    "https://www.belleislefl.gov/agendas"),
    ("Florida",        "Cape Coral",          "city",    "https://www.capecoral.gov/agendas"),
    ("Florida",        "Ocean Ridge",         "town",    "https://www.oceanridge.gov/agendas"),
    ("Florida",        "Titusville",          "city",    "https://www.titusville.com/agendas"),
    ("Florida",        "Fruitland Park",      "city",    "https://www.fruitlandpark.org/agendas"),
    ("Florida",        "Hernando County",     "county",  "https://www.hernandocountyfl.gov/agendas"),
    ("Florida",        "St. Pete Beach",      "city",    "https://www.stpetebeach.org/agendas"),
    ("Florida",        "Ocean Springs",       "city",    "https://www.oceansprings-ms.gov/agendas"),
    ("Florida",        "Orange Beach",        "city",    "https://www.orangebeachal.gov/agendas"),

    # Minnesota
    ("Minnesota",      "Mille Lacs County",   "county",  "https://www.millelacs.mn.gov/agendas"),
    ("Minnesota",      "Wright County",       "county",  "https://www.co.wright.mn.us/agendas"),
    ("Minnesota",      "Breezy Point",        "city",    "https://www.breezypointmn.gov/agendas"),
    ("Minnesota",      "Pine Island",         "city",    "https://www.pineislandmn.gov/agendas"),
    ("Minnesota",      "La Crescent",         "city",    "https://www.cityoflacrescent-mn.gov/agendas"),

    # Illinois
    ("Illinois",       "Mahomet",             "village", "https://www.mahomet-il.gov/agendas"),
    ("Illinois",       "Morton Grove",        "village", "https://www.mortongroveil.org/agendas"),
    ("Illinois",       "Mount Prospect",      "village", "https://www.mountprospect.org/agendas"),
    ("Illinois",       "Homewood",            "village", "https://www.village.homewood.il.us/agendas"),
    ("Illinois",       "McHenry County",      "county",  "https://www.mchenrycountyil.gov/agendas"),

    # Massachusetts
    ("Massachusetts",  "Grafton",             "town",    "https://www.grafton-ma.gov/agendas"),
    ("Massachusetts",  "Watertown",           "city",    "https://www.watertown-ma.gov/agendas"),

    # New Mexico
    ("New Mexico",     "Roswell",             "city",    "https://www.roswell-nm.gov/agendas"),
    ("New Mexico",     "Corrales",            "village", "https://www.corrales-nm.org/agendas"),
    ("New Mexico",     "Rio Rancho",          "city",    "https://www.rrnm.gov/agendas"),

    # Arizona
    ("Arizona",        "Florence",            "town",    "https://www.florenceaz.gov/agendas"),
    ("Arizona",        "Chino Valley",        "town",    "https://www.chinoaz.net/agendas"),

    # Colorado
    ("Colorado",       "Newcastle",           "town",    "https://www.newcastlecolorado.org/agendas"),

    # Alabama
    ("Alabama",        "Enterprise",          "city",    "https://www.enterpriseal.gov/agendas"),
    ("Alabama",        "Fairhope",            "city",    "https://www.fairhopeal.gov/agendas"),

    # Arkansas
    ("Arkansas",       "Springdale",          "city",    "https://www.springdalear.gov/agendas"),

    # Mississippi
    ("Mississippi",    "Gluckstadt",          "city",    "https://www.gluckstadtms.gov/agendas"),
    ("Mississippi",    "Hattiesburg",         "city",    "https://www.hattiesburgms.com/agendas"),
    ("Mississippi",    "Ocean Springs",       "city",    "https://www.oceansprings-ms.gov/agendas"),

    # Hawaii
    ("Hawaii",         "Hawaii County",       "county",  "https://www.hawaiicounty.gov/agendas"),

    # Pennsylvania
    ("Pennsylvania",   "Pine Township",       "township","https://www.twp.pine.pa.us/agendas"),
    ("Pennsylvania",   "Howell Township",     "township","https://www.twp.howell.nj.us/agendas"),
    ("Pennsylvania",   "Westmoreland County", "county",  "https://www.co.westmoreland.pa.us/agendas"),
    ("Pennsylvania",   "West Whiteland",      "township","https://www.westwhiteland.org/agendas"),

    # Louisiana
    ("Louisiana",      "Ascension Parish",    "parish",  "https://www.ascensionparish.net/agendas"),

    # Idaho
    ("Idaho",          "Coeur d'Alene",       "city",    "https://www.cdaid.org/agendas"),

    # West Virginia
    ("West Virginia",  "Shepherdstown",       "town",    "https://www.shepherdstown.gov/agendas"),

    # Texas
    ("Texas",          "Tulsa",               "city",    "https://www.cityoftulsa.org/agendas"),
    ("Texas",          "McAllen",             "city",    "https://www.cityofmcallentx.com/agendas"),
    ("Texas",          "Eagle Pass",          "city",    "https://www.eaglepasstx.gov/agendas"),
    ("Texas",          "Joshua",              "city",    "https://www.cityofjoshua.com/agendas"),
    ("Texas",          "Jarrell",             "city",    "https://www.cityofjarrell.com/agendas"),
    ("Texas",          "Bartow",              "city",    "https://www.cityofbartow.net/agendas"),
    ("Texas",          "Sedgwick",            "city",    "https://www.cityofsedgwickks.com/agendas"),
]


def scrape_custom_sites(state: str, collected: list, max_packets: int) -> int:
    """Scrape custom government websites for the given state."""
    sites = [(st, muni, pt, url) for st, muni, pt, url in CUSTOM_SITES
             if st == state]
    if not sites:
        return 0

    added = 0
    today = date.today()

    for st, municipality, place_type, agenda_url in sites:
        if len(collected) >= max_packets:
            break

        try:
            r = requests.get(agenda_url, headers=HEADERS,
                           timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "lxml")
        except Exception:
            continue

        # Find all PDF links on the page
        for a in soup.find_all("a", href=True):
            if len(collected) >= max_packets:
                break

            href  = a["href"].strip()
            label = a.get_text(strip=True)

            # Must look like a PDF or agenda link
            if not any(x in href.lower() or x in label.lower()
                      for x in [".pdf", "agenda", "packet", "minutes"]):
                continue

            # Build absolute URL
            if href.startswith("http"):
                pdf_url = href
            elif href.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(agenda_url)
                pdf_url = f"{parsed.scheme}://{parsed.netloc}{href}"
            else:
                pdf_url = f"{agenda_url.rstrip('/')}/{href}"

            # Find a date near this link
            parent_text = ""
            for parent in a.parents:
                parent_text = parent.get_text(" ", strip=True)[:200]
                if any(m in parent_text for m in
                       ["January","February","March","April","May","June",
                        "July","August","September","October","November","December"]):
                    break

            date_match = re.search(
                r"(January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+\d{1,2},?\s*\d{4}|"
                r"\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}",
                parent_text, re.IGNORECASE
            )

            meeting_date = parse_date(date_match.group(0)) if date_match else None
            if not is_future_or_today(meeting_date):
                continue

            # Classify body type from label or page context
            body_type = classify_body(label) or classify_body(parent_text) or \
                        classify_body(municipality + " planning zoning")
            if not body_type:
                body_type = "planning_zoning"  # default for custom sites

            dl = download_packet(pdf_url, st, municipality,
                                 body_type, date_str(meeting_date))
            if not dl or dl.get("failed"):
                continue

            collected.append({
                "state":        st,
                "municipality": municipality,
                "place_type":   place_type,
                "body_name":    label[:80] or f"{municipality} Planning",
                "body_type":    body_type,
                "meeting_date": date_str(meeting_date),
                "meeting_time": "",
                "location":     "",
                "source_url":   agenda_url,
                "platform":     "Custom",
                **dl,
            })
            added += 1

    return added
