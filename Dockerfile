FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    dnsutils \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY update_dns.py .
COPY config.yaml .

# Create log directory
RUN mkdir -p /var/log && \
    touch /var/log/dns-updater.log && \
    chmod 666 /var/log/dns-updater.log

# Create cron job file
RUN echo "* * * * * cd /app && /usr/local/bin/python /app/update_dns.py >> /var/log/cron.log 2>&1" > /etc/cron.d/dns-updater && \
    chmod 0644 /etc/cron.d/dns-updater && \
    crontab /etc/cron.d/dns-updater && \
    touch /var/log/cron.log

# Create entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]
