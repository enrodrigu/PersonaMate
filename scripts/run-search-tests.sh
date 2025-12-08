#!/usr/bin/env bash
#
# PersonaMate Test Runner - Search & Embeddings Tests
# Run semantic search and embedding quality tests (requires Qdrant)
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

echo -e "${CYAN}PersonaMate - Search & Embeddings Tests${NC}"
echo -e "${CYAN}=======================================${NC}"
echo ""

# Start Qdrant (and MongoDB for some tests)
echo -e "${YELLOW}Starting Qdrant and MongoDB...${NC}"
$COMPOSE_CMD up -d qdrant mongodb

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

echo ""
echo -e "${YELLOW}Services ready. Waiting 2s for initialization...${NC}"
sleep 2

echo ""
echo -e "${GREEN}Running search & embeddings tests...${NC}"
echo ""

# Run search tests
set +e
$COMPOSE_CMD run --rm pytest pytest \
    /app/test/python/test_search_embeddings.py \
    -v -s

EXIT_CODE=$?
set -e

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Search & embeddings tests passed!${NC}"
    echo ""
    echo -e "${YELLOW}Cleaning up services...${NC}"
    $COMPOSE_CMD down --remove-orphans
    exit 0
else
    echo -e "${RED}✗ Search & embeddings tests failed!${NC}"
    echo ""
    echo -e "${YELLOW}Service logs:${NC}"
    $COMPOSE_CMD logs --tail=50 qdrant mongodb
    echo ""
    echo -e "${YELLOW}Cleaning up services...${NC}"
    $COMPOSE_CMD down --remove-orphans
    exit $EXIT_CODE
fi
