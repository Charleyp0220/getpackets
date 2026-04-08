"""
auto_discover.py — runs automatically to find new packet sources.

Runs 4 discovery engines in parallel:
1. Legistar slug brute-forcer — tests new city name patterns
2. Granicus subdomain finder — tests {city}.granicus.com
3. CivicClerk finder — tests {city}.civicclerk.com (new platform)
4. API endpoint scanner — finds open government APIs from data.gov

Schedule this to run weekly via cron:
  0 2 * * 1 cd ~/Downloads/getpackets && source venv/bin/activate && python auto_discover.py
"""

import sys, os, requests, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0.0.0"}
TIMEOUT = 6

# ── 1. Legistar slug discovery ────────────────────────────────────────────────
def discover_legistar():
    from scrapers.legistar import LEGISTAR_CITIES
    existing = set(LEGISTAR_CITIES.keys())

    # Generate candidates from US city/county names
    import re
    candidates = []

    # Load from municipalities list
    try:
        from municipalities import load_municipalities
        places = load_municipalities()
        for p in places:
            name = p["name"].lower()
            state = p["state"]
            # Generate slug variants
            raw = re.sub(r"[^a-z0-9]", "", name)
            hyph = re.sub(r"\s+", "-", name.strip())
            for slug in [raw, hyph, f"cityof{raw}", f"townof{raw}",
                         f"{raw}city", f"{raw}gov"]:
                if slug not in existing and len(slug) > 2:
                    candidates.append((slug, state, p["name"]))
    except Exception:
        pass

    # Test in parallel
    def test(args):
        slug, state, name = args
        try:
            r = requests.get(
                f"https://webapi.legistar.com/v1/{slug}/Events?$top=1",
                headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200 and len(r.content) > 50:
                ct = r.headers.get("Content-Type", "")
                if "json" in ct or "xml" in ct:
                    return (slug, state, name)
        except Exception:
            pass
        return None

    # Deduplicate
    seen = set()
    unique = [(s, st, n) for s, st, n in candidates
              if s not in existing and s not in seen and not seen.add(s)]

    found = []
    print(f"\n  [Legistar] Testing {len(unique)} candidates...")
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(test, c): c for c in unique[:500]}
        for future in as_completed(futures):
            result = future.result()
            if result:
                found.append(result)
                print(Fore.GREEN + f"  FOUND slug: {result[0]} ({result[2]}, {result[1]})")

    if found:
        # Auto-add to legistar.py
        with open("scrapers/legistar.py", "r") as f:
            content = f.read()
        additions = "\n    # Auto-discovered\n"
        for slug, state, name in found:
            if f'"{slug}"' not in content:
                additions += f'    "{slug}":{" "*(25-len(slug))}("{state}", "{name}"),\n'
        content = content.replace("}\n\n# ── Lookup", additions + "}\n\n# ── Lookup")
        with open("scrapers/legistar.py", "w") as f:
            f.write(content)
        print(Fore.GREEN + f"  [Legistar] Added {len(found)} new slugs")

    return found


# ── 2. Granicus subdomain finder ──────────────────────────────────────────────
def discover_granicus():
    from scrapers.legistar import LEGISTAR_CITIES
    import re

    # Build candidate list from known city names
    candidates = set()
    for slug, (state, name) in LEGISTAR_CITIES.items():
        raw = re.sub(r"[^a-z0-9]", "", name.lower())
        hyph = re.sub(r"\s+", "-", name.lower().strip())
        candidates.add((raw, state, name))
        candidates.add((hyph, state, name))

    def test(args):
        slug, state, name = args
        url = f"https://{slug}.granicus.com/ViewPublisher.php?view_id=1"
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200 and "granicus" in r.text.lower():
                return (slug, state, name)
        except Exception:
            pass
        return None

    found = []
    print(f"\n  [Granicus] Testing {len(candidates)} candidates...")
    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(test, c): c for c in candidates}
        for future in as_completed(futures):
            result = future.result()
            if result:
                found.append(result)
                print(Fore.GREEN + f"  FOUND Granicus: {result[0]}.granicus.com ({result[2]})")

    if found:
        # Add to granicus.py
        with open("scrapers/granicus.py", "r") as f:
            content = f.read()
        additions = "\n    # Auto-discovered\n"
        for slug, state, name in found:
            if f'"{slug}"' not in content:
                additions += f'    "{slug}":{" "*(20-len(slug))}("{state}", "{name}", 1),\n'
        content = content.replace("}\n\nGRANICUS_BASE", additions + "}\n\nGRANICUS_BASE")
        with open("scrapers/granicus.py", "w") as f:
            f.write(content)
        print(Fore.GREEN + f"  [Granicus] Added {len(found)} new cities")

    return found


# ── 3. CivicClerk finder ──────────────────────────────────────────────────────
def discover_civicclerk():
    """
    CivicClerk is a growing platform used by hundreds of cities.
    URL: https://www.civicclerk.com/web/{city}/home.aspx
    or:  https://{city}.civicclerk.com
    """
    from scrapers.legistar import LEGISTAR_CITIES
    import re

    candidates = []
    for slug, (state, name) in LEGISTAR_CITIES.items():
        raw = re.sub(r"[^a-z0-9]", "", name.lower())
        candidates.append((raw, state, name))

    def test(args):
        slug, state, name = args
        for url in [
            f"https://www.civicclerk.com/web/{slug}/home.aspx",
            f"https://{slug}.civicclerk.com/web/home.aspx",
        ]:
            try:
                r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                if r.status_code == 200 and "civicclerk" in r.text.lower():
                    return (slug, state, name, url)
            except Exception:
                pass
        return None

    found = []
    print(f"\n  [CivicClerk] Testing {len(candidates)} candidates...")
    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(test, c): c for c in candidates}
        for future in as_completed(futures):
            result = future.result()
            if result:
                found.append(result)
                print(Fore.GREEN + f"  FOUND CivicClerk: {result[2]} ({result[1]})")

    if found:
        print(Fore.GREEN + f"  [CivicClerk] Found {len(found)} cities — adding scraper...")
        _write_civicclerk_entries(found)

    return found


