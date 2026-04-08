"""
pdf_search.py — extracts text from downloaded PDFs and indexes
planning/zoning keywords for fast searching.

Run with: python pdf_search.py
Or import search_packets() for use in dashboard.
"""

import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import PACKETS_DIR, ALL_PLANNING_KEYWORDS
from database  import get_conn, init_db

INDEX_FILE = "data/pdf_index.json"


def extract_text(pdf_path: str) -> str:
    """Extract text from a PDF file using pdfplumber."""
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:10]:  # first 10 pages only
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return text.lower()
    except Exception as e:
        return ""


def find_keywords(text: str) -> list:
    """Find all planning/zoning keywords in extracted text."""
    found = []
    for kw in ALL_PLANNING_KEYWORDS:
        if kw.lower() in text:
            found.append(kw)
    return found


def index_all_pdfs(force=False):
    """
    Index all downloaded PDFs for keyword search.
    Saves results to data/pdf_index.json
    """
    try:
        import pdfplumber
    except ImportError:
        print("Installing pdfplumber...")
        os.system(f"{sys.executable} -m pip install pdfplumber -q "
                  "--break-system-packages")
        import pdfplumber

    init_db()
    conn = get_conn()
    packets = conn.execute(
        "SELECT id, filename, local_path FROM packets WHERE status='active'"
    ).fetchall()
    conn.close()

    # Load existing index
    index = {}
    if os.path.exists(INDEX_FILE) and not force:
        with open(INDEX_FILE) as f:
            index = json.load(f)

    updated = 0
    for p in packets:
        pid      = str(p["id"])
        path     = p["local_path"]
        filename = p["filename"]

        if pid in index and not force:
            continue
        if not path or not os.path.exists(path):
            continue

        print(f"  Indexing: {filename[:60]}")
        text     = extract_text(path)
        keywords = find_keywords(text)

        index[pid] = {
            "filename": filename,
            "keywords": keywords,
            "has_planning": len(keywords) > 0,
            "text_preview": text[:500].strip(),
        }
        updated += 1

    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)

    print(f"\n  Indexed {updated} new PDFs ({len(index)} total)")
    return index


def search_packets(query: str) -> list:
    """
    Search indexed PDFs for a query string.
    Returns list of packet IDs that match.
    """
    if not os.path.exists(INDEX_FILE):
        return []

    with open(INDEX_FILE) as f:
        index = json.load(f)

    query_l = query.lower().strip()
    matches = []
    for pid, data in index.items():
        # Check keywords
        if any(query_l in kw for kw in data.get("keywords", [])):
            matches.append(int(pid))
            continue
        # Check text preview
        if query_l in data.get("text_preview", ""):
            matches.append(int(pid))

    return matches


def get_packet_keywords(packet_id: int) -> list:
    """Get keywords found in a specific packet."""
    if not os.path.exists(INDEX_FILE):
        return []
    with open(INDEX_FILE) as f:
        index = json.load(f)
    data = index.get(str(packet_id), {})
    return data.get("keywords", [])


if __name__ == "__main__":
    print()
    print("="*55)
    print("  GETPACKETS PDF INDEXER")
    print("="*55)
    print()

    force = "--force" in sys.argv
    index = index_all_pdfs(force=force)

    # Show keyword summary
    all_kws = {}
    for data in index.values():
        for kw in data.get("keywords", []):
            all_kws[kw] = all_kws.get(kw, 0) + 1

    if all_kws:
        print("\n  Top keywords found in your packets:")
        for kw, cnt in sorted(all_kws.items(), key=lambda x: -x[1])[:20]:
            print(f"    {kw:35s} {cnt} packets")

    print()
    print("  Index saved to", INDEX_FILE)
    print("  Run again with --force to reindex all PDFs")
    print()
