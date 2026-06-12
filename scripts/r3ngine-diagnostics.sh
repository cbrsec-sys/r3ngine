#!/bin/bash

# ==================================================
# r3ngine Docker Diagnostic Utility
# ==================================================

set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "=================================================="
echo "      r3ngine Container Health Diagnostics"
echo "=================================================="
echo -e "${NC}"

# Detect r3ngine containers
CONTAINERS=$(docker ps -a --format "{{.Names}}" | grep -Ei 'r3ngine|rengine|neo4j|temporal|postgres|redis|worker|frontend|backend|web' || true)

if [ -z "$CONTAINERS" ]; then
    echo -e "${RED}No r3ngine related containers detected${NC}"
    exit 1
fi

for CONTAINER in $CONTAINERS; do

    echo
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${BLUE}Container: ${CONTAINER}${NC}"
    echo -e "${BLUE}==================================================${NC}"

    STATUS=$(docker inspect --format '{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo "unknown")
    EXIT_CODE=$(docker inspect --format '{{.State.ExitCode}}' "$CONTAINER" 2>/dev/null || echo "unknown")
    RESTARTS=$(docker inspect --format '{{.RestartCount}}' "$CONTAINER" 2>/dev/null || echo "0")
    OOM=$(docker inspect --format '{{.State.OOMKilled}}' "$CONTAINER" 2>/dev/null || echo "false")

    echo "Status       : $STATUS"
    echo "Exit Code    : $EXIT_CODE"
    echo "Restarts     : $RESTARTS"
    echo "OOM Killed   : $OOM"

    if [ "$STATUS" != "running" ]; then
        echo -e "${RED}Container is not running${NC}"
    fi

    if [ "$OOM" = "true" ]; then
        echo -e "${RED}Container was OOM killed${NC}"
    fi

    if [ "$RESTARTS" -gt 5 ]; then
        echo -e "${YELLOW}High restart count detected${NC}"
    fi

    HEALTH=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$CONTAINER")

    echo "Health       : $HEALTH"

    if [ "$HEALTH" = "unhealthy" ]; then
        echo -e "${RED}Health check failing${NC}"
    fi

    echo
    echo "Recent Logs:"
    echo "-------------------------------------------"

    docker logs --tail 25 "$CONTAINER" 2>&1 | tail -25

    echo
done

echo
echo -e "${BLUE}=================================================="
echo "Docker Resource Usage"
echo -e "==================================================${NC}"

docker stats --no-stream

echo
echo -e "${BLUE}=================================================="
echo "Network Validation"
echo -e "==================================================${NC}"

docker network ls

echo
echo -e "${BLUE}=================================================="
echo "Volume Validation"
echo -e "==================================================${NC}"

docker volume ls

echo
echo -e "${BLUE}=================================================="
echo "Container Health Summary"
echo -e "==================================================${NC}"

docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

echo
echo -e "${BLUE}=================================================="
echo "Restart Loop Detection"
echo -e "==================================================${NC}"

docker ps -a --format "{{.Names}}" | while read CONTAINER
do
    RESTARTS=$(docker inspect --format '{{.RestartCount}}' "$CONTAINER" 2>/dev/null || echo 0)

    if [ "$RESTARTS" -gt 10 ]; then
        echo -e "${RED}$CONTAINER -> restart loop suspected (${RESTARTS} restarts)${NC}"
    fi
done

echo
echo -e "${BLUE}=================================================="
echo "Temporal Diagnostics"
echo -e "==================================================${NC}"

docker ps --format "{{.Names}}" | grep -i temporal >/dev/null 2>&1

if [ $? -eq 0 ]; then
    docker ps --format "{{.Names}}" | grep -i temporal | while read TEMP
    do
        echo
        echo "Temporal Container: $TEMP"

        docker logs "$TEMP" 2>&1 | tail -20 | grep -Ei \
            "error|fatal|panic|timeout|connection refused|unavailable" || true
    done
else
    echo "No Temporal containers detected"
fi

echo
echo -e "${BLUE}=================================================="
echo "Neo4j Diagnostics"
echo -e "==================================================${NC}"

docker ps --format "{{.Names}}" | grep -i neo4j >/dev/null 2>&1

if [ $? -eq 0 ]; then
    docker ps --format "{{.Names}}" | grep -i neo4j | while read NEO
    do
        echo
        echo "Neo4j Container: $NEO"

        docker logs "$NEO" 2>&1 | tail -20 | grep -Ei \
            "error|fatal|panic|exception|outofmemory" || true
    done
else
    echo "No Neo4j containers detected"
fi

echo
echo -e "${BLUE}=================================================="
echo "Postgres Diagnostics"
echo -e "==================================================${NC}"

docker ps --format "{{.Names}}" | grep -Ei "postgres|db" >/dev/null 2>&1

if [ $? -eq 0 ]; then
    docker ps --format "{{.Names}}" | grep -Ei "postgres|db" | while read DB
    do
        echo
        echo "Database Container: $DB"

        docker logs "$DB" 2>&1 | tail -20 | grep -Ei \
            "error|fatal|panic|could not connect|connection refused" || true
    done
else
    echo "No Postgres containers detected"
fi

echo
echo -e "${GREEN}"
echo "=================================================="
echo "Diagnostic Completed"
echo "=================================================="
echo -e "${NC}"
