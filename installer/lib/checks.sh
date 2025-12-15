#!/bin/bash
# checks.sh - Pre-flight validation and system checks
# Part of installer v0.1

# Source dependencies
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "$SCRIPT_DIR/colors.sh"
source "$SCRIPT_DIR/ui.sh"

# Global variables for check results
declare -g CHECK_FAILED=0
declare -g CHECK_WARNINGS=0

# Check if running as root (should NOT be root)
check_not_root() {
    show_check "Checking user privileges" 0

    if [[ $EUID -eq 0 ]]; then
        show_check "Should not run as root" 2
        print_error "This installer should not be run as root"
        print_info "Run as a regular user with sudo privileges"
        return 1
    fi

    show_check "Running as non-root user" 1
    return 0
}

# Check if user has sudo privileges
check_sudo() {
    show_check "Checking sudo access" 0

    if ! sudo -n true 2>/dev/null; then
        # User doesn't have passwordless sudo, prompt for password
        if ! sudo -v; then
            show_check "Sudo access required" 2
            print_error "This installer requires sudo privileges"
            return 1
        fi
    fi

    show_check "Sudo access verified" 1
    return 0
}

# Check operating system
check_os() {
    show_check "Detecting operating system" 0

    if [[ ! -f /etc/os-release ]]; then
        show_check "Cannot detect OS" 2
        print_error "/etc/os-release not found"
        return 1
    fi

    source /etc/os-release

    export DETECTED_OS="$ID"
    export DETECTED_OS_VERSION="$VERSION_ID"
    export DETECTED_OS_NAME="$NAME"

    show_check "Operating System: $DETECTED_OS_NAME" 1
    return 0
}

# Check system architecture
check_architecture() {
    show_check "Checking system architecture" 0

    local arch=$(uname -m)
    export DETECTED_ARCH="$arch"

    # Check if compatible
    case "$arch" in
        x86_64|aarch64|armv7l|armv8l)
            show_check "Architecture: $arch" 1
            return 0
            ;;
        *)
            show_check "Unsupported architecture: $arch" 3
            print_warning "This architecture may not be fully supported"
            ((CHECK_WARNINGS++))
            return 0
            ;;
    esac
}

# Check Python version
check_python() {
    show_check "Checking Python installation" 0

    if ! command -v python3 &>/dev/null; then
        show_check "Python 3 not found" 2
        print_error "Python 3 is required but not installed"
        return 1
    fi

    local python_version=$(python3 --version 2>&1 | awk '{print $2}')
    local python_major=$(echo "$python_version" | cut -d. -f1)
    local python_minor=$(echo "$python_version" | cut -d. -f2)

    export DETECTED_PYTHON_VERSION="$python_version"

    # Require Python 3.7+
    if [[ $python_major -lt 3 ]] || [[ $python_major -eq 3 && $python_minor -lt 7 ]]; then
        show_check "Python $python_version (too old)" 2
        print_error "Python 3.7 or newer is required"
        return 1
    fi

    show_check "Python $python_version" 1
    return 0
}

# Check disk space
check_disk_space() {
    show_check "Checking available disk space" 0

    local install_dir="${1:-/home/$USER}"
    local required_mb=500  # Require at least 500MB

    # Get available space in MB
    local available_mb=$(df -m "$install_dir" | awk 'NR==2 {print $4}')

    export DETECTED_DISK_SPACE="$available_mb"

    if [[ $available_mb -lt $required_mb ]]; then
        show_check "Insufficient disk space (${available_mb}MB available, ${required_mb}MB required)" 2
        print_error "Not enough disk space for installation"
        return 1
    fi

    show_check "Disk space: ${available_mb}MB available" 1
    return 0
}

# Check internet connectivity
check_internet() {
    show_check "Checking internet connectivity" 0

    # Try to reach common DNS servers and websites
    local test_hosts=("8.8.8.8" "1.1.1.1")

    for host in "${test_hosts[@]}"; do
        if ping -c 1 -W 2 "$host" &>/dev/null; then
            show_check "Internet connectivity" 1
            return 0
        fi
    done

    show_check "No internet connectivity" 2
    print_error "Internet connection is required for installation"
    return 1
}

# Check if Git is installed
check_git() {
    show_check "Checking Git installation" 0

    if ! command -v git &>/dev/null; then
        show_check "Git not installed" 3
        print_warning "Git is not installed (required for KiwiSDR client)"
        ((CHECK_WARNINGS++))
        return 0
    fi

    local git_version=$(git --version | awk '{print $3}')
    show_check "Git $git_version" 1
    export DETECTED_GIT_VERSION="$git_version"
    return 0
}

# Check for existing installation
check_existing_installation() {
    show_check "Checking for existing installation" 0

    local kiwi_recorder_path="/home/$USER/kiwi_recorder.py"
    local install_marker="/home/$USER/.shipping-forecast-installed"

    if [[ -f "$install_marker" ]]; then
        show_check "Previous installation detected" 3
        print_warning "Existing installation found"
        export EXISTING_INSTALLATION=true
        ((CHECK_WARNINGS++))
        return 0
    fi

    if [[ -f "$kiwi_recorder_path" ]]; then
        show_check "kiwi_recorder.py exists" 4
        print_info "Found existing kiwi_recorder.py (will be backed up)"
        export EXISTING_KIWI_RECORDER=true
    else
        show_check "Clean installation" 1
        export EXISTING_INSTALLATION=false
        export EXISTING_KIWI_RECORDER=false
    fi

    return 0
}

