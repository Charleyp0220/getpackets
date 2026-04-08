"""
scrapers/google_pdf_hunt.py — finds government agenda PDFs directly
via search engine queries.

Instead of guessing URLs, we let search engines tell us exactly where
the PDFs are. This finds cities we'd never discover by guessing slugs.

Uses DuckDuckGo (no API key needed) and Bing search.
"""

import requests, re, time
from datetime import date, timedelta
from urllib.parse import urlparse, urlencode, quote
from bs4 import BeautifulSoup
from utils import classify_body, parse_date, date_str, download_packet, is_future_or_today
from constants import HEADERS, REQUEST_TIMEOUT

DDG_URL  = "https://html.duckduckgo.com/html/"
BING_URL = "https://www.bing.com/search"

# Search queries that find planning/zoning packets
# These are carefully crafted to find only real government PDFs
QUERIES_BY_STATE = {
    "Alabama": [
        'site:*.al.us "planning commission" "agenda" filetype:pdf',
        'site:*.al.gov "zoning" "agenda packet" filetype:pdf',
        'site:*.alabama.gov "board of adjustment" "agenda" filetype:pdf',
    ],
    "Alaska": [
        'site:*.ak.us "planning commission" "agenda" filetype:pdf',
        'site:*.ak.gov "zoning" "agenda" filetype:pdf',
    ],
    "Arizona": [
        'site:*.az.us "planning" "agenda packet" filetype:pdf',
        'site:*.az.gov "zoning" "board of adjustment" filetype:pdf',
        'site:*.maricopa.gov "planning" "agenda" filetype:pdf',
    ],
    "Arkansas": [
        'site:*.ar.us "planning commission" "agenda" filetype:pdf',
        'site:*.ar.gov "zoning" "agenda" filetype:pdf',
    ],
    "California": [
        'site:*.ca.us "planning commission" "agenda packet" filetype:pdf',
        'site:*.ca.gov "zoning board" "agenda" filetype:pdf',
        'site:*.lacounty.gov "planning" "agenda" filetype:pdf',
        'site:*.sandiego.gov "planning" "agenda" filetype:pdf',
        'site:*.sfgov.org "planning" "agenda" filetype:pdf',
    ],
    "Colorado": [
        'site:*.co.us "planning commission" "agenda" filetype:pdf',
        'site:*.co.gov "zoning" "agenda packet" filetype:pdf',
        'site:*.denvergov.org "planning" "agenda" filetype:pdf',
    ],
    "Connecticut": [
        'site:*.ct.us "planning" "zoning" "agenda" filetype:pdf',
        'site:*.ct.gov "planning" "agenda" filetype:pdf',
    ],
    "Delaware": [
        'site:*.de.us "planning" "agenda" filetype:pdf',
        'site:*.delaware.gov "zoning" "agenda" filetype:pdf',
    ],
    "Florida": [
        'site:*.fl.us "planning" "agenda packet" filetype:pdf',
        'site:*.fl.gov "zoning board" "agenda" filetype:pdf',
        'site:*.broward.org "planning" "agenda" filetype:pdf',
        'site:*.miamidade.gov "planning" "agenda" filetype:pdf',
    ],
    "Georgia": [
        'site:*.ga.us "planning commission" "agenda" filetype:pdf',
        'site:*.ga.gov "zoning" "agenda packet" filetype:pdf',
        'site:*.atlantaga.gov "planning" "agenda" filetype:pdf',
    ],
    "Hawaii": [
        'site:*.hi.us "planning" "agenda" filetype:pdf',
        'site:*.hawaii.gov "zoning" "agenda" filetype:pdf',
    ],
    "Idaho": [
        'site:*.id.us "planning" "agenda packet" filetype:pdf',
        'site:*.id.gov "zoning" "agenda" filetype:pdf',
    ],
    "Illinois": [
        'site:*.il.us "planning commission" "agenda" filetype:pdf',
        'site:*.il.gov "zoning board" "agenda packet" filetype:pdf',
        'site:*.chicago.gov "planning" "agenda" filetype:pdf',
        'site:*.cookcountyil.gov "planning" "agenda" filetype:pdf',
    ],
    "Indiana": [
        'site:*.in.us "plan commission" "agenda" filetype:pdf',
        'site:*.in.gov "board of zoning" "agenda" filetype:pdf',
    ],
    "Iowa": [
        'site:*.ia.us "planning" "agenda" filetype:pdf',
        'site:*.iowa.gov "zoning" "agenda" filetype:pdf',
    ],
    "Kansas": [
        'site:*.ks.us "planning" "agenda packet" filetype:pdf',
        'site:*.ks.gov "metropolitan planning" "agenda" filetype:pdf',
    ],
    "Kentucky": [
        'site:*.ky.us "planning commission" "agenda" filetype:pdf',
        'site:*.ky.gov "board of adjustment" "agenda" filetype:pdf',
    ],
    "Louisiana": [
        'site:*.la.us "planning" "agenda" filetype:pdf',
        'site:*.la.gov "zoning" "agenda packet" filetype:pdf',
    ],
    "Maine": [
        'site:*.me.us "planning board" "agenda" filetype:pdf',
        'site:*.maine.gov "zoning" "agenda" filetype:pdf',
    ],
    "Maryland": [
        'site:*.md.us "planning" "agenda packet" filetype:pdf',
        'site:*.maryland.gov "zoning" "agenda" filetype:pdf',
        'site:*.baltimorecity.gov "planning" "agenda" filetype:pdf',
    ],
    "Massachusetts": [
        'site:*.ma.us "planning board" "agenda" filetype:pdf',
        'site:*.mass.gov "zoning board" "agenda" filetype:pdf',
    ],
    "Michigan": [
        'site:*.mi.us "planning commission" "agenda" filetype:pdf',
        'site:*.mi.gov "zoning board" "agenda packet" filetype:pdf',
        'site:*.detroitmi.gov "planning" "agenda" filetype:pdf',
    ],
    "Minnesota": [
        'site:*.mn.us "planning commission" "agenda" filetype:pdf',
        'site:*.mn.gov "board of adjustment" "agenda" filetype:pdf',
    ],
    "Mississippi": [
        'site:*.ms.us "planning commission" "agenda" filetype:pdf',
        'site:*.ms.gov "zoning" "agenda" filetype:pdf',
    ],
    "Missouri": [
        'site:*.mo.us "planning" "agenda packet" filetype:pdf',
        'site:*.mo.gov "zoning" "agenda" filetype:pdf',
    ],
    "Montana": [
        'site:*.mt.us "planning board" "agenda" filetype:pdf',
        'site:*.mt.gov "zoning" "agenda" filetype:pdf',
    ],
    "Nebraska": [
        'site:*.ne.us "planning commission" "agenda" filetype:pdf',
        'site:*.ne.gov "zoning" "agenda" filetype:pdf',
    ],
    "Nevada": [
        'site:*.nv.us "planning commission" "agenda" filetype:pdf',
        'site:*.nv.gov "board of adjustment" "agenda" filetype:pdf',
        'site:*.clarkcountynv.gov "planning" "agenda" filetype:pdf',
    ],
    "New Hampshire": [
        'site:*.nh.us "planning board" "agenda" filetype:pdf',
        'site:*.nh.gov "zoning board" "agenda" filetype:pdf',
    ],
    "New Jersey": [
        'site:*.nj.us "planning board" "agenda" filetype:pdf',
        'site:*.nj.gov "zoning board" "agenda" filetype:pdf',
    ],
    "New Mexico": [
        'site:*.nm.us "planning" "agenda" filetype:pdf',
        'site:*.nm.gov "zoning" "agenda" filetype:pdf',
    ],
    "New York": [
        'site:*.ny.us "planning board" "agenda" filetype:pdf',
        'site:*.ny.gov "zoning board" "agenda" filetype:pdf',
        'site:*.nyc.gov "planning" "agenda" filetype:pdf',
    ],
    "North Carolina": [
        'site:*.nc.us "planning board" "agenda" filetype:pdf',
        'site:*.nc.gov "board of adjustment" "agenda" filetype:pdf',
        'site:*.wakegov.com "planning" "agenda" filetype:pdf',
    ],
    "North Dakota": [
        'site:*.nd.us "planning" "agenda" filetype:pdf',
        'site:*.nd.gov "zoning" "agenda" filetype:pdf',
    ],
    "Ohio": [
        'site:*.oh.us "planning commission" "agenda" filetype:pdf',
        'site:*.oh.gov "board of zoning" "agenda" filetype:pdf',
    ],
    "Oklahoma": [
        'site:*.ok.us "planning commission" "agenda" filetype:pdf',
        'site:*.ok.gov "board of adjustment" "agenda" filetype:pdf',
    ],
    "Oregon": [
        'site:*.or.us "planning commission" "agenda" filetype:pdf',
        'site:*.or.gov "hearings officer" "agenda" filetype:pdf',
        'site:*.portlandoregon.gov "planning" "agenda" filetype:pdf',
    ],
    "Pennsylvania": [
        'site:*.pa.us "planning commission" "agenda" filetype:pdf',
        'site:*.pa.gov "zoning hearing" "agenda" filetype:pdf',
        'site:*.phila.gov "planning" "agenda" filetype:pdf',
    ],
    "Rhode Island": [
        'site:*.ri.us "planning board" "agenda" filetype:pdf',
        'site:*.ri.gov "zoning board" "agenda" filetype:pdf',
    ],
    "South Carolina": [
        'site:*.sc.us "planning commission" "agenda" filetype:pdf',
        'site:*.sc.gov "board of zoning" "agenda" filetype:pdf',
    ],
    "South Dakota": [
        'site:*.sd.us "planning commission" "agenda" filetype:pdf',
        'site:*.sd.gov "zoning" "agenda" filetype:pdf',
    ],
    "Tennessee": [
        'site:*.tn.us "planning commission" "agenda" filetype:pdf',
        'site:*.tn.gov "board of zoning" "agenda" filetype:pdf',
    ],
    "Texas": [
        'site:*.tx.us "planning" "zoning" "agenda" filetype:pdf',
        'site:*.tx.gov "board of adjustment" "agenda packet" filetype:pdf',
        'site:*.houstontx.gov "planning" "agenda" filetype:pdf',
        'site:*.dallascityhall.com "planning" "agenda" filetype:pdf',
        'site:*.austintexas.gov "planning" "agenda" filetype:pdf',
    ],
    "Utah": [
        'site:*.ut.us "planning commission" "agenda" filetype:pdf',
        'site:*.utah.gov "board of adjustment" "agenda" filetype:pdf',
    ],
    "Vermont": [
        'site:*.vt.us "planning commission" "agenda" filetype:pdf',
        'site:*.vermont.gov "development review" "agenda" filetype:pdf',
    ],
    "Virginia": [
        'site:*.va.us "planning commission" "agenda" filetype:pdf',
        'site:*.va.gov "board of zoning" "agenda" filetype:pdf',
        'site:*.fairfaxcounty.gov "planning" "agenda" filetype:pdf',
    ],
    "Washington": [
        'site:*.wa.us "planning commission" "agenda" filetype:pdf',
        'site:*.wa.gov "hearing examiner" "agenda" filetype:pdf',
        'site:*.kingcounty.gov "planning" "agenda" filetype:pdf',
        'site:*.seattle.gov "planning" "agenda" filetype:pdf',
    ],
    "West Virginia": [
        'site:*.wv.us "planning commission" "agenda" filetype:pdf',
        'site:*.wv.gov "board of zoning" "agenda" filetype:pdf',
    ],
    "Wisconsin": [
        'site:*.wi.us "plan commission" "agenda" filetype:pdf',
        'site:*.wi.gov "board of appeals" "agenda" filetype:pdf',
        'site:*.milwaukee.gov "planning" "agenda" filetype:pdf',
    ],
    "Wyoming": [
        'site:*.wy.us "planning commission" "agenda" filetype:pdf',
        'site:*.wy.gov "board of adjustment" "agenda" filetype:pdf',
    ],
}


