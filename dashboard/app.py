"""dashboard/app.py — GetPackets dashboard."""

import os, sys, threading, subprocess, collections, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

from flask import Flask, render_template, request, send_file, jsonify, abort
from database import (init_db, get_all_meetings, get_archived_meetings,
                      get_all_manual_links, get_packets_for_meeting,
                      get_packet_by_id, get_stats,
                      archive_packet, unarchive_packet, delete_packet,
                      get_failed_downloads, get_sessions,
                      get_packets_for_session, delete_all_packets,
                      get_recycle_bin, restore_from_recycle,
                      empty_recycle_bin, move_to_recycle,
                      delete_oldest_packets, purge_expired_recycle)

app = Flask(__name__)
init_db()

_proc  = None
_lock  = threading.Lock()
_log   = collections.deque(maxlen=300)
_llock = threading.Lock()
ANSI   = re.compile(r'\x1b\[[0-9;]*m')


def _read(proc):
    for raw in proc.stdout:
        line = ANSI.sub('', raw.decode("utf-8", errors="replace").rstrip())
        if line:
            with _llock:
                _log.append(line)
    with _llock:
        _log.append("── finished ──")


def resolve(path):
    if os.path.isabs(path) and os.path.exists(path):
        return path
    alt = os.path.join(PROJECT_ROOT, path)
    return alt if os.path.exists(alt) else path


@app.route("/")
def index():
    tab          = request.args.get("tab", "packets")
    search       = request.args.get("q", "")
    body_filter  = request.args.get("body", "")
    state_filter = request.args.get("state", "")
    view         = request.args.get("view", "card")
    sort_by      = request.args.get("sort", "newest")
    page         = int(request.args.get("page", 1))
    per_page     = int(request.args.get("per_page", 50))
    show_archive = request.args.get("archived", "0") == "1"

    date_from = request.args.get("date_from", "")
    date_to   = request.args.get("date_to", "")
    pdf_query = request.args.get("pdf_q", "")

    if show_archive:
        meetings = get_archived_meetings(search, state_filter)
    else:
        meetings = get_all_meetings(search, body_filter, state_filter,
                                    date_from=date_from, date_to=date_to)

    # PDF keyword search
    pdf_matches = []
    if pdf_query:
        try:
            from pdf_search import search_packets
            pdf_matches = search_packets(pdf_query)
            if pdf_matches:
                meetings = [m for m in meetings
                           if any(p["id"] in pdf_matches
                                  for p in get_packets_for_meeting(m["id"]))]
        except Exception:
            pass

    links   = get_all_manual_links(search, state_filter)
    failed  = get_failed_downloads(search, state_filter)
    stats   = get_stats()

    sessions = get_sessions()
    recycle  = get_recycle_bin(search, state_filter)
    purge_expired_recycle()

    # Pagination
    total_meetings = len(meetings)
    total_pages    = max(1, (total_meetings + per_page - 1) // per_page)
    page           = max(1, min(page, total_pages))
    start          = (page - 1) * per_page
    meetings_page  = meetings[start:start + per_page]

    # Keywords for dashboard
    from database import get_keywords
    user_keywords = get_keywords()

    return render_template("index.html",
        tab=tab, meetings=meetings_page, links=links, stats=stats,
        failed=failed, sessions=sessions, recycle=recycle,
        user_keywords=user_keywords,
        total_meetings=total_meetings,
        total_pages=total_pages, current_page=page,
        per_page=per_page, sort_by=sort_by,
        search=search, body_filter=body_filter,
        state_filter=state_filter, view=view,
        show_archive=show_archive,
        date_from=date_from, date_to=date_to,
        pdf_query=pdf_query,
    )


# ── Scraper control ───────────────────────────────────────────────────────────
@app.route("/api/scraper/start", methods=["POST"])
def start():
    global _proc
    with _lock:
        if _proc and _proc.poll() is None:
            return jsonify({"status": "already_running"})
        with _llock:
            _log.clear()
            _log.append("── starting GetPackets ──")
        _proc = subprocess.Popen(
            [sys.executable, os.path.join(PROJECT_ROOT, "run.py")],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        threading.Thread(target=_read, args=(_proc,), daemon=True).start()
    return jsonify({"status": "started", "pid": _proc.pid})


@app.route("/api/scraper/stop", methods=["POST"])
def stop():
    global _proc
    with _lock:
        if _proc and _proc.poll() is None:
            _proc.terminate(); _proc.wait()
            with _llock:
                _log.append("── stopped by user ──")
            return jsonify({"status": "stopped"})
    return jsonify({"status": "not_running"})


@app.route("/api/scraper/status")
def status():
    with _lock:
        running = _proc and _proc.poll() is None
        st = "running" if running else ("finished" if _proc else "idle")
    with _llock:
        lines = list(_log)
    return jsonify({"running": running, "status": st, "log": lines})


# ── Packet actions ────────────────────────────────────────────────────────────
@app.route("/api/packet/<int:pid>/archive", methods=["POST"])
def api_archive(pid):
    archive_packet(pid)
    return jsonify({"status": "archived"})

@app.route("/api/packet/<int:pid>/unarchive", methods=["POST"])
def api_unarchive(pid):
    unarchive_packet(pid)
    return jsonify({"status": "active"})

@app.route("/api/packet/<int:pid>/delete", methods=["POST"])
def api_delete(pid):
    # Move to recycle bin instead of permanent delete
    move_to_recycle(pid)
    return jsonify({"status": "recycled"})


@app.route("/api/packet/<int:pid>/delete-permanent", methods=["POST"])
def api_delete_permanent(pid):
    also_file = request.json.get("deleteFile", False) if request.json else False
    delete_packet(pid, delete_file=also_file)
    return jsonify({"status": "deleted"})


# ── File serving ──────────────────────────────────────────────────────────────
@app.route("/view/<int:pid>")
def view_file(pid):
    p = get_packet_by_id(pid)
    if not p: abort(404)
    path = resolve(p["local_path"])
    if not os.path.exists(path):
        abort(404, description=f"File missing: {path}")
    return send_file(path, mimetype="application/pdf",
                     as_attachment=False, download_name=p["filename"])

@app.route("/download/<int:pid>")
def download_file(pid):
    p = get_packet_by_id(pid)
    if not p: abort(404)
    path = resolve(p["local_path"])
    if not os.path.exists(path):
        abort(404, description=f"File missing: {path}")
    return send_file(path, mimetype="application/pdf",
                     as_attachment=True, download_name=p["filename"])

@app.route("/meeting/<int:mid>")
def meeting_detail(mid):
    include = request.args.get("archived", "0") == "1"
    return jsonify(get_packets_for_meeting(mid, include_archived=include))

@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())



@app.route("/api/pdf-search")
def pdf_search_api():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"matches": []})
    try:
        from pdf_search import search_packets, get_packet_keywords
        matches = search_packets(query)
        return jsonify({"matches": matches, "count": len(matches)})
    except Exception as e:
        return jsonify({"matches": [], "error": str(e)})


