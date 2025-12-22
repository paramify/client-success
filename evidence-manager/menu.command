#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
    # Check if dependencies are installed
    if ! python3 -c "import requests" 2>/dev/null; then
        echo "Installing dependencies..."
        pip install -r requirements.txt
    fi
fi

# Check if .env file exists, create if not
if [ ! -f ".env" ]; then
    echo "PARAMIFY_API_URL=https://app.paramify.com/api/v0" > .env
    echo "PARAMIFY_API_KEY=" >> .env
fi

# Check if API key is set
API_KEY=$(grep "^PARAMIFY_API_KEY=" .env | cut -d'=' -f2)

if [ -z "$API_KEY" ] || [ "$API_KEY" = "your_api_key_here" ]; then
    echo ""
    echo "========================================="
    echo "  Paramify Evidence Manager Setup"
    echo "========================================="
    echo ""
    echo "Please enter your Paramify API key:"
    read -r USER_API_KEY

    if [ -z "$USER_API_KEY" ]; then
        echo ""
        echo "No API key provided. Exiting."
        exit 1
    fi

    # Update the .env file with the new API key
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|^PARAMIFY_API_KEY=.*|PARAMIFY_API_KEY=$USER_API_KEY|" .env
    else
        # Linux
        sed -i "s|^PARAMIFY_API_KEY=.*|PARAMIFY_API_KEY=$USER_API_KEY|" .env
    fi

    echo ""
    echo "API key saved successfully!"
    echo ""
fi

# Run the menu
python3 menu.py
