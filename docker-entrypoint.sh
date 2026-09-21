#!/bin/sh
set -u

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

interval="${DNS_UPDATER_INTERVAL_SECONDS:-60}"
case "$interval" in
    ''|*[!0-9]*)
        echo "DNS_UPDATER_INTERVAL_SECONDS must be a positive integer" >&2
        exit 2
        ;;
esac

if [ "$interval" -lt 1 ]; then
    echo "DNS_UPDATER_INTERVAL_SECONDS must be at least 1" >&2
    exit 2
fi

trap 'exit 0' INT TERM

echo "Starting Cloudflare DNS Updater (interval: ${interval}s)"
while true; do
    if python /app/update_dns.py; then
        touch /tmp/dns-updater.last-success
    else
        echo "DNS update failed; retrying in ${interval}s" >&2
    fi

    sleep "$interval" &
    wait $!
done
