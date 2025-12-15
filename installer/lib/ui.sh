#!/bin/bash
# ui.sh - Interactive UI components for Shipping Forecast Installer
# Part of installer v0.1

# Source colors if not already loaded
if [[ -z "$BRAND_BLUE" ]]; then
    source "$(dirname "${BASH_SOURCE[0]}")/colors.sh"
fi

# Progress Bar
# Usage: show_progress <current> <total> <label>
show_progress() {
    local current=$1
    local total=$2
    local label="$3"
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))

    # Build progress bar
    local bar=""
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=0; i<empty; i++)); do bar+="░"; done

    # Print progress bar
    printf "\r${BRAND_BLUE}${label}${RESET} ${ACCENT_CYAN}[${bar}]${RESET} ${TEXT_WHITE}${percentage}%%${RESET}"

    # Add newline if complete
    if [[ $current -eq $total ]]; then
        echo
    fi
}

# Spinner for long-running operations
# Usage: start_spinner "message" ; do_work ; stop_spinner
declare -g SPINNER_PID=""
declare -g SPINNER_MSG=""

start_spinner() {
    local message="$1"
    SPINNER_MSG="$message"

    # Spinner frames
    local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")

    {
        local i=0
        while true; do
            printf "\r${ACCENT_CYAN}${frames[i]}${RESET} ${TEXT_WHITE}${SPINNER_MSG}${RESET}  "
            i=$(( (i + 1) % ${#frames[@]} ))
            sleep 0.1
        done
    } &

    SPINNER_PID=$!
    disown
}

stop_spinner() {
    local status=${1:-0}  # 0=success, 1=error, 2=warning

    if [[ -n "$SPINNER_PID" ]]; then
        kill "$SPINNER_PID" 2>/dev/null
        wait "$SPINNER_PID" 2>/dev/null
    fi

    # Clear the spinner line
    printf "\r%-80s\r" " "

    # Print final status
    case $status in
        0)
            print_success "$SPINNER_MSG"
            ;;
        1)
            print_error "$SPINNER_MSG"
            ;;
        2)
            print_warning "$SPINNER_MSG"
            ;;
    esac

    SPINNER_PID=""
    SPINNER_MSG=""
}

# Interactive Yes/No prompt
# Usage: if ask_yes_no "Continue?"; then ... fi
ask_yes_no() {
    local prompt="$1"
    local default="${2:-y}"  # Default is 'y'
    local response

    if [[ "$default" == "y" ]]; then
        local options="${MUTED_GRAY}[Y/n]${RESET}"
    else
        local options="${MUTED_GRAY}[y/N]${RESET}"
    fi

    while true; do
        echo -e -n "${ACCENT_CYAN}${SYMBOL_INFO}${RESET} ${TEXT_WHITE}${prompt}${RESET} ${options} "
        read -r response

        # Use default if empty
        if [[ -z "$response" ]]; then
            response="$default"
        fi

        case "${response,,}" in
            y|yes)
                return 0
                ;;
            n|no)
                return 1
                ;;
            *)
                print_warning "Please answer 'yes' or 'no'"
                ;;
        esac
    done
}

# Interactive text input
# Usage: result=$(ask_input "Prompt" "default value")
ask_input() {
    local prompt="$1"
    local default="$2"
    local response

    if [[ -n "$default" ]]; then
        echo -e -n "${ACCENT_CYAN}${SYMBOL_ARROW}${RESET} ${TEXT_WHITE}${prompt}${RESET} ${MUTED_GRAY}[${default}]${RESET}: "
    else
        echo -e -n "${ACCENT_CYAN}${SYMBOL_ARROW}${RESET} ${TEXT_WHITE}${prompt}${RESET}: "
    fi

    read -r response

    if [[ -z "$response" && -n "$default" ]]; then
        echo "$default"
    else
        echo "$response"
    fi
}

