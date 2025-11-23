#!/usr/bin/env bash
set -euo pipefail

# Script to run Neo4j integration tests using Docker Compose.
# - Starts the `neo4j` service
# - Waits for the Bolt port to become available
# - Runs the `pytest` service (defined in docker-compose.yml)
# - Shows Neo4j logs if tests fail and brings down the compose stack

COMPOSE_CMD="docker compose"
NEO_HOST="localhost"
NEO_BOLT=7687
TIMEOUT=60

echo "Starting Neo4j service..."
NEO_DIRS=("./neo4j/data" "./neo4j/logs")
if [ "${SKIP_NEO4J_CLEAN:-0}" != "1" ]; then
  echo "Removing existing Neo4j data/log directories to ensure clean initialization..."
  for d in "${NEO_DIRS[@]}"; do
    if [ -e "$d" ]; then
      rm -rf "$d"
    fi
  done
fi

$COMPOSE_CMD up -d neo4j

echo "Waiting up to ${TIMEOUT}s for Neo4j Bolt port ${NEO_BOLT} on ${NEO_HOST}..."
start_time=$(date +%s)
while true; do
  if command -v nc >/dev/null 2>&1; then
    if nc -z ${NEO_HOST} ${NEO_BOLT} >/dev/null 2>&1; then
      echo "Bolt port ${NEO_BOLT} is open."
      break
    fi
  else
    # Fallback: try to open a TCP connection using /dev/tcp
    if (echo > /dev/tcp/${NEO_HOST}/${NEO_BOLT}) >/dev/null 2>&1; then
      echo "Bolt port ${NEO_BOLT} is open."
      break
    fi
  fi

  now=$(date +%s)
  elapsed=$((now - start_time))
  if [ ${elapsed} -ge ${TIMEOUT} ]; then
    echo "Timed out waiting for Neo4j to become ready after ${TIMEOUT}s" >&2
    echo "Recent Neo4j logs:" >&2
    $COMPOSE_CMD logs --no-color neo4j | sed -n '1,200p' >&2 || true
    exit 1
  fi
  sleep 1
done

echo "Giving Neo4j a few seconds to finish initialization..."
sleep 3

echo "Running pytest via docker compose..."
set +e
$COMPOSE_CMD run --rm pytest
EXIT_CODE=$?
set -e

if [ ${EXIT_CODE} -eq 0 ]; then
  echo "Integration tests passed. Bringing down compose stack..."
  $COMPOSE_CMD down --remove-orphans
  exit 0
else
  echo "Integration tests failed (exit ${EXIT_CODE}). Showing neo4j logs (tail 200 lines):" >&2
  $COMPOSE_CMD logs --no-color neo4j | sed -n '1,200p' >&2 || true
  echo "Bringing down compose stack..." >&2
  $COMPOSE_CMD down --remove-orphans
  exit ${EXIT_CODE}
fi
