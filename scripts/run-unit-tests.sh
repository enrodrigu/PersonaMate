#!/usr/bin/env bash
#
# PersonaMate Test Runner - Unit Tests
# Run fast unit tests (no external services required)
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}PersonaMate - Unit Tests${NC}"
echo -e "${CYAN}========================${NC}"
echo ""

# Unit tests don't need external services, but we build the image if needed
echo -e "${YELLOW}Building test image...${NC}"
docker compose build pytest

echo ""
echo -e "${GREEN}Running unit tests (fast, no services needed)...${NC}"
echo ""

# Run unit tests
docker compose run --rm pytest pytest \
    /app/test/python/test_embedding_pipeline.py \
    /app/test/python/test_tools.py \
    -v

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Unit tests passed!${NC}"
else
    echo -e "${RED}✗ Unit tests failed!${NC}"
fi

echo ""
exit $EXIT_CODE
