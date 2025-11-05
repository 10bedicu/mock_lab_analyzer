#!/usr/bin/env bash

# Integration test script

echo "🧪 Running Integration Tests"
echo "============================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Check if required files exist
echo "Test 1: Checking file structure..."
required_files=(run.py shared/state.py config/settings.py lab_analyzer/analyzer.py web/app.py web/routes.py)

all_exist=true
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file exists"
    else
        echo "  ✗ $file missing"
        all_exist=false
    fi
done

if [ "$all_exist" = "true" ]; then
    echo -e "${GREEN}✓ All required files exist${NC}"
else
    echo -e "${RED}✗ Some files are missing${NC}"
    exit 1
fi

echo ""

# Test 2: Check if dependencies are installed
echo "Test 2: Checking dependencies..."
if pipenv run python -c "import flask; import hl7; print('✓ All dependencies installed')" 2>/dev/null; then
    echo -e "${GREEN}✓ Dependencies OK${NC}"
else
    echo -e "${RED}✗ Missing dependencies. Run: pipenv install${NC}"
    exit 1
fi

echo ""

# Test 3: Syntax check
echo "Test 3: Checking Python syntax..."
py_files=(run.py shared/state.py config/settings.py lab_analyzer/analyzer.py web/app.py web/routes.py)

syntax_ok=true
for file in "${py_files[@]}"; do
    if pipenv run python -m py_compile "$file" 2>/dev/null; then
        echo "  ✓ $file syntax OK"
    else
        echo "  ✗ $file has syntax errors"
        syntax_ok=false
    fi
done

if [ "$syntax_ok" = "true" ]; then
    echo -e "${GREEN}✓ All files have valid syntax${NC}"
else
    echo -e "${RED}✗ Some files have syntax errors${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=============================
All tests passed! ✓
=============================${NC}"
echo ""
echo "To start the system:"
echo "  1. Terminal 1: python test_server.py"
echo "  2. Terminal 2: python run.py"
echo "  3. Terminal 3: python test_client.py"
echo ""
echo "Or use the quick start script:"
echo "  ./start.sh"
