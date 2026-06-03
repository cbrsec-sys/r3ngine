#!/bin/bash
# Safe PostgreSQL backup before upgrades.
# Called by 'make fullupgrade'. Requires the db container to be running.
# Environment variables (passed by Makefile):
#   POSTGRES_USER      - database user
#   POSTGRES_DB        - database name
#   DOCKER_COMPOSE_CMD - full docker compose command with file flags

set -euo pipefail

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${DOCKER_COMPOSE_CMD:?DOCKER_COMPOSE_CMD is required}"

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DUMP_FILE="$BACKUP_DIR/pre_upgrade_$(date +%Y%m%d_%H%M%S).sql"
ERROR_LOG="$BACKUP_DIR/.pg_dump_err.tmp"

mkdir -p "$BACKUP_DIR"
echo "  Backing up '$POSTGRES_DB' to $DUMP_FILE ..."

# Redirect stdout to the dump file; stderr to a separate log so it never
# contaminates the backup content (avoids false-pass on the size check below).
$DOCKER_COMPOSE_CMD exec -T db \
    pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
    > "$DUMP_FILE" \
    2> "$ERROR_LOG"
PG_EXIT=$?

if [ $PG_EXIT -ne 0 ]; then
    echo "  ERROR: pg_dump failed (exit: $PG_EXIT)." >&2
    echo "  pg_dump error output:" >&2
    cat "$ERROR_LOG" >&2
    rm -f "$DUMP_FILE" "$ERROR_LOG"
    exit 1
fi

if [ ! -s "$DUMP_FILE" ]; then
    echo "  ERROR: pg_dump produced an empty file. Check connection and database name." >&2
    cat "$ERROR_LOG" >&2
    rm -f "$DUMP_FILE" "$ERROR_LOG"
    exit 1
fi

rm -f "$ERROR_LOG"

DUMP_SIZE=$(du -sh "$DUMP_FILE" | cut -f1)
echo "  Backup saved: $DUMP_FILE ($DUMP_SIZE)"
echo "  To restore: $DOCKER_COMPOSE_CMD exec -T db psql -U $POSTGRES_USER $POSTGRES_DB < $DUMP_FILE"
