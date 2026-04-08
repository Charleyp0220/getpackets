"""
diagnose.py — shows exactly what each scraper produces for one state.
Run: python diagnose.py
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)
from database import init_db, get_stats, get_conn
from constants import DB_FILE

init_db()

print()
print(Fore.CYAN + "="*60)
print(Fore.CYAN + "  GETPACKETS DIAGNOSTIC")
print(Fore.CYAN + "="*60)

# 1. Database status
s = get_stats()
conn = get_conn()
skip_count = conn.execute("SELECT COUNT(*) FROM skip_list").fetchone()[0]
recycle_count = conn.execute("SELECT COUNT(*) FROM recycle_bin").fetchone()[0]

# Check for duplicates in DB
dups = conn.execute("""
    SELECT municipality, state, body_type, meeting_date, COUNT(*) as cnt
    FROM meetings GROUP BY municipality, state, body_type, meeting_date
    HAVING cnt > 1
""").fetchall()

# Check platform breakdown
platforms = conn.execute("""
    SELECT m.platform, COUNT(*) as cnt
    FROM packets p JOIN meetings m ON m.id=p.meeting_id
    WHERE p.status='active'
    GROUP BY m.platform ORDER BY cnt DESC
""").fetchall()

conn.close()

print(f"\n  Active packets : {s['total_packets']}")
print(f"  Archived       : {s['archived_packets']}")
print(f"  Skip list      : {skip_count} (never re-download)")
print(f"  Recycle bin    : {recycle_count}")
print(f"  Duplicates     : {len(dups)}")
if platforms:
    print(f"\n  By platform:")
    for p, cnt in platforms:
        print(f"    {(p or 'Unknown'):20s} {cnt}")

# 2. Test each scraper on California (rich state)
print()
print(Fore.CYAN + "  Testing each scraper on California...")
print(Fore.CYAN + "  (1 minute, shows exactly what works)")
print()

results = {}

# Legistar
try:
    from scrapers.legistar import LEGISTAR_CITIES, scrape_legistar_slug
    from concurrent.futures import ThreadPoolExecutor, as_completed
    ca_slugs = [(slug, name) for slug, (st, name) in LEGISTAR_CITIES.items() if st == "California"]
    items = []
    t0 = time.time()
    def fetch(args):
        slug, name = args
        r = []
        scrape_legistar_slug(slug, "California", name, "city", r, 200)
        return r
    with ThreadPoolExecutor(max_workers=16) as ex:
        for future in as_completed({ex.submit(fetch, s): s for s in ca_slugs[:10]}):
            items.extend(future.result())
    results["Legistar"] = (len(items), time.time()-t0)
    print(Fore.GREEN + f"  Legistar      : {len(items):4d} items  ({time.time()-t0:.1f}s)")
except Exception as e:
    results["Legistar"] = (0, 0)
    print(Fore.RED + f"  Legistar      : ERROR — {e}")

# PrimeGov
try:
    from scrapers.primegov import scrape_primegov
    items = []; t0 = time.time()
    scrape_primegov("California", items, 200)
    results["PrimeGov"] = (len(items), time.time()-t0)
    print(Fore.GREEN + f"  PrimeGov      : {len(items):4d} items  ({time.time()-t0:.1f}s)")
except Exception as e:
    print(Fore.RED + f"  PrimeGov      : ERROR — {e}")

# CivicPlus
try:
    from scrapers.civicplus import scrape_civicplus
    items = []; t0 = time.time()
    scrape_civicplus("California", items, 200)
    results["CivicPlus"] = (len(items), time.time()-t0)
    print(Fore.GREEN + f"  CivicPlus     : {len(items):4d} items  ({time.time()-t0:.1f}s)")
except Exception as e:
    print(Fore.RED + f"  CivicPlus     : ERROR — {e}")

# Granicus
try:
    from scrapers.granicus import scrape_granicus
    items = []; t0 = time.time()
    scrape_granicus("California", items, 200)
    results["Granicus"] = (len(items), time.time()-t0)
    print(Fore.GREEN + f"  Granicus      : {len(items):4d} items  ({time.time()-t0:.1f}s)")
except Exception as e:
    print(Fore.RED + f"  Granicus      : ERROR — {e}")

# BoardDocs
try:
    from scrapers.boarddocs import scrape_boarddocs
    items = []; t0 = time.time()
    scrape_boarddocs("California", items, 200)
    results["BoardDocs"] = (len(items), time.time()-t0)
    print(Fore.GREEN + f"  BoardDocs     : {len(items):4d} items  ({time.time()-t0:.1f}s)")
except Exception as e:
    print(Fore.RED + f"  BoardDocs     : ERROR — {e}")

# Laserfiche
try:
    from scrapers.laserfiche import scrape_laserfiche
    items = []; t0 = time.time()
    scrape_laserfiche("California", items, 200)
    results["Laserfiche"] = (len(items), time.time()-t0)
    color = Fore.GREEN if len(items) > 0 else Fore.YELLOW
    print(color + f"  Laserfiche    : {len(items):4d} items  ({time.time()-t0:.1f}s)")
except Exception as e:
    print(Fore.RED + f"  Laserfiche    : ERROR — {e}")

# Novus
try:
    from scrapers.novus import scrape_novus
    items = []; t0 = time.time()
    scrape_novus("California", items, 200)
    results["Novus"] = (len(items), time.time()-t0)
    print(Fore.GREEN + f"  Novus         : {len(items):4d} items  ({time.time()-t0:.1f}s)")
except Exception as e:
    print(Fore.RED + f"  Novus         : ERROR — {e}")

print()
print(Fore.CYAN + "="*60)
total = sum(v[0] for v in results.values())
print(Fore.GREEN + f"  Total items found: {total}")
print()
working = [(k,v[0]) for k,v in results.items() if v[0] > 0]
broken  = [(k,v[0]) for k,v in results.items() if v[0] == 0]
if working:
    print(Fore.GREEN + f"  Working: {', '.join(k for k,_ in working)}")
if broken:
    print(Fore.RED   + f"  Returning 0: {', '.join(k for k,_ in broken)}")
print(Fore.CYAN + "="*60)
print()
