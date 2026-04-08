#!/bin/bash
# setup_cron.sh — sets up weekly auto-discovery and daily scraping

GETPACKETS="$HOME/Downloads/getpackets"
PYTHON="$GETPACKETS/venv/bin/python"
LOG="$GETPACKETS/logs"

mkdir -p "$LOG"

# Add cron jobs
(crontab -l 2>/dev/null; cat << CRON
# GetPackets — run scraper every 6 hours
0 */6 * * * cd $GETPACKETS && $PYTHON run.py >> $LOG/run.log 2>&1

# GetPackets — auto-discover new sources every Monday at 3am
0 3 * * 1 cd $GETPACKETS && $PYTHON auto_discover.py >> $LOG/discover.log 2>&1

# GetPackets — clean expired recycle bin daily at midnight
0 0 * * * cd $GETPACKETS && $PYTHON -c "from database import init_db, purge_expired_recycle; init_db(); n=purge_expired_recycle(); print(f'Purged {n} expired items')" >> $LOG/cleanup.log 2>&1
CRON
) | crontab -

echo ""
echo "  Cron jobs installed:"
echo "  - Scraper runs every 6 hours automatically"
echo "  - Auto-discovery runs every Monday at 3am"
echo "  - Cleanup runs daily at midnight"
echo ""
echo "  View logs: tail -f $LOG/run.log"
echo ""
crontab -l
