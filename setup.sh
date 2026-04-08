#!/bin/bash
# setup.sh — run once to install GetPackets.
# Usage: bash setup.sh

set -e
cd "$(dirname "$0")"

echo ""
echo "  ╔═══════════════════════════════╗"
echo "  ║   GetPackets — Setup       ║"
echo "  ╚═══════════════════════════════╝"
echo ""

# 1. Create virtual environment
if [ ! -d "venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv venv
fi

# 2. Install dependencies
echo "  Installing dependencies..."
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 3. Download cities CSV
mkdir -p data
if [ ! -f "data/uscities.csv" ]; then
    echo "  Downloading US municipalities list..."
    python3 -c "
import urllib.request, os
url = 'https://simplemaps.com/static/exports/us-cities/1.79/us-cities.csv'
dest = 'data/uscities.csv'
try:
    urllib.request.urlretrieve(url, dest)
    print('  Downloaded uscities.csv successfully.')
except Exception as e:
    print(f'  Could not download CSV: {e}')
    print('  Will use built-in city list instead.')
"
fi

# 4. Create folders
mkdir -p data/db data/packets

echo ""
echo "  ✔ Setup complete!"
echo ""
echo "  To start GetPackets:"
echo "    Double-click START.sh"
echo "  Or in terminal:"
echo "    source venv/bin/activate"
echo "    python dashboard/app.py"
echo ""