# Interactive menu selection
# Usage: choice=$(show_menu "Title" "Option 1" "Option 2" "Option 3")
show_menu() {
    local title="$1"
    shift
    local options=("$@")
    local choice
    local num_options=${#options[@]}

    echo
    echo -e "${BOLD}${BRAND_BLUE}${title}${RESET}"
    echo

    for i in "${!options[@]}"; do
        local num=$((i + 1))
        echo -e "  ${ACCENT_CYAN}${num})${RESET} ${TEXT_WHITE}${options[i]}${RESET}"
    done

    echo

    while true; do
        echo -e -n "${ACCENT_CYAN}${SYMBOL_ARROW}${RESET} ${TEXT_WHITE}Enter choice${RESET} ${MUTED_GRAY}[1-${num_options}]${RESET}: "
        read -r choice

        if [[ "$choice" =~ ^[0-9]+$ ]] && [[ $choice -ge 1 ]] && [[ $choice -le $num_options ]]; then
            echo "${options[$((choice - 1))]}"
            return 0
        else
            print_warning "Invalid choice. Please enter a number between 1 and ${num_options}"
        fi
    done
}

# Display a stage banner
# Usage: show_stage 1 "Pre-flight Checks"
show_stage() {
    local stage_num="$1"
    local stage_name="$2"
    local total_stages="${3:-10}"

    echo
    echo -e "${BRAND_BLUE}╔═══════════════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BRAND_BLUE}║${RESET}  ${BOLD}${TEXT_WHITE}Stage ${stage_num}/${total_stages}:${RESET} ${ACCENT_CYAN}${stage_name}${RESET}$(printf ' %.0s' $(seq 1 $((73 - ${#stage_name} - 11))))${BRAND_BLUE}║${RESET}"
    echo -e "${BRAND_BLUE}╚═══════════════════════════════════════════════════════════════════════════╝${RESET}"
    echo
}

# Display a checklist item
# Usage: show_check "Item description" <status>
# Status: 0=pending, 1=success, 2=error, 3=warning, 4=info
show_check() {
    local description="$1"
    local status=${2:-0}

    case $status in
        0)  # Pending
            echo -e "  ${MUTED_GRAY}○${RESET} ${TEXT_WHITE}${description}${RESET}"
            ;;
        1)  # Success
            echo -e "  ${SUCCESS_GREEN}✓${RESET} ${TEXT_WHITE}${description}${RESET}"
            ;;
        2)  # Error
            echo -e "  ${ERROR_RED}✗${RESET} ${TEXT_WHITE}${description}${RESET}"
            ;;
        3)  # Warning
            echo -e "  ${WARNING_YELLOW}⚠${RESET} ${TEXT_WHITE}${description}${RESET}"
            ;;
        4)  # Info
            echo -e "  ${ACCENT_CYAN}ℹ${RESET} ${TEXT_WHITE}${description}${RESET}"
            ;;
    esac
}

# Display welcome banner
show_welcome() {
    clear
    echo
    echo -e "${BRAND_BLUE}╔═══════════════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BRAND_BLUE}║${RESET}                                                                           ${BRAND_BLUE}║${RESET}"
    echo -e "${BRAND_BLUE}║${RESET}           ${BOLD}${TEXT_WHITE}🌊 Shipping Forecast Recorder Installer 🌊${RESET}              ${BRAND_BLUE}║${RESET}"
    echo -e "${BRAND_BLUE}║${RESET}                                                                           ${BRAND_BLUE}║${RESET}"
    echo -e "${BRAND_BLUE}║${RESET}              ${ACCENT_CYAN}Automated BBC Radio 4 Shipping Forecast${RESET}                ${BRAND_BLUE}║${RESET}"
    echo -e "${BRAND_BLUE}║${RESET}                ${ACCENT_CYAN}198 kHz Longwave • Podcast Feed${RESET}                     ${BRAND_BLUE}║${RESET}"
    echo -e "${BRAND_BLUE}║${RESET}                                                                           ${BRAND_BLUE}║${RESET}"
    echo -e "${BRAND_BLUE}║${RESET}                          ${MUTED_GRAY}Version 0.1${RESET}                                ${BRAND_BLUE}║${RESET}"
    echo -e "${BRAND_BLUE}║${RESET}                                                                           ${BRAND_BLUE}║${RESET}"
    echo -e "${BRAND_BLUE}╚═══════════════════════════════════════════════════════════════════════════╝${RESET}"
    echo
}

