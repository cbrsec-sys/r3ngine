#!/bin/bash
# Upgrade the PostgreSQL data volume when the image major version has changed.
# Called by 'make fullupgrade' AFTER services are stopped but BEFORE image rebuild.
#
# Reads the PG_VERSION file from the data volume to detect the current data version.
# Compares it to the target version in docker-compose.yml.
# If they differ:  removes the old volume → starts new container → restores backup.
# If they match:   no-op (exits 0 immediately).
#
# Environment (all passed by Makefile):
#   POSTGRES_USER       - database user
#   POSTGRES_DB         - database name
#   DOCKER_COMPOSE_CMD  - full docker compose command with file flags
#   PG_VOLUME_NAME      - named Docker volume (e.g. r3ngine_postgres_data)
#   BACKUP_DIR          - directory containing pre_upgrade_*.sql files (default: ./backups)

set -euo pipefail

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${DOCKER_COMPOSE_CMD:?DOCKER_COMPOSE_CMD is required}"
: "${PG_VOLUME_NAME:?PG_VOLUME_NAME is required}"

BACKUP_DIR="${BACKUP_DIR:-./backups}"

# Abort early if the data volume doesn't exist yet (fresh install — nothing to upgrade).
if ! docker volume inspect "$PG_VOLUME_NAME" > /dev/null 2>&1; then
    echo "  No existing PostgreSQL volume — fresh install, no upgrade needed."
    exit 0
fi

# Read the PostgreSQL major version written into the data directory.
# Use -v (short form) rather than --mount to avoid Docker version quirks with
# the 'readonly' flag. The || echo "0" is outside the $() so set -e does not
# abort the script if the docker run itself exits non-zero (e.g. missing image).
VOLUME_PG_MAJOR=$(docker run --rm \
    -v "${PG_VOLUME_NAME}:/pgdata:ro" \
    alpine:latest \
    sh -c "cat /pgdata/PG_VERSION 2>/dev/null" 2>/dev/null \
    || echo "0")
VOLUME_PG_MAJOR=$(printf '%s' "$VOLUME_PG_MAJOR" | tr -d '[:space:]')
[ -z "$VOLUME_PG_MAJOR" ] && VOLUME_PG_MAJOR="0"

echo "  Data volume PostgreSQL major version: ${VOLUME_PG_MAJOR}"

# Parse the target major version from the postgres image tag in docker-compose.yml.
TARGET_PG_MAJOR=$(grep 'image:.*postgres:' docker-compose.yml 2>/dev/null | \
    grep -oE 'postgres:[0-9]+' | cut -d: -f2 | head -1 || echo "16")

echo "  Target PostgreSQL major version:  ${TARGET_PG_MAJOR}"

if [ "${VOLUME_PG_MAJOR}" = "${TARGET_PG_MAJOR}" ]; then
    echo "  Data volume already at PostgreSQL ${TARGET_PG_MAJOR}. No upgrade needed."
    exit 0
fi

echo "  Upgrade required: PostgreSQL ${VOLUME_PG_MAJOR} → ${TARGET_PG_MAJOR}"

# Find the most recent backup created by db_backup.sh in this run.
BACKUP_FILE=$(ls -t "$BACKUP_DIR"/pre_upgrade_*.sql 2>/dev/null | head -1 || true)
if [ -z "$BACKUP_FILE" ]; then
    echo "  ERROR: No backup found in $BACKUP_DIR." >&2
    echo "  The upgrade script requires a database backup before proceeding." >&2
    exit 1
fi

echo "  Restoring from: $BACKUP_FILE"

# Remove the old data volume — it cannot be read by the new PostgreSQL major version.
echo "  Removing old data volume ($PG_VOLUME_NAME)..."
docker volume rm "$PG_VOLUME_NAME"
echo "  Old volume removed."

# Start a fresh PostgreSQL container on the new version.
echo "  Starting PostgreSQL ${TARGET_PG_MAJOR} container..."
$DOCKER_COMPOSE_CMD up -d db

echo -n "  Waiting for PostgreSQL ${TARGET_PG_MAJOR} to be ready..."
attempt=0
until $DOCKER_COMPOSE_CMD exec -T db \
    pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge 30 ]; then
        echo ""
        echo "  ERROR: PostgreSQL ${TARGET_PG_MAJOR} did not become ready within 60s." >&2
        exit 1
    fi
    printf "."
    sleep 2
done
echo " ready."

# Restore all data from the backup.
echo "  Restoring data..."
$DOCKER_COMPOSE_CMD exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB" \
    < "$BACKUP_FILE" > /dev/null

# Quick sanity check on the restore.
SCAN_COUNT=$($DOCKER_COMPOSE_CMD exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB" \
    -t -c 'SELECT COUNT(*) FROM "startScan_scanhistory";' 2>/dev/null | \
    tr -d '[:space:]' || echo "unknown")

echo "  PostgreSQL upgraded: ${VOLUME_PG_MAJOR} → ${TARGET_PG_MAJOR}"
echo "  Verified: $SCAN_COUNT scan history record(s) restored."
