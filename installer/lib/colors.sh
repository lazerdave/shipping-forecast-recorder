#!/bin/bash
# colors.sh - Color definitions and output helpers for Shipping Forecast Installer
# Part of installer v0.1

# Color Palette (256-color mode)
export BRAND_BLUE='\033[38;5;33m'        # Primary brand color
export ACCENT_CYAN='\033[38;5;51m'       # Highlights and accents
export SUCCESS_GREEN='\033[38;5;46m'     # Success messages
export WARNING_YELLOW='\033[38;5;226m'   # Warning messages
export ERROR_RED='\033[38;5;196m'        # Error messages
export MUTED_GRAY='\033[38;5;240m'       # Secondary text
export TEXT_WHITE='\033[38;5;255m'       # Primary text
export RESET='\033[0m'                   # Reset all formatting

# Text Formatting
export BOLD='\033[1m'
export DIM='\033[2m'
export ITALIC='\033[3m'
export UNDERLINE='\033[4m'

# Background Colors (for emphasis)
export BG_BLUE='\033[48;5;33m'
export BG_GREEN='\033[48;5;46m'
export BG_RED='\033[48;5;196m'
export BG_YELLOW='\033[48;5;226m'

# Status Symbols (using Unicode box-drawing and symbols)
export SYMBOL_SUCCESS="${SUCCESS_GREEN}✓${RESET}"
export SYMBOL_ERROR="${ERROR_RED}✗${RESET}"
export SYMBOL_WARNING="${WARNING_YELLOW}⚠${RESET}"
export SYMBOL_INFO="${ACCENT_CYAN}ℹ${RESET}"
export SYMBOL_ARROW="${BRAND_BLUE}→${RESET}"
export SYMBOL_DOT="${MUTED_GRAY}•${RESET}"

# Box Drawing Characters
export BOX_TL='╔'  # Top-left
export BOX_TR='╗'  # Top-right
export BOX_BL='╚'  # Bottom-left
export BOX_BR='╝'  # Bottom-right
export BOX_H='═'   # Horizontal
export BOX_V='║'   # Vertical
export BOX_VR='╠'  # Vertical-right (left edge)
export BOX_VL='╣'  # Vertical-left (right edge)
export BOX_HU='╩'  # Horizontal-up (bottom edge)
export BOX_HD='╦'  # Horizontal-down (top edge)

# Output Helper Functions

# Print colored message with optional symbol
# Usage: print_message "color" "symbol" "message"
print_message() {
    local color="$1"
    local symbol="$2"
    local message="$3"
    echo -e "${color}${symbol} ${message}${RESET}"
}

# Convenience functions for common message types
print_success() {
    print_message "$SUCCESS_GREEN" "$SYMBOL_SUCCESS" "$1"
}

print_error() {
    print_message "$ERROR_RED" "$SYMBOL_ERROR" "$1"
}

print_warning() {
    print_message "$WARNING_YELLOW" "$SYMBOL_WARNING" "$1"
}

print_info() {
    print_message "$ACCENT_CYAN" "$SYMBOL_INFO" "$1"
}

print_step() {
    print_message "$BRAND_BLUE" "$SYMBOL_ARROW" "$1"
}

