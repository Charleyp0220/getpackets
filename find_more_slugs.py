"""
find_more_slugs.py — finds correct CivicPlus slugs for cities that returned HTTP 0
by trying alternate URL patterns.

Run with: python find_more_slugs.py
"""
import sys, os, requests, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0.0.0"}
TIMEOUT = 8

def ok(m):   print(Fore.GREEN  + "  FOUND  " + Style.RESET_ALL + m)
def fail(m): print(Fore.RED    + "  miss   " + Style.RESET_ALL + m)

def test(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        return r.status_code, len(r.content)
    except:
        return 0, 0

# Cities that failed — try alternate slug patterns
# Format: (city, state, state_abbr, [slug_variants_to_try])
RETRY = [
    # North Carolina
    ("Raleigh",       "North Carolina", "nc", ["nc-raleighcity","raleigh-nc","raleighgov","cityofraleigh"]),
    ("Cary",          "North Carolina", "nc", ["nc-carytown","cary-nc","townofcary"]),
    ("Wilmington",    "North Carolina", "nc", ["nc-wilmingtoncity","wilmington-nc","cityofwilmington"]),
    ("Asheville",     "North Carolina", "nc", ["nc-ashevillecity","asheville-nc","cityofasheville"]),
    ("Chapel Hill",   "North Carolina", "nc", ["nc-chapelhilltown","chapelhill-nc","townofchapelhill"]),
    ("Gastonia",      "North Carolina", "nc", ["nc-gastoniacity","gastonia-nc"]),
    # California
    ("Chico",         "California",     "ca", ["ca-chicocity","chico-ca","cityofchico"]),
    ("Redding",       "California",     "ca", ["ca-reddingcity","redding-ca","cityofredding"]),
    ("Roseville",     "California",     "ca", ["ca-rosevillecity","roseville-ca","cityofroseville"]),
    ("Berkeley",      "California",     "ca", ["ca-berkeleycity","berkeley-ca","cityofberkeley","cityofberkeleycivicplus"]),
    ("Petaluma",      "California",     "ca", ["ca-petalumacity","petaluma-ca","cityofpetaluma"]),
    ("Vacaville",     "California",     "ca", ["ca-vacavillecity","vacaville-ca","cityofvacaville"]),
    ("Santa Barbara", "California",     "ca", ["ca-santabarbaracounty","sb-city","santabarbara-ca"]),
    ("Hayward",       "California",     "ca", ["ca-haywardcity","hayward-ca","cityofhayward"]),
    ("Vallejo",       "California",     "ca", ["ca-vallejocity","vallejo-ca","cityofvallejo"]),
    # Texas
    ("Amarillo",      "Texas",          "tx", ["tx-amarillocity","amarillo-tx","cityofamarillo"]),
    ("Waco",          "Texas",          "tx", ["tx-wacocity","waco-tx","cityofwaco","wacotx"]),
    ("Round Rock",    "Texas",          "tx", ["tx-roundrockcity","roundrock-tx","cityofroundrock"]),
    ("Lewisville",    "Texas",          "tx", ["tx-lewisvillecity","lewisville-tx","cityoflewisville"]),
    ("Richardson",    "Texas",          "tx", ["tx-richardsoncity","richardson-tx","cityofrichardson"]),
    ("Pearland",      "Texas",          "tx", ["tx-pearlandcity","pearland-tx","cityofpearland"]),
    ("Tyler",         "Texas",          "tx", ["tx-tylercity","tyler-tx","cityoftyler"]),
    # Florida
    ("Sarasota",      "Florida",        "fl", ["fl-sarasotacity","sarasota-fl","cityofsarasota"]),
    ("Bradenton",     "Florida",        "fl", ["fl-bradentonCity","bradenton-fl","cityofbradenton"]),
    ("Lakeland",      "Florida",        "fl", ["fl-lakelandcity","lakeland-fl","cityoflakeland"]),
    ("Clearwater",    "Florida",        "fl", ["fl-clearwatercity","clearwater-fl","cityofclearwater"]),
    ("Gainesville",   "Florida",        "fl", ["fl-gainesvillecity","gainesville-fl","cityofgainesville"]),
    ("Kissimmee",     "Florida",        "fl", ["fl-kissimmeecity","kissimmee-fl","cityofkissimmee"]),
    # Georgia
    ("Albany",        "Georgia",        "ga", ["ga-albanycity","albany-ga","cityofalbany"]),
    ("Warner Robins", "Georgia",        "ga", ["ga-warnerrobinscity","warnerrobins-ga"]),
    ("Alpharetta",    "Georgia",        "ga", ["ga-alpharettacity","alpharetta-ga","cityofalpharetta"]),
    ("Valdosta",      "Georgia",        "ga", ["ga-valdostacity","valdosta-ga","cityofvaldosta"]),
    # Ohio
    ("Hamilton",      "Ohio",           "oh", ["oh-hamiltoncity","hamilton-oh","cityofhamilton"]),
    ("Kettering",     "Ohio",           "oh", ["oh-ketteringcity","kettering-oh","cityofkettering"]),
    ("Springfield",   "Ohio",           "oh", ["oh-springfieldcity","springfield-oh"]),
    ("Newark",        "Ohio",           "oh", ["oh-newark","newark-oh","cityofnewark"]),
    ("Mentor",        "Ohio",           "oh", ["oh-mentorcity","mentor-oh","cityofmentor"]),
    # Michigan
    ("Troy",          "Michigan",       "mi", ["mi-troycity","troy-mi","cityoftroy"]),
    ("Southfield",    "Michigan",       "mi", ["mi-southfieldcity","southfield-mi","cityofsouthfield"]),
    # Wisconsin
    ("Green Bay",     "Wisconsin",      "wi", ["wi-greenbaycity","greenbay-wi","cityofgreenbay","wi-greenbay"]),
    ("Kenosha",       "Wisconsin",      "wi", ["wi-kenoshacity","kenosha-wi","cityofkenosha"]),
    ("Racine",        "Wisconsin",      "wi", ["wi-racinecity","racine-wi","cityofracine"]),
    ("Appleton",      "Wisconsin",      "wi", ["wi-appletoncity","appleton-wi","cityofappleton"]),
    ("Oshkosh",       "Wisconsin",      "wi", ["wi-oshkoshcity","oshkosh-wi","cityofoshkosh"]),
    ("Eau Claire",    "Wisconsin",      "wi", ["wi-eauclairecity","eauclaire-wi","cityofeauclaire"]),
    # Iowa
    ("Cedar Rapids",  "Iowa",           "ia", ["ia-cedarrapidscity","cedarrapids-ia","cityofcedarrapids"]),
    ("Davenport",     "Iowa",           "ia", ["ia-davenportcity","davenport-ia","cityofdavenport"]),
    ("Iowa City",     "Iowa",           "ia", ["ia-iowacitycity","iowacity-ia","cityofiowacity"]),
    ("Waterloo",      "Iowa",           "ia", ["ia-waterloocity","waterloo-ia","cityofwaterloo"]),
    # Oregon
    ("Bend",          "Oregon",         "or", ["or-bendcity","bend-or","cityofbend","or-bend"]),
    ("Medford",       "Oregon",         "or", ["or-medfordcity","medford-or","cityofmedford"]),
    ("Corvallis",     "Oregon",         "or", ["or-corvalliscity","corvallis-or","cityofcorvallis"]),
    ("Hillsboro",     "Oregon",         "or", ["or-hillsborocity","hillsboro-or","cityofhillsboro"]),
    ("Beaverton",     "Oregon",         "or", ["or-beavertoncity","beaverton-or","cityofbeaverton"]),
    # Washington
    ("Bellingham",    "Washington",     "wa", ["wa-bellinghamcity","bellingham-wa","cityofbellingham"]),
    ("Yakima",        "Washington",     "wa", ["wa-yakimacity","yakima-wa","cityofyakima"]),
    ("Olympia",       "Washington",     "wa", ["wa-olympiacity","olympia-wa","cityofolympia"]),
    ("Auburn",        "Washington",     "wa", ["wa-auburncity","auburn-wa","cityofauburn"]),
    # Colorado
    ("Fort Collins",  "Colorado",       "co", ["co-fortcollinscity","fortcollins-co","cityoffortcollins"]),
    ("Pueblo",        "Colorado",       "co", ["co-pueblocity","pueblo-co","cityofpueblo"]),
    ("Greeley",       "Colorado",       "co", ["co-greeleycity","greeley-co","cityofgreeley"]),
    ("Longmont",      "Colorado",       "co", ["co-longmontcity","longmont-co","cityoflongmont"]),
    ("Loveland",      "Colorado",       "co", ["co-lovelandcity","loveland-co","cityofloveland"]),
    # Minnesota
    ("Rochester",     "Minnesota",      "mn", ["mn-rochestercity","rochester-mn","cityofrochester"]),
    ("Duluth",        "Minnesota",      "mn", ["mn-duluthcity","duluth-mn","cityofduluth"]),
    ("Bloomington",   "Minnesota",      "mn", ["mn-bloomingtoncity","bloomington-mn","cityofbloomington"]),
    ("St. Cloud",     "Minnesota",      "mn", ["mn-stcloudcity","stcloud-mn","cityofstcloud"]),
    # Others
    ("Boise",         "Idaho",          "id", ["id-boisecity","boise-id","cityofboise"]),
    ("Billings",      "Montana",        "mt", ["mt-billingscity","billings-mt","cityofbillings"]),
    ("Missoula",      "Montana",        "mt", ["mt-missoulacity","missoula-mt","cityofmissoula"]),
    ("Bozeman",       "Montana",        "mt", ["mt-bozemancity","bozeman-mt","cityofbozeman"]),
    ("Cheyenne",      "Wyoming",        "wy", ["wy-cheyennecity","cheyenne-wy","cityofcheyenne"]),
    ("Providence",    "Rhode Island",   "ri", ["ri-providencecity","providence-ri","cityofprovidence"]),
    ("Hilo",          "Hawaii",         "hi", ["hi-hilocounty","hilo-hi","countyofhawaii"]),
]

print()
print(Fore.CYAN + "="*60)
print(Fore.CYAN + f"  Finding correct slugs for {len(RETRY)} cities...")
print(Fore.CYAN + "="*60)
print()

found = []
for city, state, abbr, variants in RETRY:
    hit = None
    for slug in variants:
        url = f"https://{slug}.civicplus.com/AgendaCenter"
        code, size = test(url)
        if code in (200, 403) and size > 100:
            hit = slug
            break
        time.sleep(0.2)

    if hit:
        ok(f"{city:20s} ({state}) → {hit}")
        found.append((hit, state, city))
    else:
        fail(f"{city:20s} ({state})")

print()
print(Fore.CYAN + "="*60)
print(f"  Found {len(found)} new working slugs")
print(Fore.CYAN + "="*60)

if found:
    print()
    print("Add these to scrapers/civicplus.py CIVICPLUS_CITIES dict:")
    print()
    for slug, state, city in found:
        print(f'    "{slug}":{" "*(30-len(slug))}("{state}", "{city}"),')

    # Auto-append to civicplus.py
    with open("scrapers/civicplus.py", "r") as f:
        content = f.read()

    additions = "\n    # Auto-discovered slugs\n"
    for slug, state, city in found:
        line = f'    "{slug}":{" "*(30-len(slug))}("{state}", "{city}"),\n'
        if f'"{slug}"' not in content:
            additions += line

    content = content.replace("}\n\nCIVICPLUS_BASE", additions + "}\n\nCIVICPLUS_BASE")
    with open("scrapers/civicplus.py", "w") as f:
        f.write(content)
    print()
    print(Fore.GREEN + f"  Auto-added to scrapers/civicplus.py")

print()
