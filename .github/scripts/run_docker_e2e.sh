#!/bin/bash
# SPDX-License-Identifier: PROPRIETARY
# Run Docker E2E test suite

set -euo pipefail

echo "=== Docker E2E Test Suite ==="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up Docker resources...${NC}"
    docker-compose -f docker-compose.test.yml down -v 2>/dev/null || true
}

trap cleanup EXIT

# Build test images
echo -e "${YELLOW}Building test images...${NC}"
docker-compose -f docker-compose.test.yml build --no-cache

# Start services
echo -e "${YELLOW}Starting test services...${NC}"
docker-compose -f docker-compose.test.yml up -d backend-test frontend-test

# Wait for backend to be healthy
echo -e "${YELLOW}Waiting for backend to be healthy...${NC}"
timeout=120
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose -f docker-compose.test.yml exec -T backend-test curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}Backend is healthy${NC}"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

if [ $elapsed -ge $timeout ]; then
    echo -e "${RED}ERROR: Backend failed to become healthy${NC}"
    docker-compose -f docker-compose.test.yml logs backend-test
    exit 1
fi

# Run API tests
echo -e "${YELLOW}Running API tests...${NC}"
if docker-compose -f docker-compose.test.yml run --rm api-tests; then
    echo -e "${GREEN}API tests passed${NC}"
else
    echo -e "${RED}API tests failed${NC}"
    exit 1
fi

# Run connector tests
echo -e "${YELLOW}Running connector tests...${NC}"
if docker-compose -f docker-compose.test.yml run --rm connector-tests; then
    echo -e "${GREEN}Connector tests passed${NC}"
else
    echo -e "${RED}Connector tests failed${NC}"
    exit 1
fi

# Run integration tests
echo -e "${YELLOW}Running integration tests...${NC}"
if docker-compose -f docker-compose.test.yml run --rm integration-tests; then
    echo -e "${GREEN}Integration tests passed${NC}"
else
    echo -e "${RED}Integration tests failed${NC}"
    exit 1
fi

echo -e "\n${GREEN}=== All Docker E2E tests passed ===${NC}"
