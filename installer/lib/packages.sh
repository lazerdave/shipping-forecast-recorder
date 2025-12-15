#!/bin/bash
# packages.sh - Multi-distribution package management
# Part of installer v0.1

# Source dependencies
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "$SCRIPT_DIR/colors.sh"
source "$SCRIPT_DIR/ui.sh"

# Detect package manager
detect_package_manager() {
    if command -v apt-get &>/dev/null; then
        export PKG_MANAGER="apt"
    elif command -v dnf &>/dev/null; then
        export PKG_MANAGER="dnf"
    elif command -v yum &>/dev/null; then
        export PKG_MANAGER="yum"
    elif command -v pacman &>/dev/null; then
        export PKG_MANAGER="pacman"
    elif command -v zypper &>/dev/null; then
        export PKG_MANAGER="zypper"
    else
        export PKG_MANAGER="unknown"
        return 1
    fi
    return 0
}

# Update package cache
update_package_cache() {
    print_step "Updating package cache..."

    case "$PKG_MANAGER" in
        apt)
            sudo apt-get update -qq 2>&1 | tail -5
            ;;
        dnf)
            sudo dnf check-update -q 2>&1 | tail -5
            ;;
        yum)
            sudo yum check-update -q 2>&1 | tail -5
            ;;
        pacman)
            sudo pacman -Sy --noconfirm 2>&1 | tail -5
            ;;
        zypper)
            sudo zypper refresh -q 2>&1 | tail -5
            ;;
        *)
            print_error "Unknown package manager"
            return 1
            ;;
    esac

    if [[ $? -eq 0 ]]; then
        print_success "Package cache updated"
        return 0
    else
        print_warning "Package cache update failed (continuing anyway)"
        return 0
    fi
}

# Install a package
install_package() {
    local package="$1"
    local display_name="${2:-$package}"

    print_step "Installing $display_name..."

    case "$PKG_MANAGER" in
        apt)
            sudo apt-get install -y -qq "$package" 2>&1 | tail -10
            ;;
        dnf)
            sudo dnf install -y -q "$package" 2>&1 | tail -10
            ;;
        yum)
            sudo yum install -y -q "$package" 2>&1 | tail -10
            ;;
        pacman)
            sudo pacman -S --noconfirm --needed "$package" 2>&1 | tail -10
            ;;
        zypper)
            sudo zypper install -y "$package" 2>&1 | tail -10
            ;;
        *)
            print_error "Unknown package manager"
            return 1
            ;;
    esac

    local result=$?

    if [[ $result -eq 0 ]]; then
        print_success "$display_name installed"
        return 0
    else
        print_error "Failed to install $display_name"
        return 1
    fi
}

# Check if package is installed
is_package_installed() {
    local package="$1"

    case "$PKG_MANAGER" in
        apt)
            dpkg -l "$package" 2>/dev/null | grep -q "^ii"
            ;;
        dnf|yum)
            rpm -q "$package" &>/dev/null
            ;;
        pacman)
            pacman -Q "$package" &>/dev/null
            ;;
        zypper)
            rpm -q "$package" &>/dev/null
            ;;
        *)
            return 1
            ;;
    esac

    return $?
}

