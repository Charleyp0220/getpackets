"""
scrapers/civicclerk.py — CivicClerk portal scraper.

CivicClerk (now CivicPlus) portals are at:
  https://{slug}.portal.civicclerk.com/

Each portal has a public events feed at:
  https://{slug}.portal.civicclerk.com/api/Events/GetPublishedEvents
    ?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD

Agenda packets are downloadable at:
  https://{slug}.portal.civicclerk.com/event/{event_id}/files/agenda/{file_id}
"""

import requests
from datetime import date, timedelta
from utils import (classify_body, is_future_or_today, parse_date,
                   date_str, download_packet)
from constants import HEADERS, REQUEST_TIMEOUT

CIVICCLERK_CITIES = {
    # Virginia
    "charlottesvilleva":  ("Virginia",       "Charlottesville"),
    "norfolkva":          ("Virginia",       "Norfolk"),
    "roanokeva":          ("Virginia",       "Roanoke"),
    "hamptonva":          ("Virginia",       "Hampton"),
    "lynchburgva":        ("Virginia",       "Lynchburg"),
    "harrisonburgva":     ("Virginia",       "Harrisonburg"),
    "alexandriava":       ("Virginia",       "Alexandria"),
    # California
    "ranchocordovaca":    ("California",     "Rancho Cordova"),
    "santabarbaraca":     ("California",     "Santa Barbara"),
    "berkeleica":         ("California",     "Berkeley"),
    "petalumaca":         ("California",     "Petaluma"),
    "clovisca":           ("California",     "Clovis"),
    "temeculaca":         ("California",     "Temecula"),
    "murrietaca":         ("California",     "Murrieta"),
    "antiochca":          ("California",     "Antioch"),
    "vacavilleca":        ("California",     "Vacaville"),
    # Maine
    "portlandme":         ("Maine",          "Portland"),
    "lewistonme":         ("Maine",          "Lewiston"),
    # Connecticut
    "norwalkct":          ("Connecticut",    "Norwalk"),
    "hartfordct":         ("Connecticut",    "Hartford"),
    "waterburyct":        ("Connecticut",    "Waterbury"),
    "danburyct":          ("Connecticut",    "Danbury"),
    # South Carolina
    "greenvillesc":       ("South Carolina", "Greenville"),
    "columbiasc":         ("South Carolina", "Columbia"),
    "charlestonsc":       ("South Carolina", "Charleston"),
    "rockhill":           ("South Carolina", "Rock Hill"),
    # Texas
    "amarillotx":         ("Texas",          "Amarillo"),
    "wacotx":             ("Texas",          "Waco"),
    "midlandtx":          ("Texas",          "Midland"),
    "odessatx":           ("Texas",          "Odessa"),
    "roundrocktx":        ("Texas",          "Round Rock"),
    "lewisvilletx":       ("Texas",          "Lewisville"),
    # Oklahoma
    "stillwaterok":       ("Oklahoma",       "Stillwater"),
    "normanok":           ("Oklahoma",       "Norman"),
    "brokenarrowok":      ("Oklahoma",       "Broken Arrow"),
    "lawtonok":           ("Oklahoma",       "Lawton"),
    "edmondok":           ("Oklahoma",       "Edmond"),
    # New Mexico
    "santafenm":          ("New Mexico",     "Santa Fe"),
    "rioranchonm":        ("New Mexico",     "Rio Rancho"),
    # Arizona
    "prescottaz":         ("Arizona",        "Prescott"),
    "flagstaffaz":        ("Arizona",        "Flagstaff"),
    "yumaaz":             ("Arizona",        "Yuma"),
    "goodyearaz":         ("Arizona",        "Goodyear"),
    "surpriseaz":         ("Arizona",        "Surprise"),
    "avondaleaz":         ("Arizona",        "Avondale"),
    # Oregon
    "bendor":             ("Oregon",         "Bend"),
    "medfordor":          ("Oregon",         "Medford"),
    "corvallisore":       ("Oregon",         "Corvallis"),
    "albanyore":          ("Oregon",         "Albany"),
    "hillsboroor":        ("Oregon",         "Hillsboro"),
    "beavertonor":        ("Oregon",         "Beaverton"),
    "greshamor":          ("Oregon",         "Gresham"),
    # Washington
    "bellinghamwa":       ("Washington",     "Bellingham"),
    "yakimawa":           ("Washington",     "Yakima"),
    "kennewickwa":        ("Washington",     "Kennewick"),
    "richlandwa":         ("Washington",     "Richland"),
    "olympiawa":          ("Washington",     "Olympia"),
    "laceywa":            ("Washington",     "Lacey"),
    "auburnwa":           ("Washington",     "Auburn"),
    "marysvillewa":       ("Washington",     "Marysville"),
    # Colorado
    "fortcollinsco":      ("Colorado",       "Fort Collins"),
    "puebloco":           ("Colorado",       "Pueblo"),
    "greeleico":          ("Colorado",       "Greeley"),
    "longmontco":         ("Colorado",       "Longmont"),
    "lovelandco":         ("Colorado",       "Loveland"),
    "broomfieldco":       ("Colorado",       "Broomfield"),
    # Montana
    "billingsmt":         ("Montana",        "Billings"),
    "missoulamt":         ("Montana",        "Missoula"),
    "greatfallsmt":       ("Montana",        "Great Falls"),
    "bozemanmt":          ("Montana",        "Bozeman"),
    # Wyoming
    "cheyennewy":         ("Wyoming",        "Cheyenne"),
    "casperwy":           ("Wyoming",        "Casper"),
    # North Dakota
    "fargond":            ("North Dakota",   "Fargo"),
    "bismarcknd":         ("North Dakota",   "Bismarck"),
    # South Dakota
    "siouxfallssd":       ("South Dakota",   "Sioux Falls"),
    "rapidcitysd":        ("South Dakota",   "Rapid City"),
    # Idaho
    "idahofallsid":       ("Idaho",          "Idaho Falls"),
    "pocatelloid":        ("Idaho",          "Pocatello"),
    "caldwellid":         ("Idaho",          "Caldwell"),
    # Nevada
    "sparksnv":           ("Nevada",         "Sparks"),
    "carsoncitynv":       ("Nevada",         "Carson City"),
    # Utah
    "sandyut":            ("Utah",           "Sandy"),
    "ogdenut":            ("Utah",           "Ogden"),
    "stgeorgeut":         ("Utah",           "St. George"),
    "laytonut":           ("Utah",           "Layton"),
    # Minnesota
    "rochestermn":        ("Minnesota",      "Rochester"),
    "duluthmn":           ("Minnesota",      "Duluth"),
    "bloomingtonmn":      ("Minnesota",      "Bloomington"),
    "brooklynparkmn":     ("Minnesota",      "Brooklyn Park"),
    "plymouthmn":         ("Minnesota",      "Plymouth"),
    "stcloudmn":          ("Minnesota",      "St. Cloud"),
    "eaganmn":            ("Minnesota",      "Eagan"),
    # Wisconsin
    "greenbaywi":         ("Wisconsin",      "Green Bay"),
    "kenoshawi":          ("Wisconsin",      "Kenosha"),
    "racinewi":           ("Wisconsin",      "Racine"),
    "appletonwi":         ("Wisconsin",      "Appleton"),
    "oshkoshwi":          ("Wisconsin",      "Oshkosh"),
    "waukeshawi":         ("Wisconsin",      "Waukesha"),
    "eauclairewi":        ("Wisconsin",      "Eau Claire"),
    "janesvillewi":       ("Wisconsin",      "Janesville"),
    # Iowa
    "cedarrapidsia":      ("Iowa",           "Cedar Rapids"),
    "davenportia":        ("Iowa",           "Davenport"),
    "siouxcityia":        ("Iowa",           "Sioux City"),
    "iowacityia":         ("Iowa",           "Iowa City"),
    "waterlooiowa":       ("Iowa",           "Waterloo"),
    "ankenyia":           ("Iowa",           "Ankeny"),
    # Kansas
    "overlandparkks":     ("Kansas",         "Overland Park"),
    "olatheks":           ("Kansas",         "Olathe"),
    "topekaks":           ("Kansas",         "Topeka"),
    "lawrenceks":         ("Kansas",         "Lawrence"),
    # Nebraska
    "lincolnne":          ("Nebraska",       "Lincoln"),
    "bellevuene":         ("Nebraska",       "Bellevue"),
    # Missouri
    "springfieldmo":      ("Missouri",       "Springfield"),
    "columbiamo":         ("Missouri",       "Columbia"),
    "independencemo":     ("Missouri",       "Independence"),
    # Tennessee
    "murfreesborotn":     ("Tennessee",      "Murfreesboro"),
    "franklintn":         ("Tennessee",      "Franklin"),
    "jacksontn":          ("Tennessee",      "Jackson"),
    "johnsoncitytn":      ("Tennessee",      "Johnson City"),
    "kingsporttn":        ("Tennessee",      "Kingsport"),
    # North Carolina
    "wilmingtonnc":       ("North Carolina", "Wilmington"),
    "highpointnc":        ("North Carolina", "High Point"),
    "concordnc":          ("North Carolina", "Concord"),
    "greenvillenc":       ("North Carolina", "Greenville"),
    "ashevillenc":        ("North Carolina", "Asheville"),
    "chapelhillnc":       ("North Carolina", "Chapel Hill"),
    "gastoniannc":        ("North Carolina", "Gastonia"),
    "apexnc":             ("North Carolina", "Apex"),
    # Georgia
    "sandyspringsga":     ("Georgia",        "Sandy Springs"),
    "roswellga":          ("Georgia",        "Roswell"),
    "albanyga":           ("Georgia",        "Albany"),
    "warnerrobinsga":     ("Georgia",        "Warner Robins"),
    "alpharettaga":       ("Georgia",        "Alpharetta"),
    "mariettaga":         ("Georgia",        "Marietta"),
    "smyrnaga":           ("Georgia",        "Smyrna"),
    "valdostaga":         ("Georgia",        "Valdosta"),
    # Alabama
    "tuscaloosaal":       ("Alabama",        "Tuscaloosa"),
    "hooveral":           ("Alabama",        "Hoover"),
    "dothantal":          ("Alabama",        "Dothan"),
    "auburnal":           ("Alabama",        "Auburn"),
    # Louisiana
    "lafayettela":        ("Louisiana",      "Lafayette"),
    "lakecharlesla":      ("Louisiana",      "Lake Charles"),
    "bossiercityla":      ("Louisiana",      "Bossier City"),
    # Mississippi
    "gulfportms":         ("Mississippi",    "Gulfport"),
    "hattiesburgms":      ("Mississippi",    "Hattiesburg"),
    "biloxims":           ("Mississippi",    "Biloxi"),
    # Arkansas
    "fortsmithar":        ("Arkansas",       "Fort Smith"),
    "fayettevillear":     ("Arkansas",       "Fayetteville"),
    "springdalear":       ("Arkansas",       "Springdale"),
    "jonesboroar":        ("Arkansas",       "Jonesboro"),
    # Maryland
    "bowiemd":            ("Maryland",       "Bowie"),
    "hagerstownmd":       ("Maryland",       "Hagerstown"),
    "annapolismd":        ("Maryland",       "Annapolis"),
    # New Hampshire
    "concordnh":          ("New Hampshire",  "Concord"),
    # West Virginia
    "huntingtonwv":       ("West Virginia",  "Huntington"),
    "morgantownwv":       ("West Virginia",  "Morgantown"),
    # Delaware
    "doverde":            ("Delaware",       "Dover"),
    # Hawaii
    "hilohawaii":         ("Hawaii",         "Hilo"),
    # Alaska
    "fairbanksak":        ("Alaska",         "Fairbanks"),
    "juneauak":           ("Alaska",         "Juneau"),
}

