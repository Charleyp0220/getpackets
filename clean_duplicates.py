"""
clean_duplicates.py — removes duplicate entries from the database.

Run this once to clean up any duplicates created before the fix.
Safe to run multiple times — it only removes true duplicates.

Usage:
    python clean_duplicates.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_conn, init_db
from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)

def ok(msg):   print(Fore.GREEN  + "  ✔ " + Style.RESET_ALL + msg)
def info(msg): print(Fore.CYAN   + "  ℹ " + Style.RESET_ALL + msg)
def warn(msg): print(Fore.YELLOW + "  ⚠ " + Style.RESET_ALL + msg)

init_db()
conn = get_conn()

print()
print(Fore.CYAN + "  Cleaning duplicate entries from database...")
print()

# ── Step 1: Remove duplicate meetings ─────────────────────────────────────────
# Keep only the row with the lowest id for each unique combination
before = conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]

conn.execute("""
    DELETE FROM meetings
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM meetings
        GROUP BY municipality, state, body_type, meeting_date
    )
""")
conn.commit()

after = conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
removed = before - after
if removed > 0:
    warn(f"Removed {removed} duplicate meeting row(s)")
else:
    ok("No duplicate meetings found")

# ── Step 2: Remove duplicate packets ──────────────────────────────────────────
before = conn.execute("SELECT COUNT(*) FROM packets").fetchone()[0]

conn.execute("""
    DELETE FROM packets
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM packets
        GROUP BY filename
    )
""")
conn.commit()

after = conn.execute("SELECT COUNT(*) FROM packets").fetchone()[0]
removed = before - after
if removed > 0:
    warn(f"Removed {removed} duplicate packet row(s)")
else:
    ok("No duplicate packets found")

# ── Step 3: Remove duplicate manual links ─────────────────────────────────────
before = conn.execute("SELECT COUNT(*) FROM manual_links").fetchone()[0]

conn.execute("""
    DELETE FROM manual_links
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM manual_links
        GROUP BY municipality, state, meeting_url
    )
""")
conn.commit()

after = conn.execute("SELECT COUNT(*) FROM manual_links").fetchone()[0]
removed = before - after
if removed > 0:
    warn(f"Removed {removed} duplicate link row(s)")
else:
    ok("No duplicate links found")

# ── Step 4: Remove orphaned packets ───────────────────────────────────────────
# Packets whose meeting was deleted
before = conn.execute("SELECT COUNT(*) FROM packets").fetchone()[0]
conn.execute("""
    DELETE FROM packets
    WHERE meeting_id NOT IN (SELECT id FROM meetings)
""")
conn.commit()
after = conn.execute("SELECT COUNT(*) FROM packets").fetchone()[0]
removed = before - after
if removed > 0:
    warn(f"Removed {removed} orphaned packet row(s)")

# ── Final counts ───────────────────────────────────────────────────────────────
print()
meetings = conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
packets  = conn.execute("SELECT COUNT(*) FROM packets").fetchone()[0]
links    = conn.execute("SELECT COUNT(*) FROM manual_links").fetchone()[0]
conn.close()

ok(f"Database now has {meetings} meetings, {packets} packets, {links} links")
print()
