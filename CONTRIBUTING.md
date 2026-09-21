# Contributing to CloudFlare DNS Updater

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, Docker version)
- Relevant log excerpts (with credentials redacted)

### Suggesting Features

Feature requests are welcome! Please open an issue describing:
- The use case for the feature
- How it would work
- Any alternative solutions you've considered

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Test thoroughly**
5. **Commit with clear messages**: Follow conventional commits format
6. **Push to your fork**
7. **Open a Pull Request**

## Development Setup

### Local Development

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/isp-address-updater.git
cd isp-address-updater

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy example config
cp config.example.yaml config.yaml
# Edit config.yaml with test credentials

# Run tests
python update_dns.py
```

### Docker Development

```bash
# Build and test
docker compose build
docker compose up

# View logs
docker compose logs -f

# Shell access
docker compose exec dns-updater sh
```

## Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and small
- Use meaningful variable names

## Testing

Before submitting a PR:
- Run `python -m unittest discover -s tests -v`
- Test with your Cloudflare account only when an integration test is necessary
- Test Docker build and deployment
- Verify logging output
- Test error handling scenarios
- Check for credential leaks in logs

## Commit Message Format

Use conventional commits:
```
feat: add support for multiple DNS providers
fix: handle timeout errors gracefully
docs: update README with new examples
chore: update dependencies
```

## Areas for Contribution

We welcome contributions in these areas:

### Features
- Support for additional DNS providers (AWS Route53, Google Cloud DNS)
- Webhook notifications (Slack, Discord, email)
- Health check endpoint
- Prometheus metrics export
- IPv6 support
- Multiple record support

### Improvements
- Unit tests and integration tests
- CI/CD pipeline (GitHub Actions)
- Better error messages
- Performance optimizations
- Documentation improvements

### Bug Fixes
- Any bugs you encounter
- Edge cases in error handling
- Logging improvements

## Documentation

When adding features:
- Update README.md
- Update config.example.yaml
- Add inline code comments
- Update SECURITY.md if security-related

## Questions?

Feel free to open an issue for questions or join discussions in existing issues.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
