#!/usr/bin/env bash
#
# PersonaMate Test Runner - All Tests with Coverage
# Run complete test suite and generate coverage report
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

echo -e "${CYAN}PersonaMate - Complete Test Suite${NC}"
echo -e "${CYAN}=================================${NC}"
echo ""

# Start all services
echo -e "${YELLOW}Starting all services (Neo4j, MongoDB, Qdrant)...${NC}"
$COMPOSE_CMD up -d neo4j mongodb qdrant

# Wait for all services
echo -e "${YELLOW}Waiting for services to be ready...${NC}"

# Neo4j
start_time=$(date +%s)
while true; do
    if nc -z localhost 7687 >/dev/null 2>&1 || (echo > /dev/tcp/localhost/7687) >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Neo4j ready${NC}"
        break
    fi
    now=$(date +%s)
    if [ $((now - start_time)) -ge ${TIMEOUT} ]; then
        echo -e "${RED}✗ Neo4j timeout${NC}" >&2
        exit 1
    fi
    sleep 1
done

# MongoDB
start_time=$(date +%s)
while true; do
    if nc -z localhost 27017 >/dev/null 2>&1 || (echo > /dev/tcp/localhost/27017) >/dev/null 2>&1; then
        echo -e "${GREEN}✓ MongoDB ready${NC}"
        break
    fi
    now=$(date +%s)
    if [ $((now - start_time)) -ge ${TIMEOUT} ]; then
        echo -e "${RED}✗ MongoDB timeout${NC}" >&2
        exit 1
    fi
    sleep 1
done

# Qdrant
start_time=$(date +%s)
while true; do
    if nc -z localhost 6333 >/dev/null 2>&1 || (echo > /dev/tcp/localhost/6333) >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Qdrant ready${NC}"
        break
    fi
    now=$(date +%s)
    if [ $((now - start_time)) -ge ${TIMEOUT} ]; then
        echo -e "${RED}✗ Qdrant timeout${NC}" >&2
        exit 1
    fi
    sleep 1
done

echo ""
echo -e "${YELLOW}All services ready. Waiting 3s for full initialization...${NC}"
sleep 3

echo ""
echo -e "${GREEN}Running complete test suite with coverage...${NC}"
echo ""

# Run all tests with coverage
set +e
$COMPOSE_CMD run --rm pytest pytest \
    /app/test/python/ \
    -v \
    --cov=src/python \
    --cov-report=xml \
    --cov-report=term

EXIT_CODE=$?
set -e

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo -e "${CYAN}Coverage report generated: coverage.xml (for codecov.io)${NC}"
    echo ""
    echo -e "${YELLOW}Cleaning up services...${NC}"
    $COMPOSE_CMD down --remove-orphans
    exit 0
else
    echo -e "${RED}✗ Some tests failed!${NC}"
    echo ""
    echo -e "${YELLOW}Service logs:${NC}"
    $COMPOSE_CMD logs --tail=50 neo4j mongodb qdrant
    echo ""
    echo -e "${YELLOW}Cleaning up services...${NC}"
    $COMPOSE_CMD down --remove-orphans
    exit $EXIT_CODE
fi
