#!/bin/bash

# KubeEye Test Runner Script
# Usage: ./run_test.sh [options]
# Options:
#   --no-rebuild    Skip Docker image rebuild (use cache)
#   --back-lint     Run linting tools for backend (black, flake8, pylint)
#   --back-test     Run unit, integration tests and coverage for backend
#   --front-lint    Run linting tools for frontend (ESLint, Stylelint, Prettier)
#   --all           Run all tests and checks (default)
#   --help          Show this help

set -e

# Cleanup function for trap
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up on exit...${NC}"
    docker compose -f docker-compose.test.yaml down postgres-test || true
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Set trap for cleanup on exit
trap cleanup EXIT

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
RUN_BACK_LINT=false
RUN_BACK_TEST=false
RUN_FRONT_LINT=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --back-lint)
      RUN_BACK_LINT=true
      shift
      ;;
    --back-test)
      RUN_BACK_TEST=true
      shift
      ;;
    --front-lint)
      RUN_FRONT_LINT=true
      shift
      ;;
    --all)
      # Default: run everything
      RUN_BACK_LINT=true
      RUN_BACK_TEST=true
      RUN_FRONT_LINT=true
      shift
      ;;
    --help)
        echo "KubeEye Test Runner"
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --back-lint     Run linting tools for backend (black, flake8, pylint)"
        echo "  --back-test     Run unit, integration tests and coverage for backend"
        echo "  --front-lint    Run linting tools for frontend (ESLint, Stylelint, Prettier)"
        echo "  --all           Run all tests and checks (default)"
        echo "  --help          Show this help"
        exit 0
        ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# If no specific flags provided, default to --all
if [ "$RUN_BACK_LINT" = false ] && [ "$RUN_BACK_TEST" = false ] && [ "$RUN_FRONT_LINT" = false ]; then
  RUN_BACK_LINT=true
  RUN_BACK_TEST=true
  RUN_FRONT_LINT=true
fi

echo -e "${BLUE}🚀 Starting KubeEye Test Suite${NC}"
echo "================================="

# Clean up data directory at start
echo -e "${YELLOW}🧹 Cleaning up data directory at start...${NC}"
rm -rf backend/app/data || true
echo -e "${GREEN}✅ Data directory cleaned${NC}"
echo ""

# Clean up previous test results (removed)

# Function to run command with error handling
run_cmd() {
    local cmd="$1"
    local desc="$2"

    echo -e "${YELLOW}▶ Running: ${desc}${NC}"
    if eval "$cmd"; then
        echo -e "${GREEN}✅ ${desc} - PASSED${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}❌ ${desc} - FAILED${NC}"
        echo ""
        return 1
    fi
}

# Build backend test image if needed
if [ "$RUN_BACK_LINT" = true ] || [ "$RUN_BACK_TEST" = true ]; then
    echo -e "${YELLOW}🔨 Building backend test image...${NC}"
    BUILD_CMD="docker compose -f docker-compose.test.yaml build test-runner"

    if ! $BUILD_CMD; then
        echo -e "${RED}❌ Failed to build backend test image${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Backend test image built successfully${NC}"
    echo ""
fi

FAILED_TESTS=0

# Phase 1: Backend Code Quality (Formatting and Linting)
if [ "$RUN_BACK_LINT" = true ]; then
    echo -e "${BLUE}🔍 Phase 1: Code Quality Checks${NC}"
    echo "=================================="

    # Auto-format code with Black
    echo -e "${YELLOW}🔧 Auto-formatting code with Black...${NC}"
    if docker compose -f docker-compose.test.yaml run --rm test-runner sh -c "cd /app && python -m black --line-length=120 ."; then
        echo -e "${GREEN}✅ Code formatted successfully${NC}"
    else
        echo -e "${RED}❌ Code formatting failed${NC}"
        ((FAILED_TESTS++))
    fi
    echo ""

    # Flake8 linting (uses .flake8 config for line length and ignores)
    if ! run_cmd "docker compose -f docker-compose.test.yaml run --rm test-runner sh -c \"cd /app && python -m flake8 .\"" "Flake8 linting"; then
        ((FAILED_TESTS++))
        echo -e "${RED}❌ Flake8 linting failed. Fix linting issues before proceeding.${NC}"
        exit 1
    fi

    # Pylint static analysis (focus on import errors and basic issues)
    if ! run_cmd "docker compose -f docker-compose.test.yaml run --rm test-runner sh -c \"cd /app && python -m pylint --disable=all --enable=import-error,unused-import,no-name-in-module .\"" "Pylint import checks"; then
        ((FAILED_TESTS++))
        echo -e "${RED}❌ Pylint import checks failed. Fix import issues before proceeding.${NC}"
        exit 1
    fi

