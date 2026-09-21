# Proxmox VM deployment: Ubuntu 26.04

This runbook assumes a normal Ubuntu 26.04 LTS virtual machine on Proxmox VE.
Run the commands inside the VM, not on the Proxmox host.

## 1. Prepare the VM

A small VM is sufficient: 1 vCPU, 1 GB RAM, and 8-16 GB disk. Attach its NIC to
the appropriate Proxmox bridge (commonly `vmbr0`) and give it reliable DNS and
internet egress. The updater does not listen on any network port.

Install basic maintenance packages and the guest agent:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y ca-certificates curl git qemu-guest-agent
sudo systemctl enable --now qemu-guest-agent
```

In Proxmox, enable **QEMU Guest Agent** for the VM. Apply your normal VM backup
policy. A static LAN address is convenient for administration but is not needed
by the updater itself.

## 2. Install Docker Engine from Docker's repository

Remove packages that can conflict with Docker CE. On a new VM it is normal for
APT to report that none are installed:

```bash
sudo apt remove -y docker.io docker-compose docker-compose-v2 docker-doc \
  podman-docker containerd runc || true
```

Add Docker's official signing key and Ubuntu repository:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run --rm hello-world
sudo docker compose version
```

Docker's `docker` group is effectively root-level access. Either keep using
`sudo docker ...`, or add only a trusted administrator and then log out and back
in before continuing:

```bash
sudo usermod -aG docker "$USER"
```

## 3. Install the updater

The following keeps application state under `/opt` while allowing the current
administrator to update it:

```bash
sudo install -d -o "$USER" -g "$USER" /opt/isp-dns-updater
git clone https://github.com/patrick-shim/isp-dns-updater.git \
  /opt/isp-dns-updater
cd /opt/isp-dns-updater
make prepare
```

Edit the local configuration:

```bash
nano config.yaml
```

Replace `CHANGE_ME.neostation.co.kr` with the one destination DNS name that
should have A records for both WANs. Leave these discovery names intact:

```yaml
isp1_hostname: "isp1.neostation.co.kr"
isp2_hostname: "isp2.neostation.co.kr"
```

## 4. Add Cloudflare credentials

Follow the credential-creation steps in the main README. Then place the values
in separate local files, one value per file:

```bash
install -m 700 -d secrets
nano secrets/cloudflare_zone_id
nano secrets/cloudflare_api_token
chmod 600 secrets/cloudflare_zone_id secrets/cloudflare_api_token
```

Do not place credentials in `config.yaml`, `docker-compose.yml`, `.env`, a shell
script, or a Git commit. Confirm Git ignores the local material:

```bash
git check-ignore -v config.yaml secrets/cloudflare_zone_id \
  secrets/cloudflare_api_token
git status --short
```

`git status` should show no local credential files.

## 5. Validate and start

```bash
make config
make build
make test
make run-once
make up
docker compose ps
docker compose logs --tail=100
```

The one-off run performs a real Cloudflare change. It should report that the
destination points to the two resolved WAN addresses. The long-running service
then checks every minute. It will become healthy after a successful run.

Check the public answers from the VM:

```bash
dig +short A isp1.neostation.co.kr
dig +short A isp2.neostation.co.kr
dig +short A YOUR_DESTINATION.neostation.co.kr
```

## 6. Firewall and lifecycle

No inbound application rule is required. Permit outbound DNS on UDP/TCP 53 and
HTTPS on TCP 443. If the VM uses UFW, remember that Docker-published ports can
bypass some UFW rules; this Compose service publishes no ports.

Docker starts at boot, and `restart: unless-stopped` brings the updater back
after VM or daemon restarts. Verify this once during a maintenance window:

```bash
sudo reboot
```

After reconnecting:

```bash
cd /opt/isp-dns-updater
docker compose ps
docker compose logs --since=10m
```

## Updating

Review changes before rebuilding:

```bash
cd /opt/isp-dns-updater
git status --short
git pull --ff-only
docker compose build --pull
docker compose up -d
docker image prune
```

`config.yaml` and `secrets/` stay local and ignored. Do not use `git clean -x`
in this directory because it would remove those ignored deployment files.

## Rollback

Record the known-good commit before updating:

```bash
git rev-parse HEAD
```

If an update fails, check out that exact known-good commit and rebuild. Do not
reset or overwrite `config.yaml` or `secrets/`.
