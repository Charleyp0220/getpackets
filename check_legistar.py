"""
check_legistar.py — finds ALL working Legistar slugs by testing them live.
Run with: python check_legistar.py
"""
import sys, os, requests, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import date
from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

today = date.today().strftime("%Y-%m-%dT00:00:00")

# Every candidate slug to test
CANDIDATES = [
    # Washington
    ("seattle","Washington"), ("bellevue","Washington"), ("tacoma","Washington"),
    ("spokane","Washington"), ("renton","Washington"), ("kent","Washington"),
    ("everett","Washington"), ("kirkland","Washington"), ("redmond","Washington"),
    # Colorado
    ("denver","Colorado"), ("boulder","Colorado"), ("aurora","Colorado"),
    ("fort-collins","Colorado"), ("lakewood","Colorado"), ("pueblo","Colorado"),
    ("greeley","Colorado"), ("longmont","Colorado"), ("arvada","Colorado"),
    # Massachusetts  
    ("boston","Massachusetts"), ("worcester","Massachusetts"), ("cambridge","Massachusetts"),
    ("lowell","Massachusetts"), ("springfield-ma","Massachusetts"),
    # Tennessee
    ("nashville","Tennessee"), ("memphis","Tennessee"), ("knoxville","Tennessee"),
    ("chattanooga","Tennessee"), ("clarksville","Tennessee"),
    # Illinois
    ("chicago","Illinois"), ("springfield","Illinois"), ("rockford","Illinois"),
    ("peoria","Illinois"), ("elgin","Illinois"), ("joliet","Illinois"),
    ("evanston","Illinois"), ("naperville","Illinois"), ("aurora","Illinois"),
    ("waukegan","Illinois"), ("oak-park","Illinois"),
    # North Carolina
    ("charlotte","North Carolina"), ("raleigh","North Carolina"),
    ("durham","North Carolina"), ("greensboro","North Carolina"),
    ("winston-salem","North Carolina"), ("cary","North Carolina"),
    ("fayetteville","North Carolina"),
    # California
    ("lacity","California"), ("sfgov","California"), ("sandiego","California"),
    ("sanjose","California"), ("sacramento","California"), ("longbeachca","California"),
    ("anaheim","California"), ("irvine","California"), ("glendale","California"),
    ("fremont","California"), ("modesto","California"), ("fontana","California"),
    ("oxnard","California"), ("pasadena","California"), ("torrance","California"),
    # Texas
    ("austintexas","Texas"), ("houston","Texas"), ("sanantonio","Texas"),
    ("dallas","Texas"), ("fortworth","Texas"), ("elpaso","Texas"),
    ("arlington","Texas"), ("corpuschristi","Texas"), ("plano","Texas"),
    ("laredo","Texas"), ("lubbock","Texas"), ("garland","Texas"),
    ("irving","Texas"), ("amarillo","Texas"), ("brownsville","Texas"),
    ("mcallen","Texas"), ("waco","Texas"), ("carrollton","Texas"),
    # Florida
    ("miami","Florida"), ("orlando","Florida"), ("tampa","Florida"),
    ("jacksonville","Florida"), ("stpete","Florida"), ("tallahassee","Florida"),
    ("fort-lauderdale","Florida"), ("cape-coral","Florida"), ("gainesville","Florida"),
    ("clearwater","Florida"), ("west-palm-beach","Florida"),
    # Ohio
    ("columbus","Ohio"), ("cleveland","Ohio"), ("cincinnati","Ohio"),
    ("toledo","Ohio"), ("akron","Ohio"), ("dayton","Ohio"), ("canton","Ohio"),
    # Michigan
    ("detroit","Michigan"), ("grandrapids","Michigan"), ("lansing","Michigan"),
    ("ann-arbor","Michigan"), ("flint","Michigan"), ("warren","Michigan"),
    ("kalamazoo","Michigan"),
    # Georgia
    ("atlanta","Georgia"), ("savannah","Georgia"), ("macon","Georgia"),
    ("augusta","Georgia"),
    # Arizona
    ("phoenix","Arizona"), ("tucson","Arizona"), ("mesa","Arizona"),
    ("chandler","Arizona"), ("scottsdale","Arizona"), ("gilbert","Arizona"),
    ("tempe","Arizona"), ("peoria","Arizona"),
    # Virginia
    ("virginia-beach","Virginia"), ("norfolk","Virginia"), ("richmond-va","Virginia"),
    ("chesapeake","Virginia"), ("alexandria","Virginia"), ("hampton","Virginia"),
    # Pennsylvania
    ("phila","Pennsylvania"), ("pittsburgh","Pennsylvania"), ("allentown","Pennsylvania"),
    ("erie","Pennsylvania"),
    # Indiana
    ("indianapolis","Indiana"), ("fortwayne","Indiana"), ("evansville","Indiana"),
    ("south-bend","Indiana"),
    # Missouri
    ("kansascity","Missouri"), ("stlouis","Missouri"), ("springfield-mo","Missouri"),
    # Wisconsin
    ("milwaukee","Wisconsin"), ("madison","Wisconsin"), ("green-bay","Wisconsin"),
    ("kenosha","Wisconsin"), ("racine","Wisconsin"),
    # Maryland
    ("baltimore","Maryland"), ("frederick","Maryland"),
    # Minnesota
    ("minneapolis","Minnesota"), ("saint-paul","Minnesota"), ("duluth","Minnesota"),
    # Nevada
    ("lasvegas","Nevada"), ("henderson","Nevada"), ("reno","Nevada"),
    # Oregon
    ("portland","Oregon"), ("eugene","Oregon"), ("salem","Oregon"),
    ("hillsboro","Oregon"), ("beaverton","Oregon"),
    # Kentucky
    ("louisville","Kentucky"), ("lexington","Kentucky"),
    # Oklahoma
    ("oklahomacity","Oklahoma"), ("tulsa","Oklahoma"),
    # Louisiana
    ("neworleans","Louisiana"), ("shreveport","Louisiana"),
    # Connecticut
    ("hartford","Connecticut"), ("bridgeport","Connecticut"), ("new-haven","Connecticut"),
    # Iowa
    ("desmoines","Iowa"), ("cedar-rapids","Iowa"),
    # Kansas
    ("wichita","Kansas"),
    # Utah
    ("saltlakecity","Utah"), ("provo","Utah"), ("west-jordan","Utah"),
    # Nebraska
    ("omaha","Nebraska"),
    # New Jersey
    ("jersey-city","New Jersey"), ("newark","New Jersey"),
    # Alabama
    ("birmingham","Alabama"), ("huntsville","Alabama"), ("montgomery","Alabama"),
    # Idaho
    ("boise","Idaho"),
    # New Mexico
    ("albuquerque","New Mexico"),
    # South Carolina
    ("columbia-sc","South Carolina"), ("charleston-sc","South Carolina"),
    # Rhode Island
    ("providence","Rhode Island"),
    # New Hampshire
    ("manchester-nh","New Hampshire"),
    # Hawaii
    ("honolulu","Hawaii"),
    # Alaska
    ("anchorage","Alaska"),
    # New York
    ("buffalo","New York"), ("rochester","New York"), ("syracuse","New York"),
    ("albany","New York"), ("yonkers","New York"),
    # Montana
    ("billings","Montana"),
    # North Dakota
    ("fargo","North Dakota"),
    # South Dakota
    ("sioux-falls","South Dakota"),
    # Wyoming
    ("cheyenne","Wyoming"),
    # Delaware
    ("wilmington","Delaware"),
    # West Virginia
    ("charleston-wv","West Virginia"),
]