# Print a horizontal line with optional title
# Usage: print_line [width] [title]
print_line() {
    local width=${1:-80}
    local title="$2"

    if [[ -z "$title" ]]; then
        printf "%${width}s\n" | tr ' ' '─'
    else
        local title_len=${#title}
        local padding=$(( (width - title_len - 4) / 2 ))
        printf "─%.0s" $(seq 1 $padding)
        echo -n "  $title  "
        printf "─%.0s" $(seq 1 $padding)
        echo
    fi
}

# Print a section header
# Usage: print_header "Title" [width]
print_header() {
    local title="$1"
    local width=${2:-80}
    local title_len=${#title}
    local padding=$(( (width - title_len - 2) / 2 ))

    echo
    echo -e "${BRAND_BLUE}${BOX_TL}$(printf "${BOX_H}%.0s" $(seq 1 $((width-2))))${BOX_TR}${RESET}"
    echo -e "${BRAND_BLUE}${BOX_V}${RESET}$(printf " %.0s" $(seq 1 $padding))${BOLD}${TEXT_WHITE}${title}${RESET}$(printf " %.0s" $(seq 1 $padding))${BRAND_BLUE}${BOX_V}${RESET}"
    echo -e "${BRAND_BLUE}${BOX_BL}$(printf "${BOX_H}%.0s" $(seq 1 $((width-2))))${BOX_BR}${RESET}"
    echo
}

# Print a box with content
# Usage: print_box "content" [width]
print_box() {
    local content="$1"
    local width=${2:-80}

    echo -e "${BRAND_BLUE}${BOX_TL}$(printf "${BOX_H}%.0s" $(seq 1 $((width-2))))${BOX_TR}${RESET}"

    # Process multi-line content
    while IFS= read -r line; do
        local line_len=${#line}
        local padding=$((width - line_len - 4))
        echo -e "${BRAND_BLUE}${BOX_V}${RESET} ${line}$(printf " %.0s" $(seq 1 $padding)) ${BRAND_BLUE}${BOX_V}${RESET}"
    done <<< "$content"

    echo -e "${BRAND_BLUE}${BOX_BL}$(printf "${BOX_H}%.0s" $(seq 1 $((width-2))))${BOX_BR}${RESET}"
}

# Print a titled box (for important notices)
# Usage: print_notice "title" "content" [width]
print_notice() {
    local title="$1"
    local content="$2"
    local width=${3:-80}

    local title_len=${#title}
    local title_padding=$(( (width - title_len - 6) / 2 ))

    echo -e "${BRAND_BLUE}${BOX_TL}$(printf "${BOX_H}%.0s" $(seq 1 $title_padding))${BOX_HD} ${BOLD}${title}${RESET}${BRAND_BLUE} ${BOX_HD}$(printf "${BOX_H}%.0s" $(seq 1 $title_padding))${BOX_TR}${RESET}"

    # Process multi-line content
    while IFS= read -r line; do
        local line_len=${#line}
        local padding=$((width - line_len - 4))
        echo -e "${BRAND_BLUE}${BOX_V}${RESET} ${line}$(printf " %.0s" $(seq 1 $padding)) ${BRAND_BLUE}${BOX_V}${RESET}"
    done <<< "$content"

    echo -e "${BRAND_BLUE}${BOX_BL}$(printf "${BOX_H}%.0s" $(seq 1 $((width-2))))${BOX_BR}${RESET}"
}

# Detect terminal capabilities
detect_terminal_capabilities() {
    # Check if terminal supports 256 colors
    if [[ $(tput colors 2>/dev/null) -ge 256 ]]; then
        export TERM_COLORS=256
    else
        export TERM_COLORS=8
        # Fallback to basic colors if 256 not supported
        export BRAND_BLUE='\033[34m'
        export ACCENT_CYAN='\033[36m'
        export SUCCESS_GREEN='\033[32m'
        export WARNING_YELLOW='\033[33m'
        export ERROR_RED='\033[31m'
        export MUTED_GRAY='\033[90m'
        export TEXT_WHITE='\033[97m'
    fi

    # Check if terminal supports UTF-8 (for box drawing)
    if [[ "$LANG" =~ UTF-8 ]] || [[ "$LC_ALL" =~ UTF-8 ]]; then
        export TERM_UTF8=true
    else
        export TERM_UTF8=false
        # Fallback to ASCII box drawing
        BOX_TL='+'
        BOX_TR='+'
        BOX_BL='+'
        BOX_BR='+'
        BOX_H='-'
        BOX_V='|'
        BOX_VR='+'
        BOX_VL='+'
        BOX_HU='+'
        BOX_HD='+'
    fi
}

# Initialize terminal detection on source
detect_terminal_capabilities
