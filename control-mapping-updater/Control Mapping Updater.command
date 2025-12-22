#!/bin/bash
# Control Mapping Updater - Menu Interface
# Double-click this file to launch the menu

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

show_header() {
    clear
    echo -e "${CYAN}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}${BOLD}       Control Mapping Updater                 ${NC}${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════╝${NC}"
    echo ""
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is not installed.${NC}"
        read -p "Press Enter to exit..."
        exit 1
    fi
}

check_master_file() {
    if [ ! -f "$SCRIPT_DIR/Master Solution Capabilities.csv" ]; then
        echo -e "${RED}Error: Master Solution Capabilities.csv not found.${NC}"
        return 1
    fi
    return 0
}

show_status() {
    if [ -f "$SCRIPT_DIR/Master Solution Capabilities.csv" ]; then
        local unique=$(python3 -c "
import csv
with open('$SCRIPT_DIR/Master Solution Capabilities.csv') as f:
    r = csv.reader(f)
    h = next(r)
    idx = h.index('Solution Capability')
    print(len(set(row[idx].strip() for row in r if len(row) > idx)))
" 2>/dev/null)
        echo -e "${GREEN}✓${NC} Master file: ${BOLD}$unique${NC} capabilities"
    else
        echo -e "${RED}✗${NC} Master file not found"
    fi

    if [ -d "$SCRIPT_DIR/backups" ]; then
        local count=$(ls -1 "$SCRIPT_DIR/backups"/*.csv 2>/dev/null | wc -l | tr -d ' ')
        if [ "$count" -gt 0 ]; then
            echo -e "  Backups: ${BOLD}$count${NC} file(s)"
        fi
    fi
    echo ""
}

run_update() {
    show_header
    check_master_file || { read -p "Press Enter to return..."; return; }
    python3 "$SCRIPT_DIR/update_control_mapping.py"
    echo ""
    read -p "Press Enter to return to menu..."
}

run_dry_run() {
    show_header
    check_master_file || { read -p "Press Enter to return..."; return; }
    python3 "$SCRIPT_DIR/update_control_mapping.py" --dry-run
    echo ""
    read -p "Press Enter to return to menu..."
}

view_backups() {
    show_header
    echo -e "${BOLD}Backups${NC}"
    echo "───────────────────────────────"

    if [ ! -d "$SCRIPT_DIR/backups" ] || [ -z "$(ls -A "$SCRIPT_DIR/backups" 2>/dev/null)" ]; then
        echo -e "${YELLOW}No backups yet.${NC}"
    else
        ls -lht "$SCRIPT_DIR/backups"/*.csv 2>/dev/null | head -10 | while read line; do
            echo "  $line"
        done
    fi
    echo ""
    read -p "Press Enter to return to menu..."
}

main_menu() {
    while true; do
        show_header
        show_status
        echo "───────────────────────────────────────────────"
        echo ""
        echo -e "  ${CYAN}1)${NC} Update File              ${GREEN}← Run this${NC}"
        echo -e "  ${CYAN}2)${NC} Dry Run (Preview)        ${YELLOW}See changes first${NC}"
        echo -e "  ${CYAN}3)${NC} View Backups"
        echo -e "  ${CYAN}4)${NC} Open Folder"
        echo ""
        echo -e "  ${CYAN}q)${NC} Quit"
        echo ""
        read -p "Choice: " choice

        case $choice in
            1) run_update ;;
            2) run_dry_run ;;
            3) view_backups ;;
            4) open "$SCRIPT_DIR" ;;
            q|Q) echo -e "\n${GREEN}Goodbye!${NC}"; exit 0 ;;
            *) echo -e "${RED}Invalid option${NC}"; sleep 1 ;;
        esac
    done
}

check_python
main_menu
