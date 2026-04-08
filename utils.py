"""
utils.py — shared helpers for GetPackets.
"""

import os, re, requests, time, unicodedata
from datetime import date, datetime
from dateutil import parser as dp
from colorama import Fore, Style, init as colorama_init
from constants import TARGET_BODIES, HEADERS, DOWNLOAD_TIMEOUT, PACKETS_DIR

colorama_init(autoreset=True)


# ── Logging ───────────────────────────────────────────────────────────────────

def log_info(msg):  print(Fore.CYAN   + "  ℹ " + Style.RESET_ALL + msg)
def log_ok(msg):    print(Fore.GREEN  + "  ✔ " + Style.RESET_ALL + msg)
def log_warn(msg):  print(Fore.YELLOW + "  ⚠ " + Style.RESET_ALL + msg)
def log_err(msg):   print(Fore.RED    + "  ✘ " + Style.RESET_ALL + msg)
def log_link(msg):  print(Fore.MAGENTA+ "  🔗 " + Style.RESET_ALL + msg)


# ── Body classification ───────────────────────────────────────────────────────

def classify_body(name: str) -> str | None:
    name_l = name.lower()
    for body_type, keywords in TARGET_BODIES.items():
        for kw in keywords:
            if kw in name_l:
                return body_type
    return None


# ── Date helpers ──────────────────────────────────────────────────────────────

def parse_date(raw: str) -> date | None:
    if not raw:
        return None
    try:
        return dp.parse(str(raw), fuzzy=True).date()
    except Exception:
        return None


def is_future_or_today(d: date | None) -> bool:
    if d is None:
        return False
    return d >= date.today()


def date_str(d: date | None) -> str:
    return d.strftime("%Y-%m-%d") if d else "Unknown"


# ── Safe filename ─────────────────────────────────────────────────────────────

def safe_name(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s\-]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text[:80]


# ── XML parser for Legistar ───────────────────────────────────────────────────

def parse_legistar_xml(data) -> list:
    """
    Parse Legistar API response into a list of event dicts.
    Handles both JSON (new API format) and XML (old format).
    """
    # Handle both bytes and string input
    if isinstance(data, bytes):
        # Check Content-Type hint or try to detect JSON vs XML
        text = data.decode("utf-8", errors="replace").lstrip()
        is_json = text.startswith("[") or text.startswith("{")
    else:
        text = str(data).lstrip()
        is_json = text.startswith("[") or text.startswith("{")

    # ── JSON format (current Legistar API) ───────────────────────────────────
    if is_json:
        try:
            import json
            raw = json.loads(text)
            # API returns either a list directly or {value: [...]}
            if isinstance(raw, dict):
                raw = raw.get("value", raw.get("events", []))
            events = []
            for ev in raw:
                events.append({
                    "EventId":          str(ev.get("EventId", ev.get("eventId", ""))),
                    "EventBodyName":    ev.get("EventBodyName", ev.get("eventBodyName", ev.get("body", ""))),
                    "EventDate":        ev.get("EventDate", ev.get("eventDate", ev.get("date", ""))),
                    "EventTime":        ev.get("EventTime", ev.get("eventTime", ev.get("time", ""))),
                    "EventLocation":    ev.get("EventLocation", ev.get("eventLocation", ev.get("location", ""))),
                    "EventAgendaFile":  ev.get("EventAgendaFile", ev.get("eventAgendaFile", ev.get("agendaUrl", ""))),
                    "EventMinutesFile": ev.get("EventMinutesFile", ev.get("eventMinutesFile", "")),
                })
            return events
        except Exception:
            return []

    # ── XML format (old Legistar API) ────────────────────────────────────────
    import xml.etree.ElementTree as ET
    NS = "http://schemas.datacontract.org/2004/07/LegistarWebAPI.Models.v1"
    try:
        root = ET.fromstring(data if isinstance(data, bytes) else data.encode())
        events = []
        for ev in root.findall(f"{{{NS}}}GranicusEvent"):
            def t(tag):
                el = ev.find(f"{{{NS}}}{tag}")
                return el.text if el is not None else ""
            events.append({
                "EventId":          t("EventId"),
                "EventBodyName":    t("EventBodyName"),
                "EventDate":        t("EventDate"),
                "EventTime":        t("EventTime"),
                "EventLocation":    t("EventLocation"),
                "EventAgendaFile":  t("EventAgendaFile"),
                "EventMinutesFile": t("EventMinutesFile"),
            })
        return events
    except Exception:
        return []


# ── PDF downloader ────────────────────────────────────────────────────────────

def download_packet(url: str, state: str, municipality: str,
                    body_type: str, meeting_date: str,
                    retries: int = 3) -> dict | None:
    """
    Download a PDF agenda packet with retry logic.
    Returns a dict with file info, or None if all retries fail.
    Also saves the source URL so user can visit it manually if download fails.
    """
    if not url or not url.strip():
        return None

    fname  = _make_filename(state, municipality, body_type, meeting_date, url)
    fpath  = os.path.join(PACKETS_DIR, fname)
    os.makedirs(PACKETS_DIR, exist_ok=True)

    # Already downloaded
    if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
        return {
            "filename":     fname,
            "local_path":   fpath,
            "file_url":     url,
            "file_size_kb": round(os.path.getsize(fpath) / 1024, 1),
        }

    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=DOWNLOAD_TIMEOUT,
                             stream=True)
            if r.status_code == 200:
                ct = r.headers.get("Content-Type", "")
                if "pdf" in ct.lower() or url.lower().endswith(".pdf") or                    len(r.content) > 5000:
                    with open(fpath, "wb") as f:
                        f.write(r.content)
                    size_kb = round(os.path.getsize(fpath) / 1024, 1)
                    log_ok(f"Downloaded {size_kb} KB — {fname}")
                    return {
                        "filename":     fname,
                        "local_path":   fpath,
                        "file_url":     url,
                        "file_size_kb": size_kb,
                    }
                else:
                    last_error = f"Not a PDF (Content-Type: {ct})"
                    break
            else:
                last_error = f"HTTP {r.status_code}"
                if r.status_code in (403, 404, 410):
                    break  # No point retrying
        except Exception as e:
            last_error = str(e)[:80]
            if attempt < retries:
                time.sleep(2 * attempt)  # backoff

    log_err(f"Download failed ({last_error}) — {url[:80]}")
    # Return failed entry so we can save the source URL for manual visit
    return {
        "filename":     fname + ".failed",
        "local_path":   "",
        "file_url":     url,
        "file_size_kb": 0,
        "failed":       True,
        "error":        last_error,
    }


def _make_filename(state, municipality, body_type, meeting_date, url):
    ext = ".pdf"
    base = f"{safe_name(state)}_{safe_name(municipality)}_"            f"{body_type}_{meeting_date}"
    # Add last part of URL to make unique
    url_part = url.rstrip("/").split("/")[-1][:20]
    url_part = re.sub(r"[^\w]", "_", url_part)
    return f"{base}_{url_part}{ext}"