def _search_ddg(query: str) -> list[str]:
    """Search DuckDuckGo HTML for PDF links."""
    try:
        r = requests.post(DDG_URL,
            data={"q": query, "b": "", "kl": "us-en"},
            headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
            timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "lxml")
        urls = []
        for a in soup.select("a.result__url, a[href*='.pdf']"):
            href = a.get("href","")
            if ".pdf" in href.lower() and ".gov" in href.lower():
                # Clean DuckDuckGo redirect
                if "uddg=" in href:
                    from urllib.parse import unquote
                    href = unquote(href.split("uddg=")[-1].split("&")[0])
                urls.append(href)
        return urls[:10]
    except Exception:
        return []


def _search_bing(query: str) -> list[str]:
    """Search Bing for PDF links."""
    try:
        params = {"q": query, "count": "20", "mkt": "en-US"}
        r = requests.get(BING_URL, params=params,
            headers={**HEADERS, "Accept": "text/html"},
            timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "lxml")
        urls = []
        for a in soup.select("a[href*='.pdf']"):
            href = a.get("href","")
            if ".pdf" in href.lower() and ".gov" in href.lower():
                urls.append(href)
        # Also check cite tags
        for cite in soup.select("cite"):
            text = cite.get_text().strip()
            if ".pdf" in text.lower() and ".gov" in text.lower():
                urls.append("https://" + text if not text.startswith("http") else text)
        return urls[:10]
    except Exception:
        return []


