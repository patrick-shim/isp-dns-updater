.PHONY: help prepare config build up down restart logs logs-follow shell clean test run-once

help:
	@echo "CloudFlare DNS Updater - Docker Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  prepare      Create local config and secret directories"
	@echo "  config       Validate the Docker Compose configuration"
	@echo "  build        Build the Docker image"
	@echo "  up           Start the container in background"
	@echo "  down         Stop and remove the container"
	@echo "  restart      Restart the container"
	@echo "  logs         Show container logs"
	@echo "  logs-follow  Follow container logs in real-time"
	@echo "  shell        Open a shell in the running container"
	@echo "  clean        Remove the container and local image"
	@echo "  test         Run unit tests"
	@echo "  run-once     Perform one real DNS reconciliation in Docker"

prepare:
	@test -f config.yaml || cp config.example.yaml config.yaml
	@mkdir -p secrets
	@chmod 700 secrets
	@echo "Edit config.yaml and create the two secret files described in README.md"

config:
	docker compose config --quiet

build:
	docker compose build

up:
	docker compose up -d
	@echo ""
	@echo "Container started! View logs with: make logs-follow"

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs

logs-follow:
	docker compose logs -f

shell:
	docker compose exec dns-updater /bin/sh

clean:
	docker compose down -v
	docker rmi isp-dns-updater:local 2>/dev/null || true

test: build
	docker run --rm --entrypoint python \
		-v "$(CURDIR)/tests:/app/tests:ro" \
		isp-dns-updater:local -m unittest discover -s /app/tests -v

run-once:
	docker compose run --rm dns-updater python /app/update_dns.py
