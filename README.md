# CloudFlare DNS Updater

[![Docker Build](https://github.com/patrick-shim/isp-dns-updater/workflows/Docker%20Build/badge.svg)](https://github.com/patrick-shim/isp-dns-updater/actions)
[![Python Lint](https://github.com/patrick-shim/isp-dns-updater/workflows/Python%20Lint/badge.svg)](https://github.com/patrick-shim/isp-dns-updater/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

Automated CloudFlare DNS updater for dynamic IP addresses. Perfect for home servers, Unifi DreamMachine routers, or any setup with multiple WAN connections that need DNS records kept in sync.

> **⚠️ Security Note**: This tool requires CloudFlare API credentials. See [SECURITY.md](SECURITY.md) for best practices.

## Features

- **External Configuration**: All settings in YAML config file - no hardcoded values
- **Comprehensive Logging**: Detailed logging to console and file with timestamps
- **Automatic Retries**: Exponential backoff retry logic for all API calls and DNS resolution
- **Robust Error Handling**: Graceful handling of network failures, timeouts, and API errors
- **DNS Resolution**: Resolves current WAN IPs from configurable DNS hostnames
- **Record Management**: Cleans up existing DNS records and creates new A records for both IPs
- **CloudFlare API v4**: Full integration with CloudFlare's DNS API
- **Partial Success Handling**: Continues operation even if one IP fails
- **Environment Variable Support**: Override config file location via `DNS_UPDATER_CONFIG`

## Quick Start (Docker - Recommended)

The easiest way to run this is with Docker, which handles all dependencies and runs automatically every 1 minute.

### 1. Create configuration file:
```bash
cp config.example.yaml config.yaml
nano config.yaml  # Edit with your CloudFlare credentials
```

### 2. Start the container:
```bash
docker-compose up -d
```

### 3. View logs:
```bash
docker-compose logs -f
```

That's it! The script will run every 1 minute automatically.

## Setup (Native Python)

If you prefer to run without Docker:

### 1. Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate  # On Windows
```

### 2. Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Create configuration file:
```bash
cp config.example.yaml config.yaml
```

Then edit `config.yaml` with your settings:
```bash
nano config.yaml  # or vim, vi, etc.
```

### 4. Make script executable (optional):
```bash
chmod +x update_dns.py
```

## Usage

### Basic Usage
Run the script (uses `config.yaml` in the same directory):
```bash
python update_dns.py
```

Or directly (if executable):
```bash
./update_dns.py
```

### Custom Configuration File
Specify a different config file using environment variable:
```bash
DNS_UPDATER_CONFIG=/path/to/custom-config.yaml python update_dns.py
```

### Running as Cron Job
Add to crontab for automatic updates (every 5 minutes):
```bash
*/5 * * * * cd /path/to/isp-address-updater && .venv/bin/python update_dns.py >> /var/log/dns-updater-cron.log 2>&1
```

## Docker Deployment

### Prerequisites
- Docker installed
- Docker Compose installed

### Quick Start with Docker

1. **Create configuration**:
```bash
cp config.example.yaml config.yaml
nano config.yaml  # Edit with your settings
```

2. **Build and start**:
```bash
docker-compose up -d
```

3. **View logs**:
```bash
docker-compose logs -f
```

### Docker Commands

Using Make (recommended):
```bash
make help          # Show all available commands
make build         # Build the Docker image
make up            # Start container in background
make down          # Stop and remove container
make restart       # Restart the container
make logs          # Show logs
make logs-follow   # Follow logs in real-time
make shell         # Open shell in container
make clean         # Remove everything
```

Using docker-compose directly:
```bash
docker-compose build              # Build image
docker-compose up -d              # Start in background
docker-compose down               # Stop and remove
docker-compose restart            # Restart
docker-compose logs -f            # Follow logs
docker-compose exec dns-updater bash  # Shell access
```

### Cron Schedule

The Docker container runs the DNS updater **every 1 minute** automatically. The cron schedule is configured in the Dockerfile.

To change the schedule, edit the Dockerfile and rebuild:
```dockerfile
# Change this line in Dockerfile:
RUN echo "* * * * * ..." > /etc/cron.d/dns-updater
# Cron format: minute hour day month weekday
# Examples:
#   * * * * *           Every 1 minute
#   */5 * * * *         Every 5 minutes
#   0 * * * *           Every hour
#   0 */6 * * *         Every 6 hours
```

Then rebuild:
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

### Log Files

Logs are stored in the `./logs` directory on the host:
- `logs/dns-updater.log` - Application logs
- `logs/cron.log` - Cron execution logs

View logs:
```bash
# Real-time logs from Docker
docker-compose logs -f

# Or view log files directly
tail -f logs/dns-updater.log
tail -f logs/cron.log
```

### Updating Configuration

1. Edit `config.yaml` on the host
2. Restart the container:
```bash
docker-compose restart
```

The configuration file is mounted as read-only, so changes take effect after restart.

### Resource Limits

The docker-compose.yml includes resource limits:
- CPU: 0.5 cores max, 0.1 cores reserved
- Memory: 256MB max, 64MB reserved

Adjust these in `docker-compose.yml` if needed.

### Timezone Configuration

Set your timezone in `docker-compose.yml`:
```yaml
environment:
  - TZ=Asia/Seoul  # Change to your timezone
```

### Troubleshooting Docker

**Container keeps restarting:**
```bash
docker-compose logs dns-updater
```
Check for configuration errors or missing config.yaml.

**Cron not running:**
```bash
docker-compose exec dns-updater crontab -l
docker-compose exec dns-updater ps aux | grep cron
```

**Manual test inside container:**
```bash
docker-compose exec dns-updater python /app/update_dns.py
```

## Configuration

All configuration is managed through the `config.yaml` file. See `config.example.yaml` for a fully documented example.

### Configuration File Structure

```yaml
cloudflare:
  zone_id: "your_zone_id_here"           # CloudFlare Zone ID
  api_token: "your_api_token_here"       # CloudFlare API Token
  api_base_url: "https://api.cloudflare.com/client/v4"

dns:
  record_name: "unifi.example.com"       # DNS record to update
  isp1_hostname: "isp1.example.com"      # First ISP hostname
  isp2_hostname: "isp2.example.com"      # Second ISP hostname
  ttl: 120                                # DNS TTL in seconds
  proxied: false                          # Proxy through CloudFlare

retry:
  max_retries: 3                          # Max retry attempts
  initial_delay: 1.0                      # Initial retry delay (seconds)
  backoff_factor: 2.0                     # Exponential backoff multiplier
  dns_initial_delay: 2.0                  # DNS resolution retry delay

timeouts:
  api_timeout: 30                         # API request timeout (seconds)
  dns_timeout: 10                         # DNS resolution timeout (seconds)

logging:
  level: "INFO"                           # DEBUG, INFO, WARNING, ERROR, CRITICAL
  log_file: "/var/log/dns-updater.log"   # Log file path (or null)
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  date_format: "%Y-%m-%d %H:%M:%S"
```

### Finding Your CloudFlare Credentials

1. **Zone ID**: Found in CloudFlare Dashboard → Select your domain → Overview (right sidebar)
2. **API Token**: CloudFlare Dashboard → My Profile → API Tokens → Create Token
   - Use "Edit zone DNS" template
   - Select your specific zone
   - Copy the generated token

## Logging

The script logs to both console and file (configurable in `config.yaml`):
- **Console**: Real-time output to stdout
- **Log File**: Persistent log file (default: `/var/log/dns-updater.log`)

### Log Levels
- **DEBUG**: Detailed information for debugging (includes record IDs, full responses)
- **INFO**: General operational messages (default)
- **WARNING**: Non-critical issues (e.g., partial failures, retries)
- **ERROR**: Errors that don't stop execution
- **CRITICAL**: Fatal errors requiring immediate attention

### Changing Log Level
Edit `config.yaml`:
```yaml
logging:
  level: "DEBUG"  # Change to desired level
```

### Log File Permissions
Ensure the log directory exists and has write permissions:
```bash
sudo mkdir -p /var/log
sudo touch /var/log/dns-updater.log
sudo chown $USER:$USER /var/log/dns-updater.log
```

Or use a user-writable location:
```yaml
logging:
  log_file: "./logs/dns-updater.log"  # Relative to script directory
```

## Retry Logic

All network operations include automatic retry with exponential backoff (configurable in `config.yaml`):

**Default Settings:**
- **DNS Resolution**: 3 retries with 2s initial delay
- **API Calls**: 3 retries with 1s initial delay
- **Backoff Factor**: 2x (delays: 1s → 2s → 4s)

**Customization:**
```yaml
retry:
  max_retries: 5              # Increase retry attempts
  initial_delay: 0.5          # Faster initial retry
  backoff_factor: 1.5         # Less aggressive backoff
  dns_initial_delay: 3.0      # Longer DNS retry delay
```

## Error Handling

The script handles various failure scenarios:
- **Network timeouts**: Configurable timeouts for API calls and DNS resolution
- **CloudFlare API errors**: Detailed error messages with retry logic
- **DNS resolution failures**: Automatic retries with exponential backoff
- **Partial success**: Continues if one IP updates successfully
- **Missing dependencies**: Detects missing `dig` command
- **Configuration errors**: Validates config file on startup
- **File permissions**: Graceful fallback if log file is not writable

## Requirements

- **Python**: 3.6 or higher
- **System Tools**: `dig` command (install via `dnsutils` or `bind-tools` package)
- **CloudFlare**: API token with DNS edit permissions
- **Permissions**: Write access to log file location (if file logging enabled)

### Installing System Dependencies

**Debian/Ubuntu:**
```bash
sudo apt-get install dnsutils
```

**RHEL/CentOS/Fedora:**
```bash
sudo yum install bind-utils
```

**macOS:**
```bash
brew install bind
```

## File Structure

```
isp-address-updater/
├── .venv/                    # Virtual environment (native Python)
├── logs/                     # Log files (created by Docker)
├── update_dns.py             # Main script
├── config.yaml               # Your configuration (create from example)
├── config.example.yaml       # Configuration template
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # Docker Compose configuration
├── docker-entrypoint.sh      # Container entrypoint script
├── Makefile                  # Helper commands for Docker
├── .dockerignore             # Docker build exclusions
├── .gitignore                # Git exclusions
└── README.md                 # This file
```

## Troubleshooting

### Configuration file not found
```
Configuration error: Configuration file not found: /path/to/config.yaml
Please create config.yaml from config.example.yaml
```
**Solution**: Copy `config.example.yaml` to `config.yaml` and edit with your settings.

### Missing required field
```
Configuration error: Missing required field 'zone_id' in section 'cloudflare'
```
**Solution**: Ensure all required fields are present in `config.yaml`. Compare with `config.example.yaml`.

### dig command not found
```
CRITICAL - 'dig' command not found. Please install dnsutils/bind-tools package.
```
**Solution**: Install the appropriate DNS utilities package for your system (see Requirements).

### Permission denied on log file
```
Warning: Could not create log file /var/log/dns-updater.log: Permission denied
Continuing with console logging only...
```
**Solution**: Either fix permissions or use a user-writable log location in `config.yaml`.

## Security Considerations

- **Protect config.yaml**: Contains sensitive API tokens. Set appropriate file permissions:
  ```bash
  chmod 600 config.yaml
  ```
- **Use restricted API tokens**: Create CloudFlare API tokens with minimal permissions (DNS edit only)
- **Secure log files**: Log files may contain IP addresses and system information
- **Environment variables**: For production, consider using environment variables for sensitive data