PORTAL_BASE = "https://{slug}.portal.civicclerk.com"
LOOKAHEAD   = 90  # days ahead to search


def scrape_civicclerk(state: str, collected: list, max_packets: int) -> int:
    """Scrape all CivicClerk cities in `state`."""
    cities = {slug: info for slug, info in CIVICCLERK_CITIES.items()
              if info[0] == state}
    if not cities:
        return 0

    added    = 0
    today    = date.today()
    end_date = today + timedelta(days=LOOKAHEAD)
    t_str    = today.strftime("%Y-%m-%d")
    e_str    = end_date.strftime("%Y-%m-%d")

    for slug, (st, display_name) in cities.items():
        if len(collected) >= max_packets:
            break

        base = PORTAL_BASE.format(slug=slug)

        # Try the CivicClerk events API — several possible URL patterns
        events = []
        for api_url in [
            f"{base}/api/Events/GetPublishedEvents?startDate={t_str}&endDate={e_str}",
            f"{base}/api/Events?startDate={t_str}&endDate={e_str}",
            f"{base}/api/v1/Events?startDate={t_str}&endDate={e_str}&published=true",
        ]:
            try:
                r = requests.get(api_url, headers={
                    **HEADERS,
                    "Accept": "application/json",
                    "Referer": base,
                }, timeout=REQUEST_TIMEOUT)
                if r.status_code == 200:
                    ct = r.headers.get("Content-Type", "")
                    if "json" in ct:
                        data = r.json()
                        if isinstance(data, list):
                            events = data
                        elif isinstance(data, dict):
                            events = (data.get("events") or
                                      data.get("value") or
                                      data.get("items") or [])
                        if events:
                            break
            except Exception:
                continue

        if not events:
            continue

        for ev in events:
            if len(collected) >= max_packets:
                break

            body_name = (ev.get("EventBodyName") or ev.get("bodyName") or
                         ev.get("name") or ev.get("title") or "")
            body_type = classify_body(body_name)
            if not body_type:
                continue

            raw_date     = (ev.get("EventDate") or ev.get("eventDate") or
                            ev.get("date") or ev.get("startDate") or "")
            meeting_date = parse_date(str(raw_date))
            if not is_future_or_today(meeting_date):
                continue

            # Build agenda URL
            event_id  = (ev.get("EventId") or ev.get("id") or
                         ev.get("eventId") or "")
            file_id   = (ev.get("AgendaFileId") or ev.get("agendaFileId") or
                         ev.get("packetFileId") or "")
            agenda_url = ev.get("agendaUrl") or ev.get("EventAgendaFile") or ""

            if not agenda_url and event_id and file_id:
                agenda_url = f"{base}/event/{event_id}/files/agenda/{file_id}"
            if not agenda_url and event_id:
                agenda_url = f"{base}/event/{event_id}/files"
            if not agenda_url:
                continue

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
                "meeting_time": ev.get("EventTime") or ev.get("time") or "",
                "location":     ev.get("location") or "",
                "source_url":   base,
                "platform":     "CivicClerk",
                **dl,
            })
            added += 1

    return added
