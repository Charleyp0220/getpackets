"""
verify_slugs.py — tests all CivicPlus and PrimeGov slugs live
and removes the ones that return 404.

Run with: python verify_slugs.py
Results saved to: verified_civicplus.txt and verified_primegov.txt
"""

import sys, os, requests, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrapers.civicplus import CIVICPLUS_CITIES
from scrapers.primegov  import PRIMEGOV_CITIES
from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0.0.0"}
TIMEOUT = 8

def ok(m):    print(Fore.GREEN  + f"  OK   " + Style.RESET_ALL + m)
def fail(m):  print(Fore.RED    + f"  FAIL " + Style.RESET_ALL + m)
def warn(m):  print(Fore.YELLOW + f"  SKIP " + Style.RESET_ALL + m)

def test_url(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                         allow_redirects=True)
        return r.status_code, len(r.content)
    except Exception as e:
        return 0, 0

print()
print(Fore.CYAN + "="*60)
print(Fore.CYAN + "  SLUG VERIFIER — CivicPlus + PrimeGov")
print(Fore.CYAN + "="*60)

# ── CivicPlus ─────────────────────────────────────────────
print()
print(f"Testing {len(CIVICPLUS_CITIES)} CivicPlus slugs...")
print()

cp_good = {}
cp_bad  = []

for i, (slug, (state, name)) in enumerate(CIVICPLUS_CITIES.items()):
    url = f"https://{slug}.civicplus.com/AgendaCenter"
    code, size = test_url(url)
    if code == 200 and size > 500:
        ok(f"{slug:30s} ({name}, {state})")
        cp_good[slug] = (state, name)
    elif code == 403:
        warn(f"{slug:30s} — 403 blocked")
        cp_good[slug] = (state, name)  # keep — just bot-blocked
    elif code == 301 or code == 302:
        warn(f"{slug:30s} — redirects (keeping)")
        cp_good[slug] = (state, name)
    else:
        fail(f"{slug:30s} — HTTP {code}")
        cp_bad.append(slug)
    time.sleep(0.3)

print()
print(Fore.GREEN + f"  CivicPlus: {len(cp_good)} working, {len(cp_bad)} removed")

# ── PrimeGov ──────────────────────────────────────────────
print()
print(f"Testing {len(PRIMEGOV_CITIES)} PrimeGov slugs...")
print()

pg_good = {}
pg_bad  = []

for slug, (state, name) in PRIMEGOV_CITIES.items():
    url = f"https://{slug}.primegov.com/public/portal"
    code, size = test_url(url)
    if code == 200 and size > 500:
        ok(f"{slug:30s} ({name}, {state})")
        pg_good[slug] = (state, name)
    elif code == 403:
        warn(f"{slug:30s} — 403 blocked (keeping)")
        pg_good[slug] = (state, name)
    elif code in (301, 302):
        warn(f"{slug:30s} — redirects (keeping)")
        pg_good[slug] = (state, name)
    else:
        fail(f"{slug:30s} — HTTP {code}")
        pg_bad.append(slug)
    time.sleep(0.3)

print()
print(Fore.GREEN + f"  PrimeGov: {len(pg_good)} working, {len(pg_bad)} removed")

# ── Save results ──────────────────────────────────────────
with open("verified_civicplus.txt", "w") as f:
    f.write("# Verified CivicPlus slugs\n")
    for slug, (state, name) in cp_good.items():
        f.write(f"{slug},{state},{name}\n")

with open("verified_primegov.txt", "w") as f:
    f.write("# Verified PrimeGov slugs\n")
    for slug, (state, name) in pg_good.items():
        f.write(f"{slug},{state},{name}\n")

# ── Patch scrapers with verified slugs ───────────────────
print()
print("Patching scrapers/civicplus.py ...")
import re
with open("scrapers/civicplus.py", "r") as f:
    cp_content = f.read()
# Remove bad slugs
for slug in cp_bad:
    cp_content = re.sub(rf'\s*"{slug}"[^\n]+\n', '\n', cp_content)
with open("scrapers/civicplus.py", "w") as f:
    f.write(cp_content)
ok(f"Removed {len(cp_bad)} bad CivicPlus slugs")

print("Patching scrapers/primegov.py ...")
with open("scrapers/primegov.py", "r") as f:
    pg_content = f.read()
for slug in pg_bad:
    pg_content = re.sub(rf'\s*"{slug}"[^\n]+\n', '\n', pg_content)
with open("scrapers/primegov.py", "w") as f:
    f.write(pg_content)
ok(f"Removed {len(pg_bad)} bad PrimeGov slugs")

print()
print(Fore.CYAN + "="*60)
print(f"  Done. Run python run.py to start collecting.")
print(Fore.CYAN + "="*60)
print()
