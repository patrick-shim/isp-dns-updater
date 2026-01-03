#!/bin/bash
set -e

echo "Starting CloudFlare DNS Updater (cron mode)"
echo "Cron schedule: Every 1 minute"
echo "Log files:"
echo "  - Application: /var/log/dns-updater.log"
echo "  - Cron: /var/log/cron.log"
echo ""

# Run once immediately on startup
echo "Running initial DNS update..."
cd /app && python update_dns.py

# Start cron in foreground
echo ""
echo "Starting cron daemon..."
cron && tail -f /var/log/cron.log /var/log/dns-updater.log
