#!/bin/bash
# macOS double-clickable launcher for Paramify Vuln-Fetcher
# This file can be double-clicked to run the tool in Terminal

# Get the directory where this script is located
cd "$(dirname "$0")"

# Resize terminal window to be wider (100 columns x 30 rows)
printf '\e[8;30;100t'

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[1;36m'  # Bright cyan/blue
NC='\033[0m' # No Color

# Clear screen for clean presentation
clear

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}  PARAMIFY VULN-FETCHER${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""

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
    echo "Would you like to run the installation script now?"
    echo ""
    read -p "Run installer? (Y/n): " RUN_INSTALL

    if [[ ! $RUN_INSTALL =~ ^[Nn]$ ]]; then
        if [ -f "install.sh" ]; then
            chmod +x install.sh
            ./install.sh

            # After installation, offer to run the tool
            echo ""
            read -p "Installation complete! Run the tool now? (Y/n): " RUN_NOW
            if [[ ! $RUN_NOW =~ ^[Nn]$ ]]; then
                source venv/bin/activate
                python3 main.py
            fi
        else
            echo -e "${RED}✗ install.sh not found${NC}"
            echo ""
            echo "Please run the installation manually:"
            echo "  1. Open Terminal"
            echo "  2. Navigate to this folder"
            echo "  3. Run: ./install.sh"
            echo ""
            read -p "Press Enter to exit..."
        fi
    else
        echo ""
        echo "Please run the installation script first:"
        echo "  ./install.sh"
        echo ""
        read -p "Press Enter to exit..."
    fi
    exit 0
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if ! python3 -c "import requests, dotenv, urllib3" 2>/dev/null; then
    echo -e "${RED}✗ Missing dependencies${NC}"
    echo ""
    echo "Dependencies not properly installed."
    echo ""
    read -p "Run installer to fix this? (Y/n): " FIX_DEPS

    if [[ ! $FIX_DEPS =~ ^[Nn]$ ]]; then
        ./install.sh
    else
        echo ""
        read -p "Press Enter to exit..."
    fi
    exit 1
fi

# All checks passed - run the tool
# (API keys can be configured via menu option 6 if not set)
echo -e "${GREEN}✓ Setup verified${NC}"
echo ""
python3 main.py

# Close the Terminal window after a brief delay (macOS specific)
# The delay ensures the close command runs after this script exits
(sleep 0.5 && osascript -e 'tell application "Terminal" to close front window' 2>/dev/null) &
disown
exit 0
