# GetPackets
### Plain-English Guide — No Technical Experience Needed

---

## What This Does

GetPackets searches 3,000 US municipalities — cities, counties, townships, boroughs, and villages — and does two things for each one:

1. **Downloads the agenda packet** (PDF) if it can find one automatically
2. **Saves a clickable link** to the city's meeting page if it can't download a PDF, so you can visit it yourself

You can see everything in a simple website at **http://localhost:8080** — no programming needed after setup.

---

## First-Time Setup (Do This Once)

Open a terminal in the `getpackets` folder and type:

```
bash setup.sh
```

Wait for it to finish. That's it.

---

## Starting the Dashboard (Every Time)

**Option A — Double-click** `START.sh` in your file manager.
Right-click → Run as Program if double-clicking doesn't work.

**Option B — Terminal:**
```
source venv/bin/activate
python dashboard/app.py
```

Then open your browser to: **http://localhost:8080**

---

## Using the Dashboard

### Starting the Scraper
Click the green **▶ Start** button in the top right corner.
Watch the activity log appear below the header — it shows exactly what's happening in real time.

### Downloaded Packets tab
Every agenda packet (PDF) that was successfully downloaded. Click **📄 View Packets** to open or download the PDF.

### Manual Visit Links tab
Every municipality where the scraper found a meeting page but couldn't get a PDF automatically. Click **🌐 Visit Meeting Page** to open that city's government website directly in your browser and look for the agenda yourself.

### Filtering
Use the search box to find a specific city. Filter by state or meeting body type. Switch between card view and list view with the buttons in the top right of the filter bar.

---

## Where Are the Files?

All downloaded PDFs are in:
```
getpackets/data/packets/
```

Organized by state, then city, then meeting type:
```
data/packets/
  Washington/
    Seattle/
      city_council/
        2026-04-07_Seattle_city_council.pdf
  Colorado/
    Denver/
      planning_zoning/
        2026-04-10_Denver_planning_zoning.pdf
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Double-click on START.sh doesn't work | Right-click → Run as Program |
| "command not found: python" | Use `python3` instead of `python` |
| Dashboard shows 0 packets | Let the scraper run for a few minutes — it takes time to find packets |
| Port 8080 in use | Change `port=8080` to `port=5051` in `dashboard/app.py` |
| uscities.csv not found | Run `bash setup.sh` again |

---

## Questions?

Paste this README plus your question into any AI assistant and it can help you.