# Display completion banner
show_completion() {
    local success="$1"

    echo
    if [[ "$success" == "true" ]]; then
        echo -e "${SUCCESS_GREEN}╔═══════════════════════════════════════════════════════════════════════════╗${RESET}"
        echo -e "${SUCCESS_GREEN}║${RESET}                                                                           ${SUCCESS_GREEN}║${RESET}"
        echo -e "${SUCCESS_GREEN}║${RESET}                  ${BOLD}${TEXT_WHITE}✓  Installation Complete! ✓${RESET}                      ${SUCCESS_GREEN}║${RESET}"
        echo -e "${SUCCESS_GREEN}║${RESET}                                                                           ${SUCCESS_GREEN}║${RESET}"
        echo -e "${SUCCESS_GREEN}╚═══════════════════════════════════════════════════════════════════════════╝${RESET}"
    else
        echo -e "${ERROR_RED}╔═══════════════════════════════════════════════════════════════════════════╗${RESET}"
        echo -e "${ERROR_RED}║${RESET}                                                                           ${ERROR_RED}║${RESET}"
        echo -e "${ERROR_RED}║${RESET}                    ${BOLD}${TEXT_WHITE}✗  Installation Failed  ✗${RESET}                       ${ERROR_RED}║${RESET}"
        echo -e "${ERROR_RED}║${RESET}                                                                           ${ERROR_RED}║${RESET}"
        echo -e "${ERROR_RED}╚═══════════════════════════════════════════════════════════════════════════╝${RESET}"
    fi
    echo
}

# Display a key-value pair (for configuration display)
# Usage: show_config_item "Key" "Value"
show_config_item() {
    local key="$1"
    local value="$2"
    local key_width=30

    printf "  ${ACCENT_CYAN}%-${key_width}s${RESET} ${MUTED_GRAY}:${RESET} ${TEXT_WHITE}%s${RESET}\n" "$key" "$value"
}

# Display a code block
# Usage: show_code "command to run"
show_code() {
    local code="$1"
    echo
    echo -e "${MUTED_GRAY}┌─────────────────────────────────────────────────────────────────────────┐${RESET}"
    echo -e "${MUTED_GRAY}│${RESET} ${TEXT_WHITE}${code}${RESET}$(printf ' %.0s' $(seq 1 $((72 - ${#code}))))${MUTED_GRAY}│${RESET}"
    echo -e "${MUTED_GRAY}└─────────────────────────────────────────────────────────────────────────┘${RESET}"
    echo
}

# Display an error message with details
# Usage: show_error_detail "Error message" "Details (optional)"
show_error_detail() {
    local message="$1"
    local details="$2"

    echo
    echo -e "${ERROR_RED}╔═══════════════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${ERROR_RED}║${RESET}  ${BOLD}${TEXT_WHITE}ERROR${RESET}                                                                  ${ERROR_RED}║${RESET}"
    echo -e "${ERROR_RED}╠═══════════════════════════════════════════════════════════════════════════╣${RESET}"

    # Word wrap the message
    local wrapped_msg=$(echo "$message" | fold -s -w 73)
    while IFS= read -r line; do
        local padding=$((73 - ${#line}))
        echo -e "${ERROR_RED}║${RESET} ${TEXT_WHITE}${line}${RESET}$(printf ' %.0s' $(seq 1 $padding)) ${ERROR_RED}║${RESET}"
    done <<< "$wrapped_msg"

    if [[ -n "$details" ]]; then
        echo -e "${ERROR_RED}║${RESET}                                                                           ${ERROR_RED}║${RESET}"
        echo -e "${ERROR_RED}║${RESET}  ${MUTED_GRAY}Details:${RESET}                                                              ${ERROR_RED}║${RESET}"

        local wrapped_details=$(echo "$details" | fold -s -w 73)
        while IFS= read -r line; do
            local padding=$((73 - ${#line}))
            echo -e "${ERROR_RED}║${RESET} ${MUTED_GRAY}${line}${RESET}$(printf ' %.0s' $(seq 1 $padding)) ${ERROR_RED}║${RESET}"
        done <<< "$wrapped_details"
    fi

    echo -e "${ERROR_RED}╚═══════════════════════════════════════════════════════════════════════════╝${RESET}"
    echo
}

# Pause and wait for user to press Enter
pause() {
    local message="${1:-Press Enter to continue...}"
    echo
    echo -e -n "${MUTED_GRAY}${message}${RESET}"
    read -r
}