# Install system dependencies
install_system_deps() {
    show_stage 3 "System Dependencies"

    print_info "Installing required system packages..."
    echo

    # Detect package manager
    if ! detect_package_manager; then
        print_error "Could not detect package manager"
        return 1
    fi

    print_info "Package manager: $PKG_MANAGER"
    echo

    # Update package cache
    update_package_cache

    echo

    # Define package mappings for different distributions
    declare -A PACKAGES

    # Common packages
    PACKAGES[git]="git"
    PACKAGES[python3]="python3"
    PACKAGES[curl]="curl"
    PACKAGES[nginx]="nginx"

    # Python development packages
    case "$PKG_MANAGER" in
        apt)
            PACKAGES[python3-pip]="python3-pip"
            PACKAGES[python3-venv]="python3-venv"
            PACKAGES[python3-dev]="python3-dev"
            PACKAGES[python3-numpy]="python3-numpy"
            PACKAGES[python3-scipy]="python3-scipy"
            ;;
        dnf|yum)
            PACKAGES[python3-pip]="python3-pip"
            PACKAGES[python3-devel]="python3-devel"
            PACKAGES[python3-numpy]="python3-numpy"
            PACKAGES[python3-scipy]="python3-scipy"
            ;;
        pacman)
            PACKAGES[python3-pip]="python-pip"
            PACKAGES[python3-numpy]="python-numpy"
            PACKAGES[python3-scipy]="python-scipy"
            ;;
        zypper)
            PACKAGES[python3-pip]="python3-pip"
            PACKAGES[python3-devel]="python3-devel"
            PACKAGES[python3-numpy]="python3-numpy"
            PACKAGES[python3-scipy]="python3-scipy"
            ;;
    esac

    # Build tools (for Python packages that need compilation)
    case "$PKG_MANAGER" in
        apt)
            PACKAGES[build-essential]="build-essential"
            ;;
        dnf|yum)
            PACKAGES[build-essential]="gcc gcc-c++ make"
            ;;
        pacman)
            PACKAGES[build-essential]="base-devel"
            ;;
        zypper)
            PACKAGES[build-essential]="gcc gcc-c++ make"
            ;;
    esac

    # Install packages
    local failed_packages=()

    for pkg_key in "${!PACKAGES[@]}"; do
        local pkg_name="${PACKAGES[$pkg_key]}"

        # Check if already installed
        if is_package_installed "$pkg_name"; then
            print_info "$pkg_key already installed"
            continue
        fi

        # Install the package
        if ! install_package "$pkg_name" "$pkg_key"; then
            failed_packages+=("$pkg_key")
        fi
    done

    echo

    if [[ ${#failed_packages[@]} -gt 0 ]]; then
        print_error "Failed to install: ${failed_packages[*]}"
        return 1
    else
        print_success "All system dependencies installed"
        return 0
    fi
}

# Install Python packages via pip
install_python_deps() {
    show_stage 4 "Python Dependencies"

    print_info "Installing Python packages..."
    echo

    # Ensure pip is available
    if ! command -v pip3 &>/dev/null; then
        print_error "pip3 not found"
        return 1
    fi

    # Upgrade pip first
    print_step "Upgrading pip..."
    python3 -m pip install --upgrade pip --quiet 2>&1 | tail -5

    if [[ $? -eq 0 ]]; then
        print_success "pip upgraded"
    else
        print_warning "pip upgrade failed (continuing anyway)"
    fi

    echo

    # Install packages from requirements.txt
    local requirements_file="$1"

    if [[ ! -f "$requirements_file" ]]; then
        print_error "requirements.txt not found: $requirements_file"
        return 1
    fi

    print_step "Installing packages from requirements.txt..."

    # Install with progress
    python3 -m pip install -r "$requirements_file" --quiet 2>&1 | tail -10

    if [[ $? -eq 0 ]]; then
        print_success "Python dependencies installed"
        return 0
    else
        print_error "Failed to install Python dependencies"
        return 1
    fi
}

# Install Tailscale
install_tailscale() {
    print_info "Installing Tailscale..."
    echo

    # Check if already installed
    if command -v tailscale &>/dev/null; then
        local ts_version=$(tailscale version | head -1)
        print_info "Tailscale already installed: $ts_version"
        return 0
    fi

    # Install Tailscale using official script
    print_step "Downloading Tailscale installer..."

    curl -fsSL https://tailscale.com/install.sh -o /tmp/tailscale-install.sh

    if [[ $? -ne 0 ]]; then
        print_error "Failed to download Tailscale installer"
        return 1
    fi

    print_step "Running Tailscale installer..."

    sudo sh /tmp/tailscale-install.sh 2>&1 | tail -10

    if [[ $? -eq 0 ]]; then
        print_success "Tailscale installed"
        rm -f /tmp/tailscale-install.sh
        return 0
    else
        print_error "Failed to install Tailscale"
        rm -f /tmp/tailscale-install.sh
        return 1
    fi
}

# Clone KiwiSDR client repository
install_kiwi_client() {
    local install_dir="$1"
    local kiwi_client_dir="$install_dir/kiwiclient"

    print_info "Installing KiwiSDR client..."
    echo

    # Check if already exists
    if [[ -d "$kiwi_client_dir" ]]; then
        print_warning "KiwiSDR client directory already exists"

        if ask_yes_no "Update existing installation?"; then
            print_step "Updating KiwiSDR client..."
            cd "$kiwi_client_dir" || return 1

            git pull 2>&1 | tail -10

            if [[ $? -eq 0 ]]; then
                print_success "KiwiSDR client updated"
                return 0
            else
                print_error "Failed to update KiwiSDR client"
                return 1
            fi
        else
            print_info "Using existing KiwiSDR client"
            return 0
        fi
    fi

    # Clone repository
    print_step "Cloning KiwiSDR client repository..."

    git clone https://github.com/jks-prv/kiwiclient.git "$kiwi_client_dir" 2>&1 | tail -10

    if [[ $? -eq 0 ]]; then
        print_success "KiwiSDR client installed"
        return 0
    else
        print_error "Failed to clone KiwiSDR client repository"
        return 1
    fi
}

# Verify all dependencies are installed
verify_dependencies() {
    print_info "Verifying dependencies..."
    echo

    local missing_deps=()

    # Check commands
    local required_commands=("python3" "git" "curl" "nginx" "crontab")

    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &>/dev/null; then
            missing_deps+=("$cmd")
            show_check "$cmd" 2
        else
            show_check "$cmd" 1
        fi
    done

    # Check Python modules
    local required_modules=("requests" "numpy" "scipy")

    for module in "${required_modules[@]}"; do
        if ! python3 -c "import $module" 2>/dev/null; then
            missing_deps+=("python3-$module")
            show_check "python3-$module" 2
        else
            show_check "python3-$module" 1
        fi
    done

    echo

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        return 1
    else
        print_success "All dependencies verified"
        return 0
    fi
}
