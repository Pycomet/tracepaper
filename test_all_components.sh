#!/bin/bash

echo "🧪 TRACEPAPER COMPREHENSIVE TESTING SUITE"
echo "=========================================="
echo ""

# Set colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2 PASSED${NC}"
    else
        echo -e "${RED}❌ $2 FAILED${NC}"
    fi
}

# Store current directory
ORIGINAL_DIR=$(pwd)
TESTS_PASSED=0
TESTS_FAILED=0

echo -e "${BLUE}🧬 PHASE 1: BACKEND API TESTS${NC}"
echo "================================"
cd backend

echo "Installing backend dependencies..."
pip install -r requirements.txt

echo "Running backend API tests..."
python -m pytest tests/ -v --tb=short
BACKEND_RESULT=$?
print_status $BACKEND_RESULT "Backend API Tests"
if [ $BACKEND_RESULT -eq 0 ]; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

echo ""
echo -e "${BLUE}🗂️  PHASE 2: FILE WATCHER TESTS${NC}"
echo "=================================="
cd ../file_watcher

echo "Installing file watcher dependencies..."
pip install -r requirements.txt

echo "Running file watcher tests..."
python -m pytest test_watcher.py -v --tb=short
WATCHER_RESULT=$?
print_status $WATCHER_RESULT "File Watcher Tests"
if [ $WATCHER_RESULT -eq 0 ]; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

echo ""
echo -e "${BLUE}🖥️  PHASE 3: DESKTOP APP TESTS${NC}"
echo "==============================="
cd ../desktop

echo "Installing desktop app dependencies..."
npm install

echo "Running desktop React app tests..."
npm test -- --watchAll=false --passWithNoTests
DESKTOP_RESULT=$?
print_status $DESKTOP_RESULT "Desktop App Tests"
if [ $DESKTOP_RESULT -eq 0 ]; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

echo ""
echo -e "${BLUE}🔧 PHASE 4: BROWSER EXTENSION TESTS${NC}"
echo "===================================="
cd ../browser_extension

echo "Installing extension dependencies..."
npm install

echo "Running browser extension tests..."
npm test
EXTENSION_RESULT=$?
print_status $EXTENSION_RESULT "Browser Extension Tests"
if [ $EXTENSION_RESULT -eq 0 ]; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

echo ""
echo -e "${BLUE}📊 TESTING SUMMARY${NC}"
echo "=================="
echo -e "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! The project is working correctly.${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some tests failed. Check the output above for details.${NC}"
    exit 1
fi 