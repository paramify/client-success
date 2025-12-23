#!/bin/bash
# Wrapper script to run the Paramify Vuln-Fetcher

# Get the directory where this script is located
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Check if setup is needed (venv required, .env will be created if missing)
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠ Setup required!${NC}"
    echo ""
    echo "Virtual environment not found."
    echo ""
    echo "Please run the installation script first:"
    echo ""
    echo -e "  ${YELLOW}./install.sh${NC}"
    echo ""
    exit 1
fi

# Create .env file if it doesn't exist (can be configured via menu option 6)
if [ ! -f ".env" ]; then
    touch .env
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if ! python3 -c "import requests, dotenv, urllib3" 2>/dev/null; then
    echo -e "${RED}✗ Missing dependencies${NC}"
    echo ""
    echo "Dependencies not properly installed. Please run:"
    echo ""
    echo -e "  ${YELLOW}./install.sh${NC}"
    echo ""
    echo "Or manually install dependencies:"
    echo ""
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo ""
    exit 1
fi

# All checks passed - run the tool
# (API keys can be configured via menu option 6 if not set)
echo -e "${GREEN}✓ Setup verified${NC}"
echo ""
if [ $# -eq 0 ]; then
    python3 main.py
else
    python3 main.py "$@"
fi
