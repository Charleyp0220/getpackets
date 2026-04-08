"""
sync_db.py — syncs the database with what's actually on disk.

- Removes DB records for PDFs that no longer exist on disk
- Reports mismatches
- Safe to run anytime

Run with: python sync_db.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_conn, init_db, get_stats
from constants import PACKETS_DIR
from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)

def ok(m):   print(Fore.GREEN  + "  ✔ " + Style.RESET_ALL + m)
def warn(m): print(Fore.YELLOW + "  ⚠ " + Style.RESET_ALL + m)
def info(m): print(Fore.CYAN   + "  ℹ " + Style.RESET_ALL + m)

init_db()
conn = get_conn()

print()
print(Fore.CYAN + "=" * 55)
print(Fore.CYAN + "  GETPACKETS DB SYNC")
print(Fore.CYAN + "=" * 55)
print()

# Get all packets from DB
packets = conn.execute("SELECT id, filename, local_path, status FROM packets").fetchall()
info(f"Total packets in DB: {len(packets)}")

# Check which files exist on disk
disk_files = set()
if os.path.exists(PACKETS_DIR):
    disk_files = set(os.listdir(PACKETS_DIR))
info(f"PDF files on disk: {len(disk_files)}")
print()

# Find records with missing files
missing = []
for p in packets:
    fname = p["filename"]
    lpath = p["local_path"]
    # Check by filename or full path
    on_disk = (fname in disk_files or
               (lpath and os.path.exists(lpath)) or
               fname.replace(".failed", "") in disk_files)
    if not on_disk:
        missing.append(p)

if missing:
    warn(f"Found {len(missing)} DB records with no file on disk")
    print()
    for p in missing[:10]:
        print(f"    [{p['id']}] {p['filename'][:60]}")
    if len(missing) > 10:
        print(f"    ... and {len(missing)-10} more")
    print()

    # Remove orphaned records
    ans = input("  Remove these records from database? (y/n): ").strip().lower()
    if ans == 'y':
        for p in missing:
            # Also remove the meeting if it has no other packets
            conn.execute("DELETE FROM packets WHERE id=?", (p["id"],))
        conn.commit()

        # Clean up meetings with no packets
        conn.execute("""
            DELETE FROM meetings WHERE id NOT IN (
                SELECT DISTINCT meeting_id FROM packets
            )
        """)
        conn.commit()
        ok(f"Removed {len(missing)} orphaned records")
else:
    ok("Database is in sync with disk — no orphaned records")

# Final stats
s_after = get_stats()
print()
ok(f"Database now: {s_after['total_packets']} active | "
   f"{s_after['archived_packets']} archived | "
   f"{s_after['total_links']} links")

conn.close()
print()
