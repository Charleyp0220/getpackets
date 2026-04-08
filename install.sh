#!/bin/bash
# install.sh — installs GetPackets as a proper desktop and app menu entry

INSTALL_DIR="$HOME/Downloads/getpackets"
ICON_DIR="$HOME/.local/share/icons"
APP_DIR="$HOME/.local/share/applications"

mkdir -p "$ICON_DIR" "$APP_DIR"

cat > "$ICON_DIR/getpackets.svg" << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="12" fill="#161b22"/>
  <rect x="6" y="8" width="52" height="40" rx="5" fill="#21262d" stroke="#58a6ff" stroke-width="2"/>
  <rect x="12" y="16" width="24" height="3" rx="1.5" fill="#58a6ff"/>
  <rect x="12" y="22" width="40" height="2" rx="1" fill="#3fb950"/>
  <rect x="12" y="27" width="32" height="2" rx="1" fill="#3fb950"/>
  <rect x="12" y="32" width="36" height="2" rx="1" fill="#d29922"/>
  <rect x="12" y="37" width="20" height="2" rx="1" fill="#f0883e"/>
  <rect x="16" y="48" width="32" height="8" rx="4" fill="#3fb950"/>
  <text x="32" y="55" text-anchor="middle" font-size="6" font-weight="bold" fill="#000" font-family="sans-serif">GetPackets</text>
</svg>
SVGEOF

cat > "$APP_DIR/getpackets.desktop" << DEOF
[Desktop Entry]
Version=1.0
Type=Application
Name=GetPackets
GenericName=Government Packet Collector
Comment=US Government Agenda Packet Scraper
Exec=bash -c 'cd "$HOME/Downloads/getpackets" && source venv/bin/activate && python dashboard/app.py & sleep 3 && xdg-open http://localhost:8080'
Icon=$ICON_DIR/getpackets.svg
Terminal=false
Categories=Network;WebBrowser;Utility;
Keywords=government;agenda;zoning;planning;packets;council;
StartupNotify=true
DEOF

cp "$APP_DIR/getpackets.desktop" "$HOME/Desktop/GetPackets.desktop"
chmod +x "$HOME/Desktop/GetPackets.desktop"
gio set "$HOME/Desktop/GetPackets.desktop" metadata::trusted true 2>/dev/null || true
update-desktop-database "$APP_DIR" 2>/dev/null || true

echo ""
echo "  GetPackets installed!"
echo "  - Desktop: ~/Desktop/GetPackets.desktop"  
echo "  - App menu: Search for 'GetPackets'"
echo "  - Dashboard: http://localhost:8080"
echo ""