def scrape_google_pdf_hunt(state: str, collected: list, max_packets: int) -> int:
    """Search for government PDFs for the given state."""
    queries = QUERIES_BY_STATE.get(state, [])
    if not queries:
        return 0

    added     = 0
    seen_urls = set()
    cutoff    = date.today() - timedelta(days=30)

    for query in queries:
        if len(collected) >= max_packets:
            break

        # Try DuckDuckGo first, fall back to Bing
        urls = _search_ddg(query)
        if not urls:
            urls = _search_bing(query)
            time.sleep(0.5)

        for pdf_url in urls:
            if len(collected) >= max_packets:
                break
            if pdf_url in seen_urls:
                continue
            seen_urls.add(pdf_url)

            # Must be a real .gov PDF
            if not pdf_url.lower().endswith(".pdf"):
                continue
            if not any(x in pdf_url.lower() for x in [".gov", ".us"]):
                continue

            # Extract municipality from URL
            parsed   = urlparse(pdf_url)
            hostname = parsed.hostname or ""
            parts    = hostname.replace("www.", "").split(".")
            muni     = parts[0].replace("-", " ").title() if parts else state

            # Classify from URL path + filename
            path_text = parsed.path.replace("/", " ").replace("-", " ").replace("_", " ")
            body_type = classify_body(path_text)
            if not body_type:
                body_type = "planning_zoning"

            # Try to extract date from URL
            date_match = re.search(
                r"(\d{4}[-_]\d{2}[-_]\d{2})|"
                r"(\d{1,2}[-_]\d{1,2}[-_]\d{2,4})",
                parsed.path
            )
            meeting_date = parse_date(date_match.group(0).replace("_", "-")) \
                           if date_match else date.today()
            if not is_future_or_today(meeting_date):
                continue

            dl = download_packet(pdf_url, state, muni,
                                body_type, date_str(meeting_date))
            if not dl or dl.get("failed"):
                continue

            collected.append({
                "state":        state,
                "municipality": muni,
                "place_type":   "city",
                "body_name":    body_type.replace("_", " ").title(),
                "body_type":    body_type,
                "meeting_date": date_str(meeting_date),
                "meeting_time": "",
                "location":     "",
                "source_url":   pdf_url,
                "platform":     "WebSearch",
                **dl,
            })
            added += 1

        time.sleep(1)  # Be polite to search engines

    return added