print()
print(Fore.CYAN + "="*60)
print(Fore.CYAN + "  Testing all Legistar slugs live...")
print(Fore.CYAN + f"  {len(CANDIDATES)} candidates to check")
print(Fore.CYAN + "="*60)
print()

working   = []
has_pdfs  = []
no_events = []
broken    = []

for slug, state in CANDIDATES:
    url = (f"https://webapi.legistar.com/v1/{slug}/Events"
           f"?$filter=EventDate ge datetime'{today}'&$top=5")
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 500:
            broken.append((slug, state, "invalid slug"))
            continue
        if r.status_code != 200:
            broken.append((slug, state, f"HTTP {r.status_code}"))
            continue

        # Check if it's XML or HTML (block page)
        ct = r.headers.get("Content-Type", "")
        if "html" in ct.lower() and "xml" not in ct.lower():
            broken.append((slug, state, "blocked (HTML response)"))
            continue

        import xml.etree.ElementTree as ET
        NS = "http://schemas.datacontract.org/2004/07/LegistarWebAPI.Models.v1"
        try:
            root = ET.fromstring(r.content)
        except ET.ParseError:
            # Try reading first bytes to diagnose
            preview = r.content[:100].decode("utf-8", errors="replace")
            broken.append((slug, state, f"parse error: {preview[:50]}"))
            continue

        events = root.findall(f"{{{NS}}}GranicusEvent")
        pdfs = []
        for ev in events:
            af = ev.find(f"{{{NS}}}EventAgendaFile")
            if af is not None and af.text and af.text.strip():
                pdfs.append(af.text.strip())

        if pdfs:
            print(Fore.GREEN + f"  READY  {slug:20s} ({state}) — {len(pdfs)} PDFs")
            has_pdfs.append((slug, state, pdfs))
            working.append((slug, state))
        elif events:
            print(Fore.YELLOW + f"  events {slug:20s} ({state}) — {len(events)} events, no PDFs yet")
            working.append((slug, state))
        else:
            no_events.append((slug, state))

        time.sleep(0.3)  # be polite

    except Exception as e:
        broken.append((slug, state, str(e)[:60]))

print()
print(Fore.CYAN + "="*60)
print(f"  Working slugs:       {len(working)}")
print(Fore.GREEN + f"  With PDFs now:       {len(has_pdfs)}")
print(f"  No upcoming events:  {len(no_events)}")
print(f"  Broken/invalid:      {len(broken)}")
print(Fore.CYAN + "="*60)

if has_pdfs:
    print()
    print(Fore.GREEN + "  These will download immediately when you run run.py:")
    for slug, state, pdfs in has_pdfs:
        print(f"    {slug} ({state}) — {len(pdfs)} PDFs")

# Save working slugs to a file for reference
with open("working_slugs.txt", "w") as f:
    f.write("# Working Legistar slugs confirmed live\n")
    for slug, state in working:
        f.write(f"{slug},{state}\n")
print()
print(f"  Saved {len(working)} working slugs to working_slugs.txt")
print()
