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

fullupgrade:		## Upgrade to Django 5.2 + PostgreSQL 16 + Gunicorn (rebuilds images, migrates DB safely).
	@echo ""
	@echo "============================================================"
	@echo "  r3ngine FULL UPGRADE — v3.4.1"
	@echo "  Django 5.2 LTS  |  PostgreSQL 16  |  Gunicorn + Uvicorn"
	@echo "============================================================"
	@echo ""
	@echo "  This upgrade will:"
	@echo ""
	@echo "  1. Back up your PostgreSQL database to ./backups/ before"
	@echo "     touching anything."
	@echo "  2. Rebuild all images with the new Django 5.2 + channels 4.x"
	@echo "     packages (no cache)."
	@echo "  3. Apply pending database migrations safely — waits for the"
	@echo "     database healthcheck to pass before attempting any migration."
	@echo "  4. Verify migrations completed with zero failures before"
	@echo "     starting the full stack."
	@echo "  5. Switch the production web server from runserver to"
	@echo "     Gunicorn + Uvicorn ASGI workers."
	@echo "  6. Any in-progress scans WILL be interrupted."
	@echo ""
	@echo "  YOUR DATA IS SAFE:"
	@echo "  - A timestamped SQL dump is saved to ./backups/ BEFORE any"
	@echo "    changes. If anything fails, restore with:"
	@echo "    psql -U \$$POSTGRES_USER \$$POSTGRES_DB < backups/<dump>.sql"
	@echo "  - All Docker VOLUMES are preserved (scan_results, postgres_data,"
	@echo "    nuclei_templates, wordlist, etc.)."
	@echo "  - Only CONTAINERS and IMAGES are rebuilt — no volume data is"
	@echo "    deleted or modified by this script."
	@echo ""
	@echo "  NOTE: PostgreSQL image version in docker-compose.yml must be"
	@echo "  updated to postgres:16-alpine separately (requires dump/restore)."
	@echo "  See UPGRADES.md for the full PostgreSQL 16 migration procedure."
	@echo ""
	@echo "  BEFORE PROCEEDING:"
	@echo "  - Ensure you have pulled the latest code  (git pull)"
	@echo "  - Ensure no critical scans are running"
	@echo "  - Ensure the db service is running  (make up)"
	@echo ""
	@echo "  For full upgrade instructions see README.md or CHANGELOG.md"
	@echo "============================================================"
	@echo ""
	@printf "  Type 'yes' to confirm and proceed: "; \
	  read confirm; \
	  [ "$${confirm}" = "yes" ] || { printf "\n  Upgrade cancelled.\n\n"; exit 1; }
	@echo ""
	@echo "[1/7] Creating database backup..."
	@POSTGRES_USER=${POSTGRES_USER} \
	  POSTGRES_DB=${POSTGRES_DB} \
	  DOCKER_COMPOSE_CMD="${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES}" \
	  bash scripts/db_backup.sh
	@echo ""
	@echo "[2/7] Stopping all running services (volumes are NOT removed)..."
	@${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} down --remove-orphans || true
	@echo ""
	@echo "[3/7] Rebuilding all images (no cache)..."
	@${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} build --no-cache ${SERVICES}
	@echo ""
	@echo "[4/7] Starting database and waiting for healthcheck..."
	@${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} up -d db redis
	@echo "  Waiting for PostgreSQL to be ready..."
	@attempt=0; \
	  until ${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} exec -T db \
	    pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB} > /dev/null 2>&1; do \
	    attempt=$$((attempt + 1)); \
	    if [ $$attempt -ge 30 ]; then \
	      echo "  ERROR: Database did not become ready within 60s. Aborting."; \
	      exit 1; \
	    fi; \
	    printf "."; sleep 2; \
	  done; echo " ready."
	@echo ""
	@echo "[5/7] Applying database migrations..."
	@${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} run --rm \
	  -e DEBUG=0 web python3 manage.py migrate --noinput; \
	  MIGRATE_EXIT=$$?; \
	  if [ $$MIGRATE_EXIT -ne 0 ]; then \
	    echo ""; \
	    echo "  ERROR: Migration failed (exit code $$MIGRATE_EXIT)."; \
	    echo "  The database backup is at ./backups/. Investigate before retrying."; \
	    exit $$MIGRATE_EXIT; \
	  fi
	@echo ""
	@echo "  Verifying all migrations are applied..."
	@PENDING=$$(${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} run --rm \
	  -e DEBUG=0 web python3 manage.py showmigrations --plan 2>/dev/null | grep " \[ \]" | wc -l); \
	  if [ "$$PENDING" -gt 0 ]; then \
	    echo "  WARNING: $$PENDING migration(s) still pending after migrate. Check manually."; \
	  else \
	    echo "  All migrations applied successfully."; \
	  fi
	@echo ""
	@echo "[6/7] Starting all services (production mode)..."
	@DEBUG=0 ${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} up -d ${SERVICES}
	@echo ""
	@echo "[7/7] Verifying services are healthy (30s grace period)..."
	@sleep 10
	@${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} ps
	@echo ""
	@echo "  Checking gunicorn started correctly..."
	@${COMPOSE_PREFIX_CMD} ${DOCKER_COMPOSE} ${COMPOSE_ALL_FILES} logs web --tail=20 \
	  | grep -E "Booting worker|UvicornWorker|Starting gunicorn|ERROR" || true
	@echo ""
	@echo "============================================================"
	@echo "  Full upgrade complete."
	@echo "  Temporal UI:    http://localhost:8080"
	@echo "  r3ngine UI:     https://localhost"
	@echo "  Database backup: ./backups/"
	@echo "============================================================"
	@echo ""

help:			## Show this help.
	@echo "Make application Docker images and manage containers using Docker Compose files."
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m (default: help)\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
