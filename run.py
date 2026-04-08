"""
run.py — GetPackets continuous scraper with master controller.

Scrapers run in priority order (best first).
Performance tracked per scraper per pass.
Broken/slow scrapers auto-detected and skipped.
"""

import os, sys, random, time
from datetime import date
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, Style, init as colorama_init

colorama_init(autoreset=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import MAX_PACKETS
from database  import (init_db, insert_meeting, insert_packet,
                        insert_manual_link, log_run,
                        meeting_exists, packet_exists, get_stats,
                        start_session, stop_session,
                        is_in_skip_list, purge_expired_recycle,
                        move_to_recycle)
from utils     import log_info, log_ok, log_warn, log_err, log_link
from scrapers.legistar              import LEGISTAR_CITIES, scrape_legistar_slug
from scrapers.civicplus             import scrape_civicplus
from scrapers.primegov              import scrape_primegov
from scrapers.boarddocs             import scrape_boarddocs
from scrapers.novus                 import scrape_novus
from scrapers.granicus              import scrape_granicus
from scrapers.custom_sites          import scrape_custom_sites
from scrapers.laserfiche            import scrape_laserfiche
from scrapers.state_portals         import scrape_state_portal
from scrapers.google_pdf_hunt       import scrape_google_pdf_hunt
# Municode disabled — JS-heavy, returns 0
# from scrapers.municode      import scrape_municode

ENABLE_FINDER   = False
INCLUDE_PAST    = True   # collect past 30 days as well as future
TIER1_MIN_ROOM  = 300    # minimum quota for tier 1 scrapers


# ── Save item ─────────────────────────────────────────────────────────────────
def save_item(item: dict) -> bool:
    if item.get("failed"):
        try:
            from database import save_failed_download
            save_failed_download(
                state=item["state"], municipality=item["municipality"],
                body_type=item["body_type"], meeting_date=item["meeting_date"],
                file_url=item.get("file_url",""), source_url=item.get("source_url",""),
                error=item.get("error",""),
            )
        except Exception:
            pass
        return False
    if meeting_exists(item["municipality"], item["state"],
                      item["body_type"], item["meeting_date"]):
        return False
    if packet_exists(item["filename"]):
        return False
    if is_in_skip_list(item["municipality"], item["state"],
                       item["body_type"], item["meeting_date"],
                       file_url=item.get("file_url",""),
                       filename=item.get("filename","")):
        return False
    mid = insert_meeting(
        state=item["state"], municipality=item["municipality"],
        place_type=item.get("place_type","city"), body_name=item["body_name"],
        body_type=item["body_type"], meeting_date=item["meeting_date"],
        meeting_time=item.get("meeting_time",""), location=item.get("location",""),
        source_url=item.get("source_url",""), platform=item.get("platform",""),
    )
    insert_packet(
        meeting_id=mid, filename=item["filename"],
        local_path=item["local_path"], file_url=item.get("file_url",""),
        file_size_kb=item.get("file_size_kb",0),
    )
    return True


# ── Safe retry wrapper ───────────────────────────────────────────────────────
def safe_run(fn, *args):
    """Run a scraper with 2 retries on failure."""
    for attempt in range(2):
        try:
            return fn(*args)
        except Exception as e:
            if attempt == 0:
                log_warn(f"  [RETRY] {fn.__name__}: {e}")
            else:
                log_err(f"  [FAIL]  {fn.__name__}: {e}")
    return 0


# ── Legistar: parallel over ALL known slugs for state ────────────────────────
def run_legistar(state: str, collected: list, max_packets: int,
                 processed: set) -> int:
    slugs = [(slug, name) for slug, (s, name) in LEGISTAR_CITIES.items()
             if s == state]
    if not slugs:
        return 0

    to_run = []
    for slug, name in slugs:
        key = f"{slug}|{date.today()}"
        if key not in processed:
            processed.add(key)
            to_run.append((slug, name))

    if not to_run:
        return 0

    added = 0

    def fetch(args):
        slug, name = args
        items = []
        scrape_legistar_slug(slug, state, name, "city", items, 200)
        return items

    with ThreadPoolExecutor(max_workers=16) as ex:
        futures = {ex.submit(fetch, s): s for s in to_run}
        for future in as_completed(futures):
            if len(collected) >= max_packets:
                break
            try:
                for item in future.result():
                    if len(collected) >= max_packets:
                        break
                    if save_item(item):
                        collected.append(item)
                        added += 1
                        log_ok(f"  ✔ [Legistar] {item['municipality']} "
                               f"— {item['body_type']} — {item['meeting_date']}")
            except Exception:
                pass
    return added


def run_civicplus(state, collected, max_packets):
    items = []
    safe_run(scrape_civicplus, state, items, max_packets - len(collected))
    return _flush(items, collected, max_packets, "CivicPlus")

def _tier1_room(collected, max_packets):
    """Tier 1 scrapers always get at least TIER1_MIN_ROOM quota."""
    return max(TIER1_MIN_ROOM, max_packets - len(collected))

def run_primegov(state, collected, max_packets):
    items = []
    safe_run(scrape_primegov, state, items, _tier1_room(collected, max_packets))
    return _flush(items, collected, max_packets, "PrimeGov")

def run_boarddocs(state, collected, max_packets):
    items = []
    safe_run(scrape_boarddocs, state, items, max_packets - len(collected))
    return _flush(items, collected, max_packets, "BoardDocs")

def run_novus(state, collected, max_packets):
    items = []
    safe_run(scrape_novus, state, items, max_packets - len(collected))
    return _flush(items, collected, max_packets, "Novus")

def run_granicus(state, collected, max_packets):
    items = []
    safe_run(scrape_granicus, state, items, _tier1_room(collected, max_packets))
    return _flush(items, collected, max_packets, "Granicus")

def run_custom(state, collected, max_packets):
    items = []
    safe_run(scrape_custom_sites, state, items, max_packets - len(collected))
    return _flush(items, collected, max_packets, "Custom")

def run_laserfiche(state, collected, max_packets):
    items = []
    safe_run(scrape_laserfiche, state, items, _tier1_room(collected, max_packets))
    return _flush(items, collected, max_packets, "Laserfiche")

def run_texas_open(state, collected, max_packets):
    items = []
    safe_run(scrape_texas_open_meetings, state, items, _tier1_room(collected, max_packets))
    return _flush(items, collected, max_packets, "TX-OpenMeetings")

def run_state_portal(state, collected, max_packets):
    items = []
    safe_run(scrape_state_portal, state, items, _tier1_room(collected, max_packets))
    return _flush(items, collected, max_packets, "StatePortal")

def run_pdf_hunt(state, collected, max_packets):
    """Search engine PDF hunter — finds cities we don't know about."""
    items = []
    safe_run(scrape_google_pdf_hunt, state, items, max_packets - len(collected))
    return _flush(items, collected, max_packets, "WebSearch")

def _flush(items, collected, max_packets, label):
    added = 0
    for item in items:
        if len(collected) >= max_packets:
            break
        if save_item(item):
            collected.append(item)
            added += 1
            log_ok(f"  ✔ [{label}] {item['municipality']} "
                   f"— {item['body_type']} — {item['meeting_date']}")
    return added


# ── Master scraper list — PRIORITY ORDER ──────────────────────────────────────
# Tier 1: Best sources — run first
# Tier 2: Good but inconsistent
# Tier 3: Custom/unpredictable — run last

SCRAPER_PIPELINE = [
    # Tier 1 — structured APIs, highest yield
    ("Legistar",        None),             # parallel, 287+ cities
    ("PrimeGov",        run_primegov),     # structured API
    ("Granicus",        run_granicus),     # strong HTML
    # ("Laserfiche",      run_laserfiche),  # disabled — too slow   # document management, 207 cities
    # ("StatePortal",     run_state_portal),  # disabled — unverified # TX/IL/FL/VA state aggregators
    # ("TX-OpenMeetings", run_texas_open),  # disabled — unverified   # Texas only, all entities
    # Tier 2 — good but inconsistent
    ("CivicPlus",       run_civicplus),
    ("BoardDocs",       run_boarddocs),
    ("Novus",           run_novus),
    # Tier 3 — discovery sources (find unknown cities)
    ("WebSearch",       run_pdf_hunt),     # search engine PDF discovery
    ("Custom",          run_custom),
    # Municode disabled (JS-heavy, returns 0)
]


# ── Per-state scraping with performance tracking ──────────────────────────────
def scrape_state(state, total_packets, processed_legistar):
    perf     = {}   # scraper -> packets found
    collected = []
    max_p    = MAX_PACKETS - total_packets

    for name, fn in SCRAPER_PIPELINE:
        if len(collected) >= max_p:
            break

        before = len(collected)
        t0 = time.time()

        if name == "Legistar":
            run_legistar(state, collected, max_p, processed_legistar)
        else:
            fn(state, collected, max_p)

        found   = len(collected) - before
        elapsed = time.time() - t0
        perf[name] = found

        if found > 0 or elapsed > 2:
            color = Fore.GREEN if found > 0 else Fore.RED
            print(color + f"    {name:12s}: {found:3d} packets  ({elapsed:.1f}s)")

    # ✅ FIXED: Second sweep
    if len(collected) < max_p:
        before2 = len(collected)

        # FIX 1: correct variable
        run_legistar(state, collected, max_p, processed_legistar)

        # FIX 2: actually call function (not just check it)
        run_granicus(state, collected, max_p)

        swept = len(collected) - before2
        if swept > 0:
            perf["SecondSweep"] = swept
            log_ok(f"  Second sweep: +{swept} more packets")

    return collected, perf


# ── Banners ───────────────────────────────────────────────────────────────────
def print_banner():
    print()
    print(Fore.CYAN + "═" * 64)
    print(Fore.CYAN + "  GETPACKETS — CONTINUOUS SCRAPER")
    print(Fore.CYAN + f"  {date.today()}  |  Target: {MAX_PACKETS} packets")
    print(Fore.CYAN + "  Tier 1: Legistar · PrimeGov · Granicus · Laserfiche · StatePortals")
    print(Fore.CYAN + "  Tier 2: CivicPlus · BoardDocs · Novus")
    print(Fore.CYAN + "  Tier 3: WebSearch · Custom")
    print(Fore.CYAN + "  Press Ctrl+C to stop")
    print(Fore.CYAN + "═" * 64)
    print()


def print_pass_header(pass_num, total):
    print()
    print(Fore.MAGENTA + "─" * 64)
    print(Fore.MAGENTA + f"  PASS {pass_num}  |  {total} packets  "
          f"|  {MAX_PACKETS - total} remaining")
    print(Fore.MAGENTA + "─" * 64)


def print_pass_summary(pass_num, pass_pkts, total, all_perf):
    print()
    print(Fore.GREEN + "─" * 64)
    print(Fore.GREEN + f"  Pass {pass_num} complete — +{pass_pkts} packets | {total} total")

    # Per-scraper totals
    totals = defaultdict(int)
    for perf in all_perf:
        for k, v in perf.items():
            totals[k] += v

    if any(v > 0 for v in totals.values()):
        print(Fore.CYAN + "  Scraper performance this pass:")
        for name, count in sorted(totals.items(), key=lambda x: -x[1]):
            if count > 0:
                bar = "█" * min(count, 30)
                print(Fore.CYAN + f"    {name:12s} {count:4d}  {bar}")

    print(Fore.GREEN + "─" * 64)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    init_db()
    print_banner()

    # Get all states that have at least one source
    all_states = set()
    for _, (state, _) in LEGISTAR_CITIES.items():
        all_states.add(state)

    # Add states from other platforms
    try:
        from scrapers.civicplus  import CIVICPLUS_CITIES
        for _, (state, _) in CIVICPLUS_CITIES.items():
            all_states.add(state)
    except Exception:
        pass
    try:
        from scrapers.primegov   import PRIMEGOV_CITIES
        for _, (state, _) in PRIMEGOV_CITIES.items():
            all_states.add(state)
    except Exception:
        pass
    try:
        from scrapers.granicus   import GRANICUS_CITIES
        for _, (state, _, __) in GRANICUS_CITIES.values():
            all_states.add(state)
    except Exception:
        pass
    try:
        from scrapers.boarddocs  import BOARDDOCS_ENTITIES
        for _, __, state, ___ in BOARDDOCS_ENTITIES:
            all_states.add(state)
    except Exception:
        pass

    states = sorted(all_states)
    print(Fore.CYAN + f"  {len(states)} states with sources | "
          f"{len(LEGISTAR_CITIES)} Legistar cities")
    print()

    purged = purge_expired_recycle()
    if purged:
        print(Fore.YELLOW + f"  Purged {purged} expired recycle bin items")

    session_id      = start_session()
    session_packets = 0
    pass_num        = 0
    processed_legistar = set()

    print(Fore.CYAN + f"  Session #{session_id} started")
    print()

    while True:
        s = get_stats()
        total_packets = s["total_packets"]

        if total_packets >= MAX_PACKETS:
            break

        pass_num += 1
        print_pass_header(pass_num, total_packets)

        random.shuffle(states)
        pass_pkts  = 0
        all_perf   = []

        for state in states:
            if total_packets + pass_pkts >= MAX_PACKETS:
                break

            print()
            print(Fore.YELLOW +
                  f"▶ {state:25s} "
                  f"({total_packets + pass_pkts}/{MAX_PACKETS})")

            collected, perf = scrape_state(
                state, total_packets + pass_pkts, processed_legistar
            )

            state_pkts = len(collected)
            pass_pkts += state_pkts
            session_packets += state_pkts
            all_perf.append(perf)

            log_run(state, packets_found=state_pkts, links_found=0)
            time.sleep(0.2)

        total_packets += pass_pkts
        print_pass_summary(pass_num, pass_pkts, total_packets, all_perf)

        if pass_pkts == 0:
            print()
            print(Fore.YELLOW + "  No new packets this pass — waiting 5 minutes...")
            print(Fore.YELLOW + "  New agendas are typically posted Mon–Thu")
            for _ in range(10):
                time.sleep(30)

    stop_session(session_id, session_packets)
    print()
    print(Fore.GREEN + "═" * 64)
    print(Fore.GREEN + f"  DONE — {total_packets} packets collected")
    print(Fore.GREEN + f"  Session #{session_id}: {session_packets} packets")
    print(Fore.GREEN + "═" * 64)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        try:
            stop_session(session_id, session_packets)
        except Exception:
            pass
        s = get_stats()
        print(Fore.YELLOW + f"  Stopped. {s['total_packets']} packets in database.")
        sys.exit(0)
