# Security Policy

## Protecting Your Credentials

This application requires sensitive CloudFlare API credentials. Please follow these security best practices:

### 1. Never Commit Credentials

**IMPORTANT**: The `config.yaml` file contains your CloudFlare API token and Zone ID. This file is already excluded in `.gitignore` to prevent accidental commits.

Before pushing to GitHub:
```bash
# Verify config.yaml is not tracked
git status

# If it appears, ensure .gitignore is working
git check-ignore config.yaml
```

### 2. Use Restricted API Tokens

When creating your CloudFlare API token:
- Use the **"Edit zone DNS"** template (not Global API Key)
- Limit permissions to **DNS:Edit** only
- Restrict to specific zones
- Set IP address restrictions if possible
- Use token expiration dates

### 3. File Permissions

Protect your configuration file on the host system:
```bash
chmod 600 config.yaml
```

### 4. Docker Security

When using Docker:
- Configuration is mounted as **read-only** in the container
- Logs may contain IP addresses - secure the `./logs` directory
- Use Docker secrets for production deployments (see below)

### 5. Production Deployment with Docker Secrets

For production environments, use Docker secrets instead of mounting config.yaml:

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  dns-updater:
    build: .
    secrets:
      - cloudflare_zone_id
      - cloudflare_api_token
    environment:
      - ZONE_ID_FILE=/run/secrets/cloudflare_zone_id
      - API_TOKEN_FILE=/run/secrets/cloudflare_api_token

secrets:
  cloudflare_zone_id:
    external: true
  cloudflare_api_token:
    external: true
```

### 6. Environment Variables (Alternative)

You can also use environment variables for sensitive data:

```bash
export CLOUDFLARE_ZONE_ID="your_zone_id"
export CLOUDFLARE_API_TOKEN="your_token"
```

Then modify `config.yaml` to reference them:
```yaml
cloudflare:
  zone_id: "${CLOUDFLARE_ZONE_ID}"
  api_token: "${CLOUDFLARE_API_TOKEN}"
```

## Reporting Security Issues

If you discover a security vulnerability, please email the maintainers directly instead of opening a public issue.

## Security Checklist

Before deploying:
- [ ] `config.yaml` is in `.gitignore`
- [ ] Using restricted CloudFlare API token (not Global API Key)
- [ ] File permissions set to 600 on `config.yaml`
- [ ] Logs directory has appropriate permissions
- [ ] API token has expiration date set
- [ ] Token is restricted to specific zones only
- [ ] No credentials in environment variables on shared systems
- [ ] Docker secrets used for production deployments

## What Gets Logged

The application logs:
- Timestamps of DNS updates
- Resolved IP addresses
- CloudFlare API responses (without credentials)
- Error messages

The application does NOT log:
- API tokens
- Full API requests with headers
- Passwords or secrets

## Revoking Compromised Tokens

If your API token is compromised:

1. **Immediately revoke** the token in CloudFlare Dashboard
2. Generate a new token with restricted permissions
3. Update your `config.yaml` with the new token
4. Restart the application/container
5. Review CloudFlare audit logs for unauthorized changes

## Additional Resources

- [CloudFlare API Token Best Practices](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)
- [Docker Secrets Documentation](https://docs.docker.com/engine/swarm/secrets/)
