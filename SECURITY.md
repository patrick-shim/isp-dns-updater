# Security policy

## Credential model

The Docker deployment reads Cloudflare credentials from these host files:

```text
secrets/cloudflare_zone_id
secrets/cloudflare_api_token
```

Docker Compose grants only the `dns-updater` service access and mounts them at
`/run/secrets`. The application reads them through the `zone_id_file` and
`api_token_file` settings. Neither value is copied into the image.

Compose file-backed secrets protect credentials from source control and from
being embedded in image layers or ordinary environment variables. They are not
an encrypted secret vault: the host files still require OS permissions, disk
protection, backups with suitable access controls, and trusted VM admins.

## Required practices

- Use a scoped Cloudflare API token, never the Global API Key.
- Grant only **Zone → DNS → Edit** and only for the intended zone.
- Store only one value in each secret file, set the directory to mode `700`, and
  set the files to owner `pashim`, group ID `10001`, mode `640`. GID `10001`
  matches the unprivileged container group without granting access to other
  host users.
- Keep `config.yaml`, `.env`, and `secrets/` ignored. Check before every push:

  ```bash
  git check-ignore -v config.yaml secrets/cloudflare_api_token
  git status --short
  git diff --cached
  ```

- Do not paste tokens into issue reports, logs, screenshots, shell scripts, or
  Compose environment fields.
- Restrict SSH and Proxmox access, enable VM backups, and keep Ubuntu and Docker
  patched.

The Zone ID is an identifier rather than an authentication secret, but this
deployment stores it beside the token to keep all Cloudflare-specific values out
of the repository.

## Container controls

The supplied Compose definition:

- runs as UID/GID `10001`, not root;
- uses a read-only root filesystem and a small temporary filesystem;
- drops all Linux capabilities and enables `no-new-privileges`;
- publishes no ports;
- rotates Docker logs; and
- limits CPU and memory.

Logs contain record names and public IP addresses, but never the authorization
header or token. Treat them as infrastructure metadata.

## Rotation and incident response

If a token might be exposed:

1. Revoke it immediately in Cloudflare under **API Tokens**.
2. Review Cloudflare audit logs and DNS records for unauthorized activity.
3. Create a new zone-scoped DNS Edit token.
4. Replace `secrets/cloudflare_api_token`, set group ID `10001`, and restore
   mode `640`.
5. Restart and verify:

   ```bash
   docker compose restart
   docker compose logs --tail=100
   docker compose ps
   ```

If a real token was ever committed, removing it from the latest file is not
enough: revoke it first, then separately purge it from Git history before making
the repository public or sharing clones.

## Reporting vulnerabilities

Report security problems privately to the repository owner rather than opening
a public issue containing exploit details or credentials.
