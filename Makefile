include .env
.DEFAULT_GOAL:=help

# Credits: https://github.com/sherifabdlnaby/elastdocker/

# This for future release of Compose that will use Docker Buildkit, which is much efficient.
COMPOSE_PREFIX_CMD := COMPOSE_DOCKER_CLI_BUILD=1

COMPOSE_ALL_FILES := -f docker-compose.yml
COMPOSE_DEV_FILES := -f docker-compose.dev.yml
SERVICES          := db web proxy redis neo4j temporal temporal-python-orchestrator temporal-go-executor

# Check if 'docker compose' command is available, otherwise use 'docker-compose'
DOCKER_COMPOSE := $(shell if command -v docker > /dev/null && docker compose version > /dev/null 2>&1; then echo "docker compose"; else echo "docker-compose"; fi)
$(info Using: $(shell echo "$(DOCKER_COMPOSE)"))

# --------------------------

.PHONY: setup certs up devup build username pull down stop restart rm logs fullupgrade

certs:		    ## Generate certificates.
	@${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} -f docker-compose.setup.yml run --rm certs

setup:			## Generate certificates.
	@make certs

up:				## Build and start all services in production mode.
	DEBUG=0 ${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} up -d --build ${SERVICES}

devup:				## Build and start all services in development mode.
	DEBUG=1 ${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_DEV_FILES} up -d --build ${SERVICES}

build:			## Build all services.
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} build ${SERVICES}

username:		## Generate Username (Use only after make up).
ifeq ($(isNonInteractive), true)
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} exec web python3 manage.py createsuperuser --username ${DJANGO_SUPERUSER_USERNAME} --email ${DJANGO_SUPERUSER_EMAIL} --noinput
else
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} exec web python3 manage.py createsuperuser
endif

changepassword:	## Change password for user
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} exec web python3 manage.py changepassword

migrate:		## Apply migrations
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} exec web python3 manage.py migrate

pull:			## Pull Docker images.
	docker login docker.pkg.github.com
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} pull

down:			## Down all services.
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} down

stop:			## Stop all services.
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} stop ${SERVICES}

restart:		## Restart all services.
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} restart ${SERVICES}

rm:				## Remove all services containers.
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} $(COMPOSE_ALL_FILES) rm -f ${SERVICES}

loadtools:		## Load external tools.
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} exec web python3 manage.py loaddata external_tools.yaml

loadengines:		## Load default engines.
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} exec web python3 manage.py loaddata default_scan_engines.yaml

test:
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} $(COMPOSE_ALL_FILES) exec web python3 manage.py test

logs:			## Tail all logs with -n 1000.
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} $(COMPOSE_ALL_FILES) logs --follow --tail=1000 ${SERVICES}

images:			## Show all Docker images.
	${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} $(COMPOSE_ALL_FILES) images ${SERVICES}

prune:			## Remove containers and delete volume data.
	@make stop && make rm && docker volume prune -f

fullupgrade:		## REQUIRED for v3.2.0+: migrate from Celery to Temporal.
	@echo ""
	@echo "============================================================"
	@echo "  r3ngine FULL UPGRADE — v3.2.0 (Celery → Temporal)"
	@echo "============================================================"
	@echo ""
	@echo "  This upgrade makes IRREVERSIBLE changes to your deployment:"
	@echo ""
	@echo "  1. All Celery and Celery Beat containers will be removed."
	@echo "  2. Temporal workflow engine containers will be started."
	@echo "  3. Database migrations will apply new Temporal models"
	@echo "     and remove legacy django_celery_beat tables."
	@echo "  4. All images will be rebuilt from scratch."
	@echo "  5. Any in-progress scans WILL be interrupted."
	@echo ""
	@echo "  YOUR DATA IS SAFE:"
	@echo "  - All Docker VOLUMES are preserved (scan_results, postgres_data,"
	@echo "    nuclei_templates, wordlist, etc.)."
	@echo "  - Only CONTAINERS and IMAGES are rebuilt — no volume data is"
	@echo "    deleted or modified by this script."
	@echo ""
	@echo "  BEFORE PROCEEDING:"
	@echo "  - Ensure you have pulled the latest code  (git pull)"
	@echo "  - Ensure no critical scans are running"
	@echo "  - Back up your database if required"
	@echo ""
	@echo "  For full upgrade instructions see README.md or CHANGELOG.md"
	@echo "============================================================"
	@echo ""
	@printf "  Type 'yes' to confirm and proceed: "; \
	  read confirm; \
	  [ "$${confirm}" = "yes" ] || { printf "\n  Upgrade cancelled.\n\n"; exit 1; }
	@echo ""
	@echo "[1/6] Stopping all running services (volumes are NOT removed)..."
	@${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} down --remove-orphans || true
	@echo ""
	@echo "[2/6] Pulling latest images and rebuilding containers (no cache)..."
	@${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} build --no-cache ${SERVICES}
	@echo ""
	@echo "[3/6] Starting database service..."
	@${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} up -d db redis
	@sleep 8
	@echo ""
	@echo "[4/6] Applying database migrations..."
	@${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} run --rm web python3 manage.py migrate --noinput
	@echo ""
	@echo "[5/6] Starting all services..."
	@DEBUG=0 ${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} up -d ${SERVICES}
	@echo ""
	@echo "[6/6] Verifying services are healthy..."
	@sleep 5
	@${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} ps
	@echo ""
	@echo "============================================================"
	@echo "  Full upgrade complete."
	@echo "  Temporal UI: http://localhost:8080"
	@echo "  r3ngine UI:  https://localhost"
	@echo "============================================================"
	@echo ""

help:			## Show this help.
	@echo "Make application Docker images and manage containers using Docker Compose files."
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m (default: help)\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
