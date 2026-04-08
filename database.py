"""
database.py — SQLite storage for GetPackets.

Features:
  - Duplicate prevention via UNIQUE constraints
  - Archive / delete support for packets
  - is_new flag (true for 48 hours after download)
"""

import sqlite3, os
from datetime import datetime, timedelta
from constants import DB_FILE

NEW_HOURS = 48  # packets are "new" for this many hours after download


def get_conn():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS meetings (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            state         TEXT NOT NULL,
            municipality  TEXT NOT NULL,
            place_type    TEXT NOT NULL DEFAULT 'city',
            body_name     TEXT NOT NULL,
            body_type     TEXT NOT NULL,
            meeting_date  TEXT NOT NULL,
            meeting_time  TEXT,
            location      TEXT,
            source_url    TEXT,
            platform      TEXT,
            scraped_at    TEXT NOT NULL,
            UNIQUE(municipality, state, body_type, meeting_date)
        );

        CREATE TABLE IF NOT EXISTS packets (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id    INTEGER REFERENCES meetings(id),
            filename      TEXT NOT NULL UNIQUE,
            local_path    TEXT NOT NULL,
            file_url      TEXT,
            file_size_kb  REAL,
            downloaded_at TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'active',
            archived_at   TEXT
        );

        CREATE TABLE IF NOT EXISTS manual_links (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            state         TEXT NOT NULL,
            municipality  TEXT NOT NULL,
            place_type    TEXT NOT NULL DEFAULT 'city',
            meeting_url   TEXT NOT NULL,
            found_at      TEXT NOT NULL,
            UNIQUE(municipality, state, meeting_url)
        );

        CREATE TABLE IF NOT EXISTS run_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at        TEXT NOT NULL,
            state         TEXT NOT NULL,
            packets_found INTEGER DEFAULT 0,
            links_found   INTEGER DEFAULT 0,
            status        TEXT DEFAULT 'ok'
        );

        CREATE TABLE IF NOT EXISTS recycle_bin (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            orig_packet_id INTEGER,
            state         TEXT NOT NULL,
            municipality  TEXT NOT NULL,
            body_type     TEXT NOT NULL,
            body_name     TEXT NOT NULL,
            meeting_date  TEXT NOT NULL,
            filename      TEXT NOT NULL,
            local_path    TEXT,
            file_url      TEXT,
            file_size_kb  REAL,
            platform      TEXT,
            source_url    TEXT,
            deleted_at    TEXT NOT NULL,
            expires_at    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS skip_list (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            state         TEXT NOT NULL,
            municipality  TEXT NOT NULL,
            body_type     TEXT NOT NULL,
            meeting_date  TEXT NOT NULL,
            file_url      TEXT,
            filename      TEXT,
            reason        TEXT DEFAULT 'deleted',
            added_at      TEXT NOT NULL,
            UNIQUE(municipality, state, body_type, meeting_date)
        );

        CREATE TABLE IF NOT EXISTS url_skip_list (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            url_hash  TEXT NOT NULL UNIQUE,
            file_url  TEXT NOT NULL,
            reason    TEXT DEFAULT 'deleted',
            added_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS search_sessions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at    TEXT NOT NULL,
            stopped_at    TEXT,
            packets_found INTEGER DEFAULT 0,
            status        TEXT DEFAULT 'running'
        );

        CREATE TABLE IF NOT EXISTS failed_downloads (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            state         TEXT NOT NULL,
            municipality  TEXT NOT NULL,
            body_type     TEXT NOT NULL,
            meeting_date  TEXT NOT NULL,
            file_url      TEXT NOT NULL,
            source_url    TEXT,
            error         TEXT,
            attempted_at  TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def meeting_exists(municipality, state, body_type, meeting_date):
    conn = get_conn()
    row = conn.execute(
        """SELECT id FROM meetings
           WHERE municipality=? AND state=? AND body_type=? AND meeting_date=?""",
        (municipality, state, body_type, meeting_date)
    ).fetchone()
    conn.close()
    return row is not None


def packet_exists(filename):
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM packets WHERE filename=?", (filename,)
    ).fetchone()
    conn.close()
    return row is not None


def insert_meeting(state, municipality, place_type, body_name, body_type,
                   meeting_date, meeting_time, location, source_url, platform):
    conn = get_conn()
    c = conn.cursor()
    existing = c.execute(
        """SELECT id FROM meetings
           WHERE municipality=? AND state=? AND body_type=? AND meeting_date=?""",
        (municipality, state, body_type, meeting_date)
    ).fetchone()
    if existing:
        conn.close()
        return existing["id"]
    c.execute("""
        INSERT OR IGNORE INTO meetings
          (state,municipality,place_type,body_name,body_type,
           meeting_date,meeting_time,location,source_url,platform,scraped_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (state, municipality, place_type, body_name, body_type,
          meeting_date, meeting_time, location, source_url, platform,
          datetime.now().isoformat()))
    mid = c.lastrowid or c.execute(
        """SELECT id FROM meetings
           WHERE municipality=? AND state=? AND body_type=? AND meeting_date=?""",
        (municipality, state, body_type, meeting_date)
    ).fetchone()["id"]
    conn.commit()
    conn.close()
    return mid


def insert_packet(meeting_id, filename, local_path, file_url, file_size_kb):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO packets
          (meeting_id,filename,local_path,file_url,file_size_kb,downloaded_at,status)
        VALUES (?,?,?,?,?,?,?)
    """, (meeting_id, filename, local_path, file_url, file_size_kb,
          datetime.now().isoformat(), "active"))
    conn.commit()
    conn.close()


def insert_manual_link(state, municipality, place_type, meeting_url):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO manual_links
          (state,municipality,place_type,meeting_url,found_at)
        VALUES (?,?,?,?,?)
    """, (state, municipality, place_type, meeting_url,
          datetime.now().isoformat()))
    conn.commit()
    conn.close()


def archive_packet(packet_id: int):
    """Mark a packet as archived (hidden from main view but not deleted)."""
    conn = get_conn()
    conn.execute(
        "UPDATE packets SET status='archived', archived_at=? WHERE id=?",
        (datetime.now().isoformat(), packet_id)
    )
    conn.commit()
    conn.close()


def unarchive_packet(packet_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE packets SET status='active', archived_at=NULL WHERE id=?",
        (packet_id,)
    )
    conn.commit()
    conn.close()


def delete_packet(packet_id: int, delete_file: bool = False):
    """Remove a packet from the database. Optionally delete the file too."""
    conn = get_conn()
    if delete_file:
        row = conn.execute(
            "SELECT local_path FROM packets WHERE id=?", (packet_id,)
        ).fetchone()
        if row:
            try:
                import os
                if os.path.exists(row["local_path"]):
                    os.remove(row["local_path"])
            except Exception:
                pass
    conn.execute("DELETE FROM packets WHERE id=?", (packet_id,))
    conn.commit()
    conn.close()



def save_failed_download(state, municipality, body_type, meeting_date,
                         file_url, source_url, error):
    """Save a failed PDF download so user can visit the URL manually."""
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO failed_downloads
          (state,municipality,body_type,meeting_date,file_url,source_url,error,attempted_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (state, municipality, body_type, meeting_date,
          file_url, source_url, error,
          datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_failed_downloads(search="", state_filter=""):
    conn = get_conn()
    q = "SELECT * FROM failed_downloads WHERE 1=1"
    params = []
    if search:
        q += " AND (municipality LIKE ? OR state LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if state_filter:
        q += " AND state=?"
        params.append(state_filter)
    q += " ORDER BY attempted_at DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_run(state, packets_found=0, links_found=0, status="ok"):
    conn = get_conn()
    conn.execute(
        """INSERT INTO run_log
           (run_at,state,packets_found,links_found,status)
           VALUES (?,?,?,?,?)""",
        (datetime.now().isoformat(), state, packets_found, links_found, status)
    )
    conn.commit()
    conn.close()


def start_session() -> int:
    """Create a new search session. Returns session id."""
    conn = get_conn()
    c = conn.execute(
        "INSERT INTO search_sessions (started_at, status) VALUES (?, 'running')",
        (datetime.now().isoformat(),)
    )
    sid = c.lastrowid
    conn.commit()
    conn.close()
    return sid


def stop_session(session_id: int, packets_found: int):
    """Mark a session as stopped."""
    conn = get_conn()
    conn.execute(
        """UPDATE search_sessions
           SET stopped_at=?, packets_found=?, status='stopped'
           WHERE id=?""",
        (datetime.now().isoformat(), packets_found, session_id)
    )
    conn.commit()
    conn.close()


def get_sessions():
    """Get all search sessions newest first."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM search_sessions ORDER BY started_at DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_current_session():
    """Get the currently running session if any."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM search_sessions WHERE status='running' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_packets_for_session(session_id: int):
    """Get packets collected in a specific session by matching download time."""
    conn = get_conn()
    session = conn.execute(
        "SELECT * FROM search_sessions WHERE id=?", (session_id,)
    ).fetchone()
    if not session:
        conn.close()
        return []
    started = session["started_at"]
    stopped = session["stopped_at"] or datetime.now().isoformat()
    rows = conn.execute("""
        SELECT p.*, m.municipality, m.state, m.body_type, m.meeting_date,
               m.body_name, m.platform
        FROM packets p
        JOIN meetings m ON m.id = p.meeting_id
        WHERE p.downloaded_at >= ? AND p.downloaded_at <= ?
        ORDER BY p.downloaded_at DESC
    """, (started, stopped)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_all_packets(delete_files: bool = False):
    """Delete all packets and meetings from database."""
    conn = get_conn()
    if delete_files:
        rows = conn.execute("SELECT local_path FROM packets").fetchall()
        import os
        for r in rows:
            try:
                if r["local_path"] and os.path.exists(r["local_path"]):
                    os.remove(r["local_path"])
            except Exception:
                pass
    conn.execute("DELETE FROM packets")
    conn.execute("DELETE FROM meetings")
    conn.execute("DELETE FROM manual_links")
    conn.execute("DELETE FROM failed_downloads")
    conn.commit()
    conn.close()


def move_to_recycle(packet_id: int, keep_days: int = 7):
    """Move a packet to the recycle bin instead of deleting permanently."""
    from datetime import timedelta
    conn = get_conn()
    # Get packet + meeting info
    row = conn.execute("""
        SELECT p.*, m.state, m.municipality, m.body_type, m.body_name,
               m.meeting_date, m.platform, m.source_url
        FROM packets p
        JOIN meetings m ON m.id = p.meeting_id
        WHERE p.id=?
    """, (packet_id,)).fetchone()
    if not row:
        conn.close()
        return False

    now     = datetime.now()
    expires = (now + timedelta(days=keep_days)).isoformat()

    # Add to recycle bin
    conn.execute("""
        INSERT OR REPLACE INTO recycle_bin
          (orig_packet_id, state, municipality, body_type, body_name,
           meeting_date, filename, local_path, file_url, file_size_kb,
           platform, source_url, deleted_at, expires_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (packet_id, row["state"], row["municipality"], row["body_type"],
          row["body_name"], row["meeting_date"], row["filename"],
          row["local_path"], row["file_url"], row["file_size_kb"],
          row["platform"], row["source_url"],
          now.isoformat(), expires))

    # Add to skip list so it never downloads again
    conn.execute("""
        INSERT OR IGNORE INTO skip_list
          (state, municipality, body_type, meeting_date, file_url, filename, reason, added_at)
        VALUES (?,?,?,?,?,?,'deleted',?)
    """, (row["state"], row["municipality"], row["body_type"],
          row["meeting_date"], row["file_url"], row["filename"], now.isoformat()))

    # Also add URL to url_skip_list
    if row["file_url"]:
        import hashlib
        url_hash = hashlib.md5(row["file_url"].encode()).hexdigest()
        conn.execute("""
            INSERT OR IGNORE INTO url_skip_list (url_hash, file_url, added_at)
            VALUES (?,?,?)
        """, (url_hash, row["file_url"], now.isoformat()))

    # Also add filename to url_skip_list
    if row["filename"]:
        import hashlib
        fn_hash = hashlib.md5(row["filename"].encode()).hexdigest()
        conn.execute("""
            INSERT OR IGNORE INTO url_skip_list (url_hash, file_url, added_at)
            VALUES (?,?,?)
        """, (fn_hash, row["filename"], now.isoformat()))

    # Remove from active packets
    conn.execute("DELETE FROM packets WHERE id=?", (packet_id,))

    # Clean up meeting if no packets left
    conn.execute("""
        DELETE FROM meetings WHERE id=? AND
        NOT EXISTS (SELECT 1 FROM packets WHERE meeting_id=?)
    """, (row["meeting_id"], row["meeting_id"]))

    conn.commit()
    conn.close()
    return True


def restore_from_recycle(recycle_id: int):
    """Restore a packet from the recycle bin."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM recycle_bin WHERE id=?", (recycle_id,)
    ).fetchone()
    if not row:
        conn.close()
        return False

    # Recreate meeting if needed
    existing = conn.execute("""
        SELECT id FROM meetings
        WHERE municipality=? AND state=? AND body_type=? AND meeting_date=?
    """, (row["municipality"], row["state"], row["body_type"],
          row["meeting_date"])).fetchone()

    if existing:
        mid = existing["id"]
    else:
        c = conn.execute("""
            INSERT INTO meetings
              (state, municipality, place_type, body_name, body_type,
               meeting_date, meeting_time, location, source_url, platform, scraped_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (row["state"], row["municipality"], "city", row["body_name"],
              row["body_type"], row["meeting_date"], "", "",
              row["source_url"] or "", row["platform"] or "",
              datetime.now().isoformat()))
        mid = c.lastrowid

    # Restore packet
    conn.execute("""
        INSERT OR IGNORE INTO packets
          (meeting_id, filename, local_path, file_url, file_size_kb,
           downloaded_at, status)
        VALUES (?,?,?,?,?,?,?)
    """, (mid, row["filename"], row["local_path"], row["file_url"],
          row["file_size_kb"], row["deleted_at"], "active"))

    # Remove from skip list
    conn.execute("""
        DELETE FROM skip_list
        WHERE municipality=? AND state=? AND body_type=? AND meeting_date=?
    """, (row["municipality"], row["state"], row["body_type"], row["meeting_date"]))

    # Remove from recycle bin
    conn.execute("DELETE FROM recycle_bin WHERE id=?", (recycle_id,))

    conn.commit()
    conn.close()
    return True


def empty_recycle_bin():
    """Permanently delete all items in recycle bin."""
    conn = get_conn()
    rows = conn.execute("SELECT local_path FROM recycle_bin").fetchall()
    import os
    for r in rows:
        try:
            if r["local_path"] and os.path.exists(r["local_path"]):
                os.remove(r["local_path"])
        except Exception:
            pass
    conn.execute("DELETE FROM recycle_bin")
    conn.commit()
    conn.close()


def get_recycle_bin(search="", state_filter=""):
    """Get all items in recycle bin."""
    conn = get_conn()
    q = "SELECT * FROM recycle_bin WHERE 1=1"
    params = []
    if search:
        q += " AND (municipality LIKE ? OR state LIKE ? OR body_name LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if state_filter:
        q += " AND state=?"
        params.append(state_filter)
    q += " ORDER BY deleted_at DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def purge_expired_recycle():
    """Remove items from recycle bin that have passed their expiry."""
    conn = get_conn()
    now = datetime.now().isoformat()
    expired = conn.execute(
        "SELECT local_path FROM recycle_bin WHERE expires_at < ?", (now,)
    ).fetchall()
    import os
    for r in expired:
        try:
            if r["local_path"] and os.path.exists(r["local_path"]):
                os.remove(r["local_path"])
        except Exception:
            pass
    result = conn.execute(
        "DELETE FROM recycle_bin WHERE expires_at < ?", (now,)
    )
    conn.commit()
    conn.close()
    return result.rowcount


def is_in_skip_list(municipality: str, state: str,
                    body_type: str, meeting_date: str,
                    file_url: str = "", filename: str = "") -> bool:
    """Check if a packet should be skipped (was previously deleted)."""
    import hashlib
    conn = get_conn()

    # Check by meeting identity
    row = conn.execute("""
        SELECT id FROM skip_list
        WHERE municipality=? AND state=? AND body_type=? AND meeting_date=?
    """, (municipality, state, body_type, meeting_date)).fetchone()
    if row:
        conn.close()
        return True

    # Check by URL hash
    if file_url:
        url_hash = hashlib.md5(file_url.encode()).hexdigest()
        row2 = conn.execute(
            "SELECT id FROM url_skip_list WHERE url_hash=?", (url_hash,)
        ).fetchone()
        if row2:
            conn.close()
            return True

    # Check by filename hash
    if filename:
        fn_hash = hashlib.md5(filename.encode()).hexdigest()
        row3 = conn.execute(
            "SELECT id FROM url_skip_list WHERE url_hash=?", (fn_hash,)
        ).fetchone()
        if row3:
            conn.close()
            return True

    conn.close()
    return False


def delete_oldest_packets(n: int, delete_files: bool = False):
    """Move the oldest N packets to recycle bin."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.id FROM packets p
        JOIN meetings m ON m.id = p.meeting_id
        WHERE p.status = 'active'
        ORDER BY p.downloaded_at ASC
        LIMIT ?
    """, (n,)).fetchall()
    conn.close()
    count = 0
    for row in rows:
        if move_to_recycle(row["id"]):
            count += 1
    return count


