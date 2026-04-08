"""
fix_and_run.py — fixes the database and tests which slugs actually work,
then reports what's ready to collect packets.

Run with: python fix_and_run.py
"""
import sys, os, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_conn, init_db, get_stats
from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)

def ok(m):   print(Fore.GREEN  + "  ✔ " + Style.RESET_ALL + m)
def info(m): print(Fore.CYAN   + "  ℹ " + Style.RESET_ALL + m)
def warn(m): print(Fore.YELLOW + "  ⚠ " + Style.RESET_ALL + m)

HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/124.0.0.0"}

init_db()
conn = get_conn()

print()
print(Fore.CYAN + "=" * 55)
print(Fore.CYAN + "  GETPACKETS FIX & VERIFY")
print(Fore.CYAN + "=" * 55)

# ── Step 1: Unarchive all packets ─────────────────────────
print()
print("Step 1: Restoring archived packets...")
result = conn.execute(
    "UPDATE packets SET status='active', archived_at=NULL WHERE status='archived'"
)
conn.commit()
ok(f"Restored {result.rowcount} packet(s) to active")

# ── Step 2: Check what's on disk vs database ──────────────
print()
print("Step 2: Checking files on disk vs database...")
from constants import PACKETS_DIR
pdf_count = 0
for root, dirs, files in os.walk(PACKETS_DIR):
    for f in files:
        if f.endswith('.pdf'):
            pdf_count += 1
            # Check if it's in the database
            row = conn.execute(
                "SELECT id FROM packets WHERE filename=?", (f,)
            ).fetchone()
            if not row:
                warn(f"On disk but NOT in DB: {f}")
info(f"Total PDFs on disk: {pdf_count}")

s = get_stats()
info(f"Total packets in DB: {s['total_packets']}")

# ── Step 3: Test Legistar slugs live ─────────────────────
print()
print("Step 3: Testing Legistar slugs live...")
from datetime import date
today = date.today().strftime("%Y-%m-%dT00:00:00")

slugs_to_test = [
    ("seattle",       "Washington"),
    ("denver",        "Colorado"),
    ("boston",        "Massachusetts"),
    ("nashville",     "Tennessee"),
    ("chicago",       "Illinois"),
    ("charlotte",     "North Carolina"),
    ("portland",      "Oregon"),
    ("milwaukee",     "Wisconsin"),
    ("louisville",    "Kentucky"),
    ("saltlakecity",  "Utah"),
    ("omaha",         "Nebraska"),
    ("raleigh",       "North Carolina"),
    ("tucson",        "Arizona"),
    ("fresno",        "California"),  
    ("aurora",        "Colorado"),
    ("tampa",         "Florida"),
    ("cleveland",     "Ohio"),
    ("pittsburgh",    "Pennsylvania"),
    ("minneapolis",   "Minnesota"),
    ("atlanta",       "Georgia"),
]

working_slugs = []
for slug, state in slugs_to_test:
    url = (f"https://webapi.legistar.com/v1/{slug}/Events"
           f"?$filter=EventDate ge datetime'{today}'&$top=3")
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code == 200 and len(r.content) > 300:
            import xml.etree.ElementTree as ET
            NS = "http://schemas.datacontract.org/2004/07/LegistarWebAPI.Models.v1"
            root = ET.fromstring(r.content)
            events = root.findall(f"{{{NS}}}GranicusEvent")
            with_pdf = [e for e in events
                       if (e.find(f"{{{NS}}}EventAgendaFile") is not None and
                           e.find(f"{{{NS}}}EventAgendaFile").text)]
            if with_pdf:
                ok(f"{slug:15s} ({state}) — {len(with_pdf)} events with PDFs")
                working_slugs.append((slug, state))
            elif events:
                warn(f"{slug:15s} ({state}) — {len(events)} events but no PDFs yet")
            else:
                info(f"{slug:15s} — no upcoming events")
        elif r.status_code == 500:
            pass  # invalid slug
    except Exception as e:
        pass

conn.close()

print()
print(Fore.CYAN + "=" * 55)
print(f"  {len(working_slugs)} slugs confirmed with agenda PDFs right now")
print()
if working_slugs:
    print(Fore.GREEN + "  READY — these will give you packets immediately:")
    for slug, state in working_slugs:
        print(f"    {slug} ({state})")
print()
print(Fore.CYAN + "  Run:  python run.py")
print(Fore.CYAN + "=" * 55)
print()
