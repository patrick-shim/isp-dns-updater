FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    dnsutils \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --system --gid 10001 dns-updater && \
    useradd --system --uid 10001 --gid dns-updater --no-create-home dns-updater

# Runtime configuration and secrets are mounted by Docker Compose, never copied.
COPY --chown=dns-updater:dns-updater update_dns.py /app/update_dns.py
COPY --chown=dns-updater:dns-updater docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0555 /usr/local/bin/docker-entrypoint.sh /app/update_dns.py

USER dns-updater

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