def delete_all_packets(delete_files: bool = False):
    """Move ALL packets to recycle bin."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id FROM packets WHERE status='active'"
    ).fetchall()
    conn.close()
    count = 0
    for row in rows:
        if move_to_recycle(row["id"]):
            count += 1
    return count


def get_all_meetings(search="", body_filter="", state_filter="",
                     show_archived=False, date_from="", date_to=""):
    conn = get_conn()
    archived_clause = "" if show_archived else \
        " AND (p.status='active' OR p.status IS NULL)"
    q = f"""
        SELECT m.*,
               COUNT(CASE WHEN p.status='active' THEN 1 END) as packet_count,
               COUNT(CASE WHEN p.status='archived' THEN 1 END) as archived_count,
               MAX(p.downloaded_at) as last_downloaded
        FROM meetings m
        LEFT JOIN packets p ON p.meeting_id = m.id
        WHERE 1=1
    """
    params = []
    if search:
        q += " AND (m.municipality LIKE ? OR m.body_name LIKE ? OR m.state LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if body_filter:
        q += " AND m.body_type=?"
        params.append(body_filter)
    if state_filter:
        q += " AND m.state=?"
        params.append(state_filter)
    if date_from:
        q += " AND m.meeting_date >= ?"
        params.append(date_from)
    if date_to:
        q += " AND m.meeting_date <= ?"
        params.append(date_to)
    q += " GROUP BY m.id HAVING packet_count > 0"
    q += " ORDER BY m.scraped_at DESC, m.meeting_date ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()

    cutoff = (datetime.now() - timedelta(hours=NEW_HOURS)).isoformat()
    result = []
    for r in rows:
        d = dict(r)
        d["is_new"] = (d.get("last_downloaded") or "") > cutoff
        result.append(d)
    return result


def get_archived_meetings(search="", state_filter=""):
    conn = get_conn()
    q = """
        SELECT m.*,
               COUNT(p.id) as packet_count,
               0 as archived_count,
               MAX(p.archived_at) as last_archived,
               MAX(p.downloaded_at) as last_downloaded
        FROM meetings m
        JOIN packets p ON p.meeting_id = m.id
        WHERE p.status='archived'
    """
    params = []
    if search:
        q += " AND (m.municipality LIKE ? OR m.state LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if state_filter:
        q += " AND m.state=?"
        params.append(state_filter)
    q += " GROUP BY m.id ORDER BY last_archived DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    # Add is_new field so template doesn't crash
    result = []
    for r in rows:
        d = dict(r)
        d["is_new"] = False
        result.append(d)
    return result


def get_all_manual_links(search="", state_filter=""):
    conn = get_conn()
    q = "SELECT * FROM manual_links WHERE 1=1"
    params = []
    if search:
        q += " AND (municipality LIKE ? OR state LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if state_filter:
        q += " AND state=?"
        params.append(state_filter)
    q += " ORDER BY state, municipality"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_packets_for_meeting(meeting_id, include_archived=False):
    conn = get_conn()
    if include_archived:
        rows = conn.execute(
            "SELECT * FROM packets WHERE meeting_id=? ORDER BY downloaded_at DESC",
            (meeting_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM packets WHERE meeting_id=?
               AND status='active' ORDER BY downloaded_at DESC""",
            (meeting_id,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_packet_by_id(packet_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM packets WHERE id=?", (packet_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_stats():
    conn = get_conn()
    cutoff = (datetime.now() - timedelta(hours=NEW_HOURS)).isoformat()
    stats = {
        "total_packets":   conn.execute(
            "SELECT COUNT(*) FROM packets WHERE status='active'").fetchone()[0],
        "archived_packets":conn.execute(
            "SELECT COUNT(*) FROM packets WHERE status='archived'").fetchone()[0],
        "new_packets":     conn.execute(
            "SELECT COUNT(*) FROM packets WHERE status='active' AND downloaded_at>?",
            (cutoff,)).fetchone()[0],
        "total_meetings":  conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0],
        "total_links":     conn.execute("SELECT COUNT(*) FROM manual_links").fetchone()[0],
        "states_covered":  conn.execute(
            "SELECT COUNT(DISTINCT state) FROM meetings").fetchone()[0],
        "body_breakdown":  [dict(r) for r in conn.execute("""
            SELECT body_type, COUNT(*) as cnt FROM meetings
            GROUP BY body_type ORDER BY cnt DESC
        """).fetchall()],
        "distinct_states": [r[0] for r in conn.execute(
            "SELECT DISTINCT state FROM meetings ORDER BY state"
        ).fetchall()],
        "link_states": [r[0] for r in conn.execute(
            "SELECT DISTINCT state FROM manual_links ORDER BY state"
        ).fetchall()],
    }
    conn.close()
    return stats


# ── Keywords management ───────────────────────────────────────────────────────

def get_keywords() -> list:
    """Get all user-defined keywords from database."""
    conn = get_conn()
    # Create keywords table if not exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_keywords (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword    TEXT NOT NULL UNIQUE,
            category   TEXT DEFAULT 'custom',
            added_at   TEXT NOT NULL
        )
    """)
    conn.commit()
    rows = conn.execute(
        "SELECT * FROM user_keywords ORDER BY category, keyword"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_keyword(keyword: str, category: str = "custom") -> bool:
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_keywords (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword    TEXT NOT NULL UNIQUE,
            category   TEXT DEFAULT 'custom',
            added_at   TEXT NOT NULL
        )
    """)
    try:
        conn.execute(
            "INSERT INTO user_keywords (keyword, category, added_at) VALUES (?,?,?)",
            (keyword.lower().strip(), category, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def delete_keyword(keyword_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM user_keywords WHERE id=?", (keyword_id,))
    conn.commit()
    conn.close()


def score_packet(text: str, extra_keywords: list = None) -> dict:
    """
    Score a packet's text for planning relevance.
    Returns score (0-100) and matched keywords.
    """
    from constants import ALL_PLANNING_KEYWORDS
    text_l = text.lower()
    all_kws = list(ALL_PLANNING_KEYWORDS) + (extra_keywords or [])

    matched = [kw for kw in all_kws if kw.lower() in text_l]
    score   = min(100, len(matched) * 8)  # 8 points per keyword, max 100

    # Bonus for high-value terms
    high_value = ["rezoning", "rezone", "variance", "plat", "subdivision",
                  "conditional use", "special use", "annexation", "replat"]
    bonus = sum(10 for hv in high_value if hv in text_l)
    score = min(100, score + bonus)

    return {"score": score, "matched": matched[:15]}


def update_packet_score(packet_id: int, score: int, keywords_found: str):
    """Update a packet's relevance score."""
    conn = get_conn()
    # Add score columns if not exist
    try:
        conn.execute("ALTER TABLE packets ADD COLUMN relevance_score INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE packets ADD COLUMN keywords_found TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    conn.execute(
        "UPDATE packets SET relevance_score=?, keywords_found=? WHERE id=?",
        (score, keywords_found, packet_id)
    )
    conn.commit()
    conn.close()


def get_packets_with_scores(meeting_id: int) -> list:
    conn = get_conn()
    rows = conn.execute("""
        SELECT *, COALESCE(relevance_score, 0) as score
        FROM packets WHERE meeting_id=? AND status='active'
        ORDER BY score DESC, downloaded_at DESC
    """, (meeting_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
