#!/bin/bash
# Installation script for Paramify Vuln-Fetcher
# This script automates the setup process

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print with color
print_header() {
    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}======================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Welcome message
clear
print_header "PARAMIFY VULN-FETCHER INSTALLER"

echo "This script will set up the Paramify Vuln-Fetcher tool on your system."
echo "It will:"
echo "  1. Check for Python 3"
echo "  2. Create a virtual environment"
echo "  3. Install dependencies"
echo "  4. Configure your API credentials"
echo "  5. Test your connections"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Step 1: Check for Python 3
print_header "STEP 1: Checking Python Installation"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Found $PYTHON_VERSION"
else
    print_error "Python 3 is not installed"
    echo ""
    echo "Please install Python 3.7 or higher:"
    echo "  macOS:   brew install python3"
    echo "  Ubuntu:  sudo apt-get install python3 python3-venv"
    echo "  Windows: Download from https://www.python.org/downloads/"
    exit 1
fi

# Step 2: Create virtual environment
print_header "STEP 2: Creating Virtual Environment"

if [ -d "venv" ]; then
    print_warning "Virtual environment already exists"
    read -p "Do you want to recreate it? (y/N): " RECREATE
    if [[ $RECREATE =~ ^[Yy]$ ]]; then
        print_info "Removing existing virtual environment..."
        rm -rf venv
        print_info "Creating new virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_info "Using existing virtual environment"
    fi
else
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Step 3: Install dependencies
print_header "STEP 3: Installing Dependencies"

print_info "Activating virtual environment..."
source venv/bin/activate

print_info "Installing required packages..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

print_success "Dependencies installed"
echo ""
pip list | grep -E "(requests|urllib3|python-dotenv)"

# Step 4: Configure credentials
print_header "STEP 4: Configuring API Credentials"

if [ -f ".env" ]; then
    print_warning ".env file already exists"
    read -p "Do you want to reconfigure it? (y/N): " RECONFIG
    if [[ ! $RECONFIG =~ ^[Yy]$ ]]; then
        print_info "Keeping existing .env file"
        SKIP_CONFIG=true
    fi
fi

if [ "$SKIP_CONFIG" != "true" ]; then
    print_info "Creating .env file from template..."
    cp .env.example .env

    echo ""
    echo "Please enter your API credentials."
    echo ""
    echo -e "${YELLOW}Note: Only Paramify API Key is required.${NC}"
    echo "Nessus credentials are optional (only needed for Nessus import)."
    echo "GitHub token is optional (only needed for private repos)."
    echo ""

    # Paramify credentials (REQUIRED)
    echo -e "${BLUE}--- Paramify Configuration (REQUIRED) ---${NC}"
    while [ -z "$PARAMIFY_KEY" ]; do
        read -p "Paramify API Key: " PARAMIFY_KEY
        if [ -z "$PARAMIFY_KEY" ]; then
            print_warning "Paramify API Key is required!"
        fi
    done
    read -p "Paramify Base URL [https://demo.paramify.com/api/v0]: " PARAMIFY_URL
    PARAMIFY_URL=${PARAMIFY_URL:-https://demo.paramify.com/api/v0}

    echo ""
    echo -e "${BLUE}--- Nessus Configuration (Optional - for Nessus import) ---${NC}"
    read -p "Nessus URL [https://localhost:8834, press Enter to skip]: " NESSUS_URL
    NESSUS_URL=${NESSUS_URL:-https://localhost:8834}
    read -p "Nessus Access Key (press Enter to skip): " NESSUS_ACCESS
    read -p "Nessus Secret Key (press Enter to skip): " NESSUS_SECRET

    echo ""
    echo -e "${BLUE}--- GitHub Configuration (Optional - for private repos) ---${NC}"
    read -p "GitHub Token (press Enter to skip): " GITHUB_TOKEN

    # Write to .env file
    cat > .env << EOF
# Paramify Configuration
PARAMIFY_API_KEY=$PARAMIFY_KEY
PARAMIFY_BASE_URL=$PARAMIFY_URL

# Nessus Configuration
NESSUS_URL=$NESSUS_URL
NESSUS_ACCESS_KEY=$NESSUS_ACCESS
NESSUS_SECRET_KEY=$NESSUS_SECRET

# GitHub Configuration (Optional)
GITHUB_TOKEN=$GITHUB_TOKEN
EOF

    print_success ".env file created"
fi

# Step 5: Test connections
print_header "STEP 5: Testing Connections"

echo "Would you like to test your API connections now?"
read -p "This will verify your credentials are working (Y/n): " TEST_CONN

if [[ ! $TEST_CONN =~ ^[Nn]$ ]]; then
    print_info "Testing Nessus connection..."
    if python3 main.py list-scans > /dev/null 2>&1; then
        print_success "Nessus connection working"
    else
        print_warning "Nessus connection failed (check your credentials in .env)"
    fi

    echo ""
    print_info "Testing Paramify connection..."
    if python3 main.py list-assessments > /dev/null 2>&1; then
        print_success "Paramify connection working"
    else
        print_warning "Paramify connection failed (check your credentials in .env)"
    fi
else
    print_info "Skipping connection tests"
fi

# Make run scripts executable
chmod +x run.sh 2>/dev/null
chmod +x run.command 2>/dev/null

# Success message
print_header "INSTALLATION COMPLETE!"

echo "Setup is complete! You can now run the tool:"
echo ""
echo -e "  ${GREEN}Option 1: Double-click run.command (easiest!)${NC}"
echo -e "  ${GREEN}Option 2: Run ./run.sh from Terminal${NC}"
echo ""
echo "Other useful commands:"
echo "  ./run.sh import              - Import from Nessus"
echo "  ./run.sh import-github       - Import from GitHub"
echo "  ./run.sh list-scans          - List Nessus scans"
echo "  ./run.sh list-assessments    - List Paramify assessments"
echo "  ./run.sh --help              - Show all options"
echo ""
echo "Documentation:"
echo "  README.md  - User guide and troubleshooting"
echo "  CLAUDE.md  - Developer documentation"
echo ""
print_success "Happy scanning!"
echo ""