# Check for required ports availability
check_ports() {
    show_check "Checking port availability" 0

    local required_ports=(8080)  # nginx port
    local ports_in_use=()

    for port in "${required_ports[@]}"; do
        if sudo netstat -tuln 2>/dev/null | grep -q ":$port " || \
           sudo ss -tuln 2>/dev/null | grep -q ":$port "; then
            ports_in_use+=("$port")
        fi
    done

    if [[ ${#ports_in_use[@]} -gt 0 ]]; then
        show_check "Ports in use: ${ports_in_use[*]}" 3
        print_warning "Required ports are already in use (will be reconfigured)"
        ((CHECK_WARNINGS++))
        export PORTS_IN_USE="${ports_in_use[*]}"
    else
        show_check "Required ports available" 1
    fi

    return 0
}

# Check system services
check_systemd() {
    show_check "Checking systemd" 0

    if ! command -v systemctl &>/dev/null; then
        show_check "systemd not available" 2
        print_error "This installer requires systemd"
        return 1
    fi

    show_check "systemd available" 1
    return 0
}

# Check cron availability
check_cron() {
    show_check "Checking cron" 0

    if ! command -v crontab &>/dev/null; then
        show_check "cron not available" 3
        print_warning "cron not found (required for scheduling)"
        ((CHECK_WARNINGS++))
        return 0
    fi

    show_check "cron available" 1
    return 0
}

# Check USB devices (for RTL-SDR or other SDR hardware)
check_usb_devices() {
    show_check "Checking USB devices" 0

    if ! command -v lsusb &>/dev/null; then
        show_check "lsusb not available" 4
        return 0
    fi

    # Look for RTL-SDR or similar devices
    local sdr_found=false
    if lsusb | grep -iq "RTL\|SDR\|DVB"; then
        sdr_found=true
    fi

    if [[ "$sdr_found" == "true" ]]; then
        show_check "SDR device detected" 4
        print_info "Local SDR hardware found (can be used instead of network KiwiSDR)"
    else
        show_check "No local SDR device (will use network KiwiSDR)" 4
    fi

    export SDR_DEVICE_FOUND="$sdr_found"
    return 0
}

# Check network configuration
check_network() {
    show_check "Checking network configuration" 0

    # Get primary network interface
    local primary_iface=$(ip route | grep default | awk '{print $5}' | head -1)

    if [[ -z "$primary_iface" ]]; then
        show_check "No default network route" 3
        print_warning "No default network route found"
        ((CHECK_WARNINGS++))
        return 0
    fi

    # Get IP address
    local ip_addr=$(ip addr show "$primary_iface" | grep "inet " | awk '{print $2}' | cut -d/ -f1 | head -1)

    export DETECTED_NETWORK_IFACE="$primary_iface"
    export DETECTED_IP_ADDR="$ip_addr"

    show_check "Network: $primary_iface ($ip_addr)" 1
    return 0
}

# Master pre-flight check function
run_preflight_checks() {
    show_stage 1 "Pre-flight Checks"

    print_info "Running system validation..."
    echo

    # Run all checks
    check_not_root || ((CHECK_FAILED++))
    check_sudo || ((CHECK_FAILED++))
    check_os || ((CHECK_FAILED++))
    check_architecture
    check_python || ((CHECK_FAILED++))
    check_disk_space || ((CHECK_FAILED++))
    check_internet || ((CHECK_FAILED++))
    check_git
    check_systemd || ((CHECK_FAILED++))
    check_cron
    check_existing_installation
    check_ports
    check_usb_devices
    check_network

    echo

    # Summary
    if [[ $CHECK_FAILED -gt 0 ]]; then
        print_error "Pre-flight checks failed: $CHECK_FAILED critical issue(s)"
        print_info "Please resolve the errors above before continuing"
        return 1
    elif [[ $CHECK_WARNINGS -gt 0 ]]; then
        print_warning "Pre-flight checks completed with $CHECK_WARNINGS warning(s)"
        if ! ask_yes_no "Continue anyway?"; then
            print_info "Installation cancelled by user"
            return 1
        fi
    else
        print_success "All pre-flight checks passed!"
    fi

    return 0
}

# Validation check for post-installation
validate_installation() {
    show_stage 10 "Validation & Testing"

    print_info "Validating installation..."
    echo

    local validation_failed=0

    # Check kiwi_recorder.py exists
    show_check "Checking kiwi_recorder.py" 0
    if [[ -f "/home/$USER/kiwi_recorder.py" ]]; then
        show_check "kiwi_recorder.py installed" 1
    else
        show_check "kiwi_recorder.py missing" 2
        ((validation_failed++))
    fi

    # Check Python dependencies
    show_check "Checking Python dependencies" 0
    if python3 -c "import requests, numpy, scipy" 2>/dev/null; then
        show_check "Python dependencies installed" 1
    else
        show_check "Python dependencies missing" 2
        ((validation_failed++))
    fi

    # Check nginx configuration
    show_check "Checking nginx" 0
    if sudo systemctl is-active --quiet nginx; then
        show_check "nginx running" 1
    else
        show_check "nginx not running" 3
        ((validation_failed++))
    fi

    # Check Tailscale
    show_check "Checking Tailscale" 0
    if command -v tailscale &>/dev/null; then
        show_check "Tailscale installed" 1
    else
        show_check "Tailscale not installed" 3
    fi

    # Check cron jobs
    show_check "Checking cron configuration" 0
    if crontab -l 2>/dev/null | grep -q "kiwi_recorder.py"; then
        show_check "Cron jobs configured" 1
    else
        show_check "Cron jobs not configured" 3
    fi

    echo

    if [[ $validation_failed -eq 0 ]]; then
        print_success "Installation validation passed!"
        return 0
    else
        print_warning "Installation completed with $validation_failed issue(s)"
        print_info "Some components may need manual configuration"
        return 1
    fi
}
