#!/usr/bin/env bash
#
# PersonaMate Test Runner - RAG Architecture Tests
# Run complete integration tests across Neo4j, MongoDB, and Qdrant
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

COMPOSE_CMD="docker compose"
TIMEOUT=60

echo -e "${CYAN}PersonaMate - RAG Architecture Tests${NC}"
echo -e "${CYAN}====================================${NC}"
echo ""

# Start all required services
echo -e "${YELLOW}Starting Neo4j, MongoDB, and Qdrant...${NC}"
$COMPOSE_CMD up -d neo4j mongodb qdrant

# Wait for Neo4j
echo -e "${YELLOW}Waiting for Neo4j Bolt port 7687...${NC}"
start_time=$(date +%s)
while true; do
    if nc -z localhost 7687 >/dev/null 2>&1 || (echo > /dev/tcp/localhost/7687) >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Neo4j ready${NC}"
        break
    fi
    now=$(date +%s)
    elapsed=$((now - start_time))
    if [ ${elapsed} -ge ${TIMEOUT} ]; then
        echo -e "${RED}✗ Timed out waiting for Neo4j${NC}" >&2
        $COMPOSE_CMD logs neo4j
        exit 1
    fi
    sleep 1
done

# Wait for MongoDB
echo -e "${YELLOW}Waiting for MongoDB port 27017...${NC}"
start_time=$(date +%s)
while true; do
    if nc -z localhost 27017 >/dev/null 2>&1 || (echo > /dev/tcp/localhost/27017) >/dev/null 2>&1; then
        echo -e "${GREEN}✓ MongoDB ready${NC}"
        break
    fi
    now=$(date +%s)
    elapsed=$((now - start_time))
    if [ ${elapsed} -ge ${TIMEOUT} ]; then
        echo -e "${RED}✗ Timed out waiting for MongoDB${NC}" >&2
        exit 1
    fi
    sleep 1
done

# Wait for Qdrant
echo -e "${YELLOW}Waiting for Qdrant port 6333...${NC}"
start_time=$(date +%s)
while true; do
    if nc -z localhost 6333 >/dev/null 2>&1 || (echo > /dev/tcp/localhost/6333) >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Qdrant ready${NC}"
        break
    fi
    now=$(date +%s)
    elapsed=$((now - start_time))
    if [ ${elapsed} -ge ${TIMEOUT} ]; then
        echo -e "${RED}✗ Timed out waiting for Qdrant${NC}" >&2
        exit 1
    fi
    sleep 1
done

echo ""
echo -e "${YELLOW}All services ready. Waiting 3s for full initialization...${NC}"
sleep 3

echo ""
echo -e "${GREEN}Running RAG architecture integration tests...${NC}"
echo ""

# Run RAG tests
set +e
$COMPOSE_CMD run --rm pytest pytest \
    /app/test/python/test_rag_architecture.py \
    -v -s

EXIT_CODE=$?
set -e

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ RAG architecture tests passed!${NC}"
    echo ""
    echo -e "${YELLOW}Cleaning up services...${NC}"
    $COMPOSE_CMD down --remove-orphans
    exit 0
else
    echo -e "${RED}✗ RAG architecture tests failed!${NC}"
    echo ""
    echo -e "${YELLOW}Service logs:${NC}"
    $COMPOSE_CMD logs --tail=50 neo4j mongodb qdrant
    echo ""
    echo -e "${YELLOW}Cleaning up services...${NC}"
    $COMPOSE_CMD down --remove-orphans
    exit $EXIT_CODE
fi
