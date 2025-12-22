#!/bin/bash
# Wrapper script to run the Paramify Vuln-Fetcher

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if setup is needed
if [ ! -d "venv" ] || [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ Setup required!${NC}"
    echo ""

    if [ ! -d "venv" ]; then
        echo "Virtual environment not found."
    fi

    if [ ! -f ".env" ]; then
        echo "Configuration file (.env) not found."
    fi

    echo ""
    echo "Please run the installation script first:"
    echo ""
    echo -e "  ${YELLOW}./install.sh${NC}"
    echo ""
    exit 1
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

# Check if .env has required values (only Paramify API key is required)
if ! grep -q "PARAMIFY_API_KEY=." .env 2>/dev/null; then
    echo -e "${YELLOW}⚠ Configuration incomplete${NC}"
    echo ""
    echo "Your .env file is missing the required Paramify API key."
    echo "Please run the installation script to configure:"
    echo ""
    echo -e "  ${YELLOW}./install.sh${NC}"
    echo ""
    echo "Or manually edit the .env file and add your PARAMIFY_API_KEY."
    echo ""
    exit 1
fi

# All checks passed - run the tool
if [ $# -eq 0 ]; then
    python3 main.py
else
    python3 main.py "$@"
fi
