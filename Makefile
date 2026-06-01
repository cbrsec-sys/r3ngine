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

.PHONY: setup certs up devup build username pull down stop restart rm logs fullupgrade erase

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

erase:			## !! DESTRUCTIVE !! Delete ALL containers, images, volumes, build cache, and local artifacts for a clean slate.
	@echo ""
	@echo "============================================================"
	@echo "  r3ngine ERASE -- COMPLETE RESET"
	@echo "============================================================"
	@echo ""
	@echo "  WARNING: This will PERMANENTLY and IRREVERSIBLY delete:"
	@echo ""
	@echo "  - All r3ngine Docker containers (running or stopped)"
	@echo "  - All r3ngine Docker images"
	@echo "  - ALL Docker volumes (scan data, PostgreSQL, Neo4j, wordlists)"
	@echo "  - Docker build layer cache"
	@echo "  - Local Python artifacts (__pycache__, *.pyc, staticfiles/)"
	@echo "  - Local frontend artifacts (dist/, node_modules/)"
	@echo ""
	@echo "  ALL SCAN DATA AND DATABASE CONTENT WILL BE LOST."
	@echo "  There is no undo. Back up first if needed."
	@echo ""
	@echo "============================================================"
	@echo ""
	@printf "  Type 'erase' to confirm full reset: "; \
	  read confirm; \
	  [ "$${confirm}" = "erase" ] || { printf "\n  Erase cancelled.\n\n"; exit 1; }
	@echo ""
	@echo "[1/5] Stopping services and removing all containers, volumes, and images..."
	@${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} down --volumes --rmi all --remove-orphans || true
	@echo ""
	@echo "[2/5] Pruning Docker build cache..."
	@docker builder prune -af || true
	@echo ""
	@echo "[3/5] Removing any remaining dangling Docker volumes..."
	@docker volume prune -f || true
	@echo ""
	@echo "[4/5] Removing local Python build artifacts..."
	@find web -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find web -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true
	@rm -rf web/staticfiles
	@echo ""
	@echo "[5/5] Removing local frontend build artifacts..."
	@rm -rf frontend/dist frontend/node_modules
	@echo ""
	@echo "============================================================"
	@echo "  Erase complete. All data has been wiped."
	@echo "  Run 'make up' to start fresh."
	@echo "============================================================"
	@echo ""

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