@app.route("/api/index-pdfs", methods=["POST"])
def index_pdfs():
    try:
        from pdf_search import index_all_pdfs
        import threading
        threading.Thread(target=index_all_pdfs, daemon=True).start()
        return jsonify({"status": "indexing started"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route("/api/packets/bulk-delete", methods=["POST"])
def bulk_delete():
    data = request.json or {}
    ids  = data.get("ids", [])
    also_file = data.get("deleteFile", False)
    for pid in ids:
        try:
            delete_packet(int(pid), delete_file=also_file)
        except Exception:
            pass
    return jsonify({"status": "deleted", "count": len(ids)})


@app.route("/api/packets/bulk-archive", methods=["POST"])
def bulk_archive():
    data = request.json or {}
    ids  = data.get("ids", [])
    for pid in ids:
        try:
            archive_packet(int(pid))
        except Exception:
            pass
    return jsonify({"status": "archived", "count": len(ids)})


# ── Keywords ──────────────────────────────────────────────────────────────────
@app.route("/api/keywords")
def api_get_keywords():
    from database import get_keywords
    return jsonify(get_keywords())

@app.route("/api/keywords/add", methods=["POST"])
def api_add_keyword():
    from database import add_keyword
    data = request.json or {}
    kw  = data.get("keyword", "").strip()
    cat = data.get("category", "custom")
    if not kw:
        return jsonify({"status": "error", "msg": "empty keyword"})
    ok = add_keyword(kw, cat)
    return jsonify({"status": "added" if ok else "exists"})

@app.route("/api/keywords/<int:kid>/delete", methods=["POST"])
def api_delete_keyword(kid):
    from database import delete_keyword
    delete_keyword(kid)
    return jsonify({"status": "deleted"})

# ── Notes & Tags ──────────────────────────────────────────────────────────────
@app.route("/api/packet/<int:pid>/note", methods=["POST"])
def api_save_note(pid):
    data = request.json or {}
    note = data.get("note", "")
    conn = __import__('database').get_conn()
    try:
        conn.execute("ALTER TABLE packets ADD COLUMN note TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    conn.execute("UPDATE packets SET note=? WHERE id=?", (note, pid))
    conn.commit()
    conn.close()
    return jsonify({"status": "saved"})

@app.route("/api/packet/<int:pid>/tag", methods=["POST"])
def api_save_tag(pid):
    data = request.json or {}
    tag  = data.get("tag", "")
    conn = __import__('database').get_conn()
    try:
        conn.execute("ALTER TABLE packets ADD COLUMN tags TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    # Get existing tags and toggle
    row = conn.execute("SELECT tags FROM packets WHERE id=?", (pid,)).fetchone()
    existing = (row["tags"] or "").split(",") if row else []
    existing = [t.strip() for t in existing if t.strip()]
    if tag in existing:
        existing.remove(tag)
    else:
        existing.append(tag)
    conn.execute("UPDATE packets SET tags=? WHERE id=?",
                 (",".join(existing), pid))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "tags": existing})

# ── Export ────────────────────────────────────────────────────────────────────
@app.route("/api/export/csv")
def export_csv():
    import csv, io
    meetings = get_all_meetings()
    output   = io.StringIO()
    writer   = csv.writer(output)
    writer.writerow(["Municipality", "State", "Body Type", "Body Name",
                     "Meeting Date", "Platform", "PDF URL", "Source URL"])
    for m in meetings:
        pkts = get_packets_for_meeting(m["id"])
        for p in pkts:
            writer.writerow([
                m["municipality"], m["state"], m["body_type"],
                m["body_name"], m["meeting_date"], m.get("platform",""),
                p.get("file_url",""), m.get("source_url","")
            ])
    output.seek(0)
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=getpackets_export.csv"}
    )

@app.route("/api/export/json")
def export_json():
    import json
    meetings = get_all_meetings()
    result   = []
    for m in meetings:
        pkts = get_packets_for_meeting(m["id"])
        result.append({**m, "packets": pkts})
    from flask import Response
    return Response(
        json.dumps(result, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=getpackets_export.json"}
    )

# ── Relevance scoring ─────────────────────────────────────────────────────────
@app.route("/api/score-packets", methods=["POST"])
def score_all_packets():
    import threading
    def do_score():
        try:
            import pdfplumber
            from database import get_conn, get_keywords, score_packet, update_packet_score
            conn  = get_conn()
            pkts  = conn.execute(
                "SELECT id, local_path FROM packets WHERE status='active'"
            ).fetchall()
            conn.close()
            extra = [k["keyword"] for k in get_keywords()]
            for p in pkts:
                if not p["local_path"] or not __import__('os').path.exists(p["local_path"]):
                    continue
                try:
                    text = ""
                    with pdfplumber.open(p["local_path"]) as pdf:
                        for page in pdf.pages[:5]:
                            t = page.extract_text()
                            if t:
                                text += t + " "
                    result = score_packet(text, extra)
                    update_packet_score(p["id"], result["score"],
                                        ",".join(result["matched"][:10]))
                except Exception:
                    pass
        except ImportError:
            pass
    threading.Thread(target=do_score, daemon=True).start()
    return jsonify({"status": "scoring started"})


@app.route("/api/recycle")
def recycle_api():
    return jsonify(get_recycle_bin())


@app.route("/api/recycle/<int:rid>/restore", methods=["POST"])
def restore_recycle(rid):
    restore_from_recycle(rid)
    return jsonify({"status": "restored"})


@app.route("/api/recycle/empty", methods=["POST"])
def empty_recycle():
    empty_recycle_bin()
    return jsonify({"status": "emptied"})


@app.route("/api/packets/delete-oldest", methods=["POST"])
def delete_oldest():
    data = request.json or {}
    n = int(data.get("count", 10))
    count = delete_oldest_packets(n)
    return jsonify({"status": "recycled", "count": count})


@app.route("/api/packets/delete-all", methods=["POST"])
def delete_all():
    count = delete_all_packets()
    return jsonify({"status": "recycled", "count": count})


@app.route("/api/sessions")
def sessions_api():
    return jsonify(get_sessions())


@app.route("/api/session/<int:sid>/packets")
def session_packets(sid):
    return jsonify(get_packets_for_session(sid))

@app.errorhandler(404)
def e404(e):
    return f"<h2>Not found</h2><p>{e}</p><p><a href='/'>Back</a></p>", 404

@app.errorhandler(500)
def e500(e):
    return f"<h2>Server error</h2><p>{e}</p><p><a href='/'>Back</a></p>", 500

if __name__ == "__main__":
    print("\n  GetPackets → http://localhost:8080\n")
    app.run(host="0.0.0.0", port=8080, debug=False)