fi

# Build frontend lint image if needed
if [ "$RUN_FRONT_LINT" = true ]; then
    echo -e "${YELLOW}🔨 Building frontend lint image...${NC}"
    BUILD_FRONT_CMD="docker compose -f docker-compose.test.yaml build frontend-lint"

    if ! $BUILD_FRONT_CMD; then
        echo -e "${RED}❌ Failed to build frontend lint image${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Frontend lint image built successfully${NC}"
    echo ""

    echo -e "${BLUE}🔍 Phase 2: Frontend Linting${NC}"
    echo "=================================="

    # Prettier formatting
    if ! run_cmd "docker compose -f docker-compose.test.yaml run --rm frontend-lint sh -c \"npm run format\"" "Prettier formatting"; then
        ((FAILED_TESTS++))
        echo -e "${RED}❌ Prettier for Frontend failed. Fix formatting issues before proceeding.${NC}"
        exit 1
    fi

    # ESLint linting for JavaScript/TypeScript
    if ! run_cmd "docker compose -f docker-compose.test.yaml run --rm frontend-lint sh -c \"npm run lint:js\"" "ESLint linting"; then
        ((FAILED_TESTS++))
        echo -e "${RED}❌ ESLint for Frontend failed. Fix linting issues before proceeding.${NC}"
        exit 1
    fi

    # Stylelint linting for CSS
    if ! run_cmd "docker compose -f docker-compose.test.yaml run --rm frontend-lint sh -c \"npm run lint:css\"" "Stylelint linting"; then
        ((FAILED_TESTS++))
        echo -e "${RED}❌ Stylelint for Frontend failed. Fix linting issues before proceeding.${NC}"
        exit 1
    fi

fi


# Phase 3: Backend Tests
if [ "$RUN_BACK_TEST" = true ]; then
    echo -e "${BLUE}🧪 Phase 3: Running Backend Tests${NC}"
    echo "================="

    # Test path for all tests
    TEST_PATH="/app/tests/"

    # Coverage options (always enabled for --back-test)
    COVERAGE_OPTS="--cov=. --cov-report=term-missing"

    # Start PostgreSQL test database
    echo -e "${YELLOW}🗄️ Starting PostgreSQL test database...${NC}"
    if docker compose -f docker-compose.test.yaml up -d postgres-test; then
        echo -e "${GREEN}✅ PostgreSQL test database started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start PostgreSQL test database${NC}"
        exit 1
    fi
    echo ""

    # Run tests
    TEST_CMD="docker compose -f docker-compose.test.yaml run --rm test-runner sh -c \"cd /app && pytest $TEST_PATH -v --tb=short --timeout=300 $COVERAGE_OPTS\""
    if ! run_cmd "$TEST_CMD" "Test execution"; then
        ((FAILED_TESTS++))
        echo -e "${RED}❌ Tests failed. Check test output above for details.${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Phase 3 completed successfully${NC}"
    echo ""
fi

# Summary
echo "================================="
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests and checks passed!${NC}"
    echo ""

    # Stop PostgreSQL test database
    echo -e "${YELLOW}🗄️ Stopping PostgreSQL test database...${NC}"
    docker compose -f docker-compose.test.yaml down postgres-test || true
    echo -e "${GREEN}✅ PostgreSQL test database stopped${NC}"
    echo ""

    # Clean up data directory
    echo -e "${YELLOW}🧹 Cleaning up data directory...${NC}"
    rm -rf backend/app/data || true
    echo -e "${GREEN}✅ Data directory cleaned${NC}"
    echo ""

    echo -e "${BLUE}📊 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}💥 $FAILED_TESTS test/check groups failed!${NC}"
    echo ""

    # Stop PostgreSQL test database on failure
    echo -e "${YELLOW}🗄️ Stopping PostgreSQL test database...${NC}"
    docker compose -f docker-compose.test.yaml down postgres-test || true
    echo -e "${GREEN}✅ PostgreSQL test database stopped${NC}"
    echo ""

    echo -e "${YELLOW}� Troubleshooting:${NC}"

    exit 1
fi
