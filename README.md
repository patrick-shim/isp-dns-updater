# ISP DNS Updater

Keeps one Cloudflare A-record set synchronized with the public IPv4 addresses
published by two ISP hostnames. The infrastructure defaults remain:

- `isp1.neostation.co.kr`
- `isp2.neostation.co.kr`

The destination record is intentionally not committed. Set `dns.record_name` in
your local `config.yaml` to the Cloudflare record that should receive both IPs.

The recommended deployment is Docker Compose on the Ubuntu 26.04 VM in Proxmox.
See [docs/PROXMOX_UBUNTU.md](docs/PROXMOX_UBUNTU.md) for the complete VM and
Docker installation procedure.

## What changed for the Proxmox deployment

- Cloudflare credentials are Compose file-backed secrets and are never copied
  into the image or stored in tracked YAML.
- The container runs as an unprivileged user with a read-only root filesystem,
  all Linux capabilities dropped, and no inbound ports.
- The updater runs once at startup and every 60 seconds after that. Docker owns
  restart behavior, health checks, and log rotation; no cron daemon is needed.
- DNS reconciliation is non-disruptive: missing records are created before stale
  records are removed, and unchanged records do not generate API writes.
- The broken upstream image build dependency on an absent `config.yaml` is gone.

## Quick start after Docker is installed

```bash
git clone https://github.com/patrick-shim/isp-dns-updater.git
cd isp-dns-updater
make prepare
```

Edit `config.yaml` and replace only this placeholder with your destination:

```yaml
dns:
  record_name: "edge.neostation.co.kr"  # example; choose your actual record
  isp1_hostname: "isp1.neostation.co.kr"
  isp2_hostname: "isp2.neostation.co.kr"
```

Create the two local secret files:

```bash
chmod 700 secrets
nano secrets/cloudflare_zone_id
nano secrets/cloudflare_api_token
chmod 600 secrets/cloudflare_zone_id secrets/cloudflare_api_token
```

Each file must contain only its value. A final newline is allowed. Then validate,
build, and perform one real reconciliation before enabling the service:

```bash
make config
make build
make test
make run-once
make up
docker compose ps
make logs-follow
```

`make run-once` changes the configured Cloudflare DNS record. Confirm
`dns.record_name` before running it.

## Getting the Cloudflare values

### Zone ID

1. Sign in to the Cloudflare dashboard and select `neostation.co.kr`.
2. On the domain Overview page, find the **API** section near the bottom.
3. Copy **Zone ID** into `secrets/cloudflare_zone_id`.

### API token

1. In Cloudflare, open **My Profile → API Tokens** and select **Create Token**.
   An account-owned token is also suitable if you prefer a service identity.
2. Start from the **Edit zone DNS** template.
3. Name it for this VM, for example `proxmox-isp-dns-updater`.
4. Keep permission **Zone → DNS → Edit**.
5. Under zone resources, restrict it to only the account and
   `neostation.co.kr` zone.
6. Optionally set token expiration and a client-IP restriction. Only use an IP
   restriction if the VM's outbound address is stable enough not to lock out
   the updater.
7. Create the token and immediately copy the one-time value into
   `secrets/cloudflare_api_token`.

Use a scoped API token, not the Global API Key. If the token is lost, create a
new one; Cloudflare does not show the secret again. See [SECURITY.md](SECURITY.md)
for rotation and storage guidance.

## Configuration

Safe settings live in the ignored `config.yaml`, copied from
`config.example.yaml`. The example points credential fields at Docker's mounted
secret paths:

```yaml
cloudflare:
  zone_id_file: "/run/secrets/cloudflare_zone_id"
  api_token_file: "/run/secrets/cloudflare_api_token"
  api_base_url: "https://api.cloudflare.com/client/v4"

dns:
  record_name: "CHANGE_ME.neostation.co.kr"
  isp1_hostname: "isp1.neostation.co.kr"
  isp2_hostname: "isp2.neostation.co.kr"
  ttl: 120
  proxied: false
```

The application also accepts `CLOUDFLARE_ZONE_ID_FILE` and
`CLOUDFLARE_API_TOKEN_FILE`; these override the YAML file paths. Direct values in
the legacy `zone_id`/`api_token` YAML fields or matching environment variables
remain supported for compatibility, but file-backed secrets are recommended.

Set the schedule or timezone for one invocation without editing Compose:

```bash
DNS_UPDATER_INTERVAL_SECONDS=300 TZ=Asia/Seoul docker compose up -d
```

The health check expects a successful update within the last five minutes. If
you set an interval longer than five minutes, adjust the health-check threshold
in `docker-compose.yml` too.

## Operations

```bash
docker compose ps                    # service and health state
docker compose logs --tail=100       # recent logs
docker compose logs -f               # follow logs
docker compose restart               # restart after config changes
git pull --ff-only
docker compose up -d --build          # deploy an updated checkout
docker compose down                  # stop and remove the container
```

The service exposes no port. It needs outbound DNS (UDP/TCP 53) to resolve the
ISP names and outbound HTTPS (TCP 443) to call Cloudflare.

## How reconciliation works

On every run, the updater:

1. Resolves the first valid A answer for both ISP hostnames.
2. Lists A records for `dns.record_name` in the configured Cloudflare zone.
3. Keeps one record for each desired IP and creates any missing record first.
4. Removes stale or duplicate A records only after all desired records exist.

If either ISP hostname cannot be resolved, the run exits without changing
Cloudflare. If a replacement cannot be created, stale records are deliberately
left in place to avoid taking the destination offline.

## Development and native execution

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

For a native run, point the two `_FILE` environment variables at local secret
files and use a native config whose credential file paths need not be valid:

```bash
export CLOUDFLARE_ZONE_ID_FILE="$PWD/secrets/cloudflare_zone_id"
export CLOUDFLARE_API_TOKEN_FILE="$PWD/secrets/cloudflare_api_token"
DNS_UPDATER_CONFIG="$PWD/config.yaml" python update_dns.py
```

## Troubleshooting

- `Replace dns.record_name`: edit the placeholder in `config.yaml`.
- `Could not read Cloudflare ... file`: create both files under `./secrets` and
  verify their permissions and spelling.
- Cloudflare `403`: check that the token has DNS Edit access to the exact zone
  whose Zone ID is in the secret file.
- Container is unhealthy: use `docker compose logs --tail=200`; health becomes
  healthy after the first successful reconciliation.
- Wrong IPs: run `dig +short A isp1.neostation.co.kr` and the corresponding
  `isp2` command from the VM to verify its resolver sees the current values.