def _write_civicclerk_entries(found):
    """Add found CivicClerk cities to a new scraper file."""
    scraper_path = "scrapers/civicclerk.py"
    entries = "\n".join(
        f'    ("{slug}", "{state}", "{name}", "{url}"),'
        for slug, state, name, url in found
    )

    template = f'''"""
scrapers/civicclerk.py — CivicClerk scraper (auto-generated).
"""
import requests, re
from datetime import date
from bs4 import BeautifulSoup
from utils import classify_body, is_future_or_today, parse_date, date_str, download_packet
from constants import HEADERS, REQUEST_TIMEOUT
from datetime import timedelta

CIVICCLERK_CITIES = [
{entries}
]

def scrape_civicclerk(state, collected, max_packets):
    cities = [(sl,st,n,u) for sl,st,n,u in CIVICCLERK_CITIES if st==state]
    added = 0
    cutoff = date.today() + timedelta(days=60)
    for slug, st, municipality, base_url in cities:
        if len(collected) >= max_packets:
            break
        try:
            r = requests.get(base_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.select("a[href$='.pdf'], a[href*='agenda']"):
                if len(collected) >= max_packets:
                    break
                href = a["href"]
                label = a.get_text(strip=True)
                body_type = classify_body(label)
                if not body_type:
                    continue
                if not href.startswith("http"):
                    href = base_url.rstrip("/") + "/" + href.lstrip("/")
                meeting_date = parse_date(label) or date.today()
                if not is_future_or_today(meeting_date):
                    continue
                if meeting_date > cutoff:
                    continue
                dl = download_packet(href, st, municipality, body_type, date_str(meeting_date))
                if not dl or dl.get("failed"):
                    continue
                collected.append({{
                    "state": st, "municipality": municipality,
                    "place_type": "city", "body_name": label[:80],
                    "body_type": body_type, "meeting_date": date_str(meeting_date),
                    "meeting_time": "", "location": "",
                    "source_url": base_url, "platform": "CivicClerk",
                    **dl,
                }})
                added += 1
        except Exception:
            continue
    return added
'''
    with open(scraper_path, "w") as f:
        f.write(template)
    print(Fore.GREEN + f"  Written {scraper_path}")


# ── 4. data.gov API scanner ───────────────────────────────────────────────────
def discover_datagov_apis():
    """
    data.gov lists thousands of government datasets and APIs.
    Search for agenda/meeting related datasets.
    """
    print(f"\n  [data.gov] Scanning for meeting/agenda APIs...")
    found = []
    try:
        r = requests.get(
            "https://catalog.data.gov/api/3/action/package_search"
            "?q=agenda+minutes+planning+zoning&rows=50&fq=res_format:PDF",
            headers=HEADERS, timeout=10
        )
        if r.status_code != 200:
            return found

        data = r.json()
        results = data.get("result", {}).get("results", [])

        for pkg in results:
            title = pkg.get("title", "")
            org   = pkg.get("organization", {}).get("title", "") if pkg.get("organization") else ""
            for res in pkg.get("resources", []):
                url = res.get("url", "")
                fmt = res.get("format", "").lower()
                if fmt == "pdf" and url and ".gov" in url:
                    found.append((title, org, url))
                    print(Fore.CYAN + f"  API: {org} — {title[:50]}")

    except Exception as e:
        print(f"  data.gov error: {e}")

    print(f"  [data.gov] Found {len(found)} PDF sources")
    return found


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print(Fore.CYAN + "="*60)
    print(Fore.CYAN + "  AUTO DISCOVER — finding new packet sources")
    print(Fore.CYAN + "="*60)

    total_found = 0

    # Run all discovery engines
    print(Fore.YELLOW + "\n── Legistar slug discovery ──")
    legistar_found = discover_legistar()
    total_found += len(legistar_found)

    print(Fore.YELLOW + "\n── Granicus subdomain discovery ──")
    granicus_found = discover_granicus()
    total_found += len(granicus_found)

    print(Fore.YELLOW + "\n── CivicClerk discovery ──")
    civicclerk_found = discover_civicclerk()
    total_found += len(civicclerk_found)

    print(Fore.YELLOW + "\n── data.gov API scan ──")
    datagov_found = discover_datagov_apis()
    total_found += len(datagov_found)

    print()
    print(Fore.GREEN + "="*60)
    print(Fore.GREEN + f"  Total new sources found: {total_found}")
    print(Fore.GREEN + f"    Legistar slugs  : {len(legistar_found)}")
    print(Fore.GREEN + f"    Granicus cities : {len(granicus_found)}")
    print(Fore.GREEN + f"    CivicClerk cities: {len(civicclerk_found)}")
    print(Fore.GREEN + f"    data.gov APIs   : {len(datagov_found)}")
    print(Fore.GREEN + "="*60)
    print()
    print(Fore.CYAN + "  Run python run.py to collect from all new sources")
    print()
