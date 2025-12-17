#!/bin/bash

# KubeEye Test Runner Script
# Usage: ./run_test.sh [options]
# Options:
#   --no-rebuild    Skip Docker image rebuild (use cache)
#   --unit          Run only unit tests
#   --integration   Run only integration tests
#   --coverage      Generate coverage report
#   --lint          Run linting tools (black, flake8, pylint)
#   --all           Run all tests and checks (default)
#   --help          Show this help

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
REBUILD=false
RUN_UNIT=true
RUN_INTEGRATION=true
RUN_COVERAGE=true
RUN_LINT=true

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --no-rebuild)
      REBUILD=false
      shift
      ;;
    --unit)
      RUN_UNIT=true
      RUN_INTEGRATION=false
      RUN_LINT=false
      shift
      ;;
    --integration)
      RUN_UNIT=false
      RUN_INTEGRATION=true
      RUN_LINT=false
      shift
      ;;
    --coverage)
      RUN_COVERAGE=true
      shift
      ;;
    --lint)
      RUN_LINT=true
      RUN_UNIT=false
      RUN_INTEGRATION=false
      shift
      ;;
    --all)
      # Default: run everything
      shift
      ;;
    --help)
      echo "KubeEye Test Runner"
      echo "Usage: $0 [options]"
      echo ""
      echo "Options:"
      echo "  --no-rebuild    Skip Docker image rebuild (use cache)"
      echo "  --unit          Run only unit tests"
      echo "  --integration   Run only integration tests"
      echo "  --coverage      Generate coverage report"
      echo "  --lint          Run linting tools (black, flake8, pylint)"
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

echo -e "${BLUE}🚀 Starting KubeEye Test Suite${NC}"
echo "================================="

# Clean up data directory at start
echo -e "${YELLOW}🧹 Cleaning up data directory at start...${NC}"
rm -rf backend/app/data
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

# Build test image if needed
if [ "$REBUILD" = true ]; then
    echo -e "${YELLOW}🔨 Rebuilding test image from scratch (--no-rebuild to skip)...${NC}"
    BUILD_CMD="docker compose -f docker-compose.test.yaml build --no-cache test-runner"
else
    echo -e "${YELLOW}🔨 Building test image (using cache)...${NC}"
    BUILD_CMD="docker compose -f docker-compose.test.yaml build test-runner"
fi

if ! $BUILD_CMD; then
    echo -e "${RED}❌ Failed to build test image${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Test image built successfully${NC}"
echo ""

FAILED_TESTS=0

# Phase 1: Code Quality (Formatting and Linting)
if [ "$RUN_LINT" = true ]; then
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


# Phase 3: Tests
if [ "$RUN_UNIT" = true ] || [ "$RUN_INTEGRATION" = true ]; then
    echo -e "${BLUE}🧪 Phase 3: Running Tests${NC}"
    echo "================="

    # Determine test path
    TEST_PATH="/app/tests/"
    if [ "$RUN_UNIT" = true ] && [ "$RUN_INTEGRATION" = false ]; then
        TEST_PATH="/app/tests/unit/"
    elif [ "$RUN_INTEGRATION" = true ] && [ "$RUN_UNIT" = false ]; then
        TEST_PATH="/app/tests/integration/"
    fi

    # Coverage options
    COVERAGE_OPTS=""
    if [ "$RUN_COVERAGE" = true ]; then
        COVERAGE_OPTS="--cov=. --cov-report=term-missing"
    fi

    # Run tests
    TEST_CMD="docker compose -f docker-compose.test.yaml run --rm test-runner sh -c \"cd /app && pytest $TEST_PATH -v --tb=short $COVERAGE_OPTS\""
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

    # Clean up data directory
    echo -e "${YELLOW}🧹 Cleaning up data directory...${NC}"
    rm -rf backend/app/data
    echo -e "${GREEN}✅ Data directory cleaned${NC}"
    echo ""

    echo -e "${BLUE}📊 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}💥 $FAILED_TESTS test/check groups failed!${NC}"
    echo ""
    echo -e "${YELLOW}🔧 Troubleshooting:${NC}"

    exit 1
fi
