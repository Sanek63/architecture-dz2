COMPOSE ?= docker compose
ENV_FILE ?= deploy/env/dev.env

READ_API_REPLICAS ?= 1
WRITE_API_REPLICAS ?= 1
TIMELINE_SERVICE_REPLICAS ?= 1
PUBLICATION_SERVICE_REPLICAS ?= 1
USER_SERVICE_REPLICAS ?= 1
POSTINFO_SERVICE_REPLICAS ?= 1
POST_UPDATE_CONSUMER_REPLICAS ?= 1
SEND_NOTIFICATION_CONSUMER_REPLICAS ?= 1

.PHONY: help install check test-system up up-perf down restart ps logs clean

help:
	@echo "install      - install Python deps"
	@echo "check        - compile modules + run smoke test"
	@echo "test-system  - full e2e test via gateway endpoints from API spec"
	@echo "up           - start stack with \\$(ENV_FILE)"
	@echo "up-perf      - start scaled stack (override replicas via make vars)"
	@echo "down         - stop stack"
	@echo "restart      - restart stack"
	@echo "ps           - show containers"
	@echo "logs         - tail logs"
	@echo "clean        - stop stack and remove volumes"

install:
	pip install -r requirements.txt

check:
	python -m compileall common services consumers
	PYTHONPATH=. python tests/smoke_test.py

test-system:
	@set -e; \
	trap '$(COMPOSE) --env-file $(ENV_FILE) down -v' EXIT; \
	$(COMPOSE) --env-file $(ENV_FILE) up -d --build; \
	PYTHONPATH=. python tests/system_test.py

up:
	$(COMPOSE) --env-file $(ENV_FILE) up -d --build

up-perf:
	$(COMPOSE) --env-file deploy/env/perf.env up -d --build \
		--scale read-api=$(READ_API_REPLICAS) \
		--scale write-api=$(WRITE_API_REPLICAS) \
		--scale timeline-service=$(TIMELINE_SERVICE_REPLICAS) \
		--scale publication-service=$(PUBLICATION_SERVICE_REPLICAS) \
		--scale user-service=$(USER_SERVICE_REPLICAS) \
		--scale postinfo-service=$(POSTINFO_SERVICE_REPLICAS) \
		--scale post-update-consumer=$(POST_UPDATE_CONSUMER_REPLICAS) \
		--scale send-notification-consumer=$(SEND_NOTIFICATION_CONSUMER_REPLICAS)

down:
	$(COMPOSE) --env-file $(ENV_FILE) down

restart: down up

ps:
	$(COMPOSE) --env-file $(ENV_FILE) ps

logs:
	$(COMPOSE) --env-file $(ENV_FILE) logs --tail=120

clean:
	$(COMPOSE) --env-file $(ENV_FILE) down -v
