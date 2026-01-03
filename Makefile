.PHONY: help build up down restart logs logs-follow shell clean

help:
	@echo "CloudFlare DNS Updater - Docker Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  build        Build the Docker image"
	@echo "  up           Start the container in background"
	@echo "  down         Stop and remove the container"
	@echo "  restart      Restart the container"
	@echo "  logs         Show container logs"
	@echo "  logs-follow  Follow container logs in real-time"
	@echo "  shell        Open a shell in the running container"
	@echo "  clean        Remove container, image, and logs"
	@echo "  test         Run the script once without Docker"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo ""
	@echo "Container started! View logs with: make logs-follow"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs

logs-follow:
	docker-compose logs -f

shell:
	docker-compose exec dns-updater /bin/bash

clean:
	docker-compose down -v
	docker rmi cloudflare-dns-updater 2>/dev/null || true
	rm -rf logs/

test:
	@if [ -d ".venv" ]; then \
		.venv/bin/python update_dns.py; \
	else \
		python3 update_dns.py; \
	fi
