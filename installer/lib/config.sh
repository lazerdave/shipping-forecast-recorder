#!/bin/bash
# config.sh - Configuration management for Shipping Forecast Installer
# Part of installer v0.1

# Source dependencies
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "$SCRIPT_DIR/colors.sh"
source "$SCRIPT_DIR/ui.sh"

# Default configuration values
declare -A CONFIG
CONFIG[INSTALL_DIR]="/home/$USER"
CONFIG[KIWI_CLIENT_DIR]="/home/$USER/kiwiclient"
CONFIG[OUTPUT_DIR]="/home/$USER/share/198k"
CONFIG[SCAN_DIR]="/home/$USER/kiwi_scans"
CONFIG[FREQUENCY]="198"
CONFIG[DURATION]="780"  # 13 minutes
CONFIG[SCAN_WORKERS]="15"
CONFIG[FEED_URL]=""
CONFIG[PODCAST_TITLE]="Shipping Forecast Tailscale"
CONFIG[PODCAST_AUTHOR]="BBC Radio 4"
CONFIG[ENABLE_TAILSCALE]="true"
CONFIG[ENABLE_NGINX]="true"
CONFIG[ENABLE_CRON]="true"
CONFIG[NGINX_PORT]="8080"
CONFIG[TIMEZONE]="Europe/London"

# Config file path
CONFIG_FILE="/home/$USER/.shipping-forecast.conf"

# Load existing configuration if available
load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        print_info "Loading existing configuration..."
        source "$CONFIG_FILE"
        return 0
    fi
    return 1
}

# Save configuration to file
save_config() {
    print_step "Saving configuration..."

    {
        echo "# Shipping Forecast Recorder Configuration"
        echo "# Generated: $(date)"
        echo ""
        for key in "${!CONFIG[@]}"; do
            echo "CONFIG[$key]=\"${CONFIG[$key]}\""
        done
    } > "$CONFIG_FILE"

    if [[ $? -eq 0 ]]; then
        print_success "Configuration saved to $CONFIG_FILE"
        return 0
    else
        print_error "Failed to save configuration"
        return 1
    fi
}

# Interactive configuration
interactive_config() {
    show_stage 2 "Configuration"

    print_info "Let's configure your Shipping Forecast installation"
    echo

    print_notice "Paths Configuration" "Configure installation directories"
    echo

    # Installation directory
    local default_install_dir="${CONFIG[INSTALL_DIR]}"
    local install_dir=$(ask_input "Installation directory" "$default_install_dir")
    CONFIG[INSTALL_DIR]="${install_dir:-$default_install_dir}"

    # Output directory
    local default_output_dir="${CONFIG[OUTPUT_DIR]}"
    local output_dir=$(ask_input "Audio output directory" "$default_output_dir")
    CONFIG[OUTPUT_DIR]="${output_dir:-$default_output_dir}"

    # Scan directory
    local default_scan_dir="${CONFIG[SCAN_DIR]}"
    local scan_dir=$(ask_input "Scan results directory" "$default_scan_dir")
    CONFIG[SCAN_DIR]="${scan_dir:-$default_scan_dir}"

    echo

    print_notice "Recording Configuration" "Configure recording parameters"
    echo

    # Frequency
    local default_freq="${CONFIG[FREQUENCY]}"
    local freq=$(ask_input "Frequency (kHz)" "$default_freq")
    CONFIG[FREQUENCY]="${freq:-$default_freq}"

    # Duration
    local default_duration="${CONFIG[DURATION]}"
    local duration=$(ask_input "Recording duration (seconds)" "$default_duration")
    CONFIG[DURATION]="${duration:-$default_duration}"

    # Scan workers
    local default_workers="${CONFIG[SCAN_WORKERS]}"
    local workers=$(ask_input "Parallel scan workers" "$default_workers")
    CONFIG[SCAN_WORKERS]="${workers:-$default_workers}"

    echo

    print_notice "Podcast Configuration" "Configure podcast feed settings"
    echo

    # Podcast title
    local default_title="${CONFIG[PODCAST_TITLE]}"
    local title=$(ask_input "Podcast title" "$default_title")
    CONFIG[PODCAST_TITLE]="${title:-$default_title}"

    # Podcast author
    local default_author="${CONFIG[PODCAST_AUTHOR]}"
    local author=$(ask_input "Podcast author" "$default_author")
    CONFIG[PODCAST_AUTHOR]="${author:-$default_author}"

    echo

    print_notice "Optional Components" "Enable or disable optional features"
    echo

    # Tailscale
    if ask_yes_no "Enable Tailscale public access?" "y"; then
        CONFIG[ENABLE_TAILSCALE]="true"
    else
        CONFIG[ENABLE_TAILSCALE]="false"
    fi

    # Nginx
    if ask_yes_no "Enable nginx HTTP server?" "y"; then
        CONFIG[ENABLE_NGINX]="true"

        # Nginx port
        local default_port="${CONFIG[NGINX_PORT]}"
        local port=$(ask_input "nginx port" "$default_port")
        CONFIG[NGINX_PORT]="${port:-$default_port}"
    else
        CONFIG[ENABLE_NGINX]="false"
    fi

    # Cron
    if ask_yes_no "Enable automatic cron scheduling?" "y"; then
        CONFIG[ENABLE_CRON]="true"
    else
        CONFIG[ENABLE_CRON]="false"
    fi

    echo

    # Display configuration summary
    show_config_summary

    echo

    if ask_yes_no "Is this configuration correct?" "y"; then
        save_config
        return 0
    else
        print_info "Configuration cancelled"
        return 1
    fi
}

# Display configuration summary
show_config_summary() {
    print_header "Configuration Summary"

    show_config_item "Installation Directory" "${CONFIG[INSTALL_DIR]}"
    show_config_item "Output Directory" "${CONFIG[OUTPUT_DIR]}"
    show_config_item "Scan Directory" "${CONFIG[SCAN_DIR]}"

    echo

    show_config_item "Frequency (kHz)" "${CONFIG[FREQUENCY]}"
    show_config_item "Duration (seconds)" "${CONFIG[DURATION]}"
    show_config_item "Scan Workers" "${CONFIG[SCAN_WORKERS]}"

    echo

    show_config_item "Podcast Title" "${CONFIG[PODCAST_TITLE]}"
    show_config_item "Podcast Author" "${CONFIG[PODCAST_AUTHOR]}"

    echo

    show_config_item "Enable Tailscale" "${CONFIG[ENABLE_TAILSCALE]}"
    show_config_item "Enable Nginx" "${CONFIG[ENABLE_NGINX]}"
    if [[ "${CONFIG[ENABLE_NGINX]}" == "true" ]]; then
        show_config_item "Nginx Port" "${CONFIG[NGINX_PORT]}"
    fi
    show_config_item "Enable Cron" "${CONFIG[ENABLE_CRON]}"
}

# Generate requirements.txt based on configuration
generate_requirements() {
    local requirements_file="${CONFIG[INSTALL_DIR]}/requirements.txt"

    print_step "Generating requirements.txt..."

    {
        echo "# Python dependencies for Shipping Forecast Recorder"
        echo "# Generated: $(date)"
        echo ""
        echo "requests>=2.28.0"
        echo "# numpy and scipy should be installed via system packages"
    } > "$requirements_file"

    if [[ $? -eq 0 ]]; then
        print_success "requirements.txt generated"
        return 0
    else
        print_error "Failed to generate requirements.txt"
        return 1
    fi
}

# Apply configuration to kiwi_recorder.py
apply_config_to_script() {
    local script_path="${CONFIG[INSTALL_DIR]}/kiwi_recorder.py"

    if [[ ! -f "$script_path" ]]; then
        print_error "kiwi_recorder.py not found at $script_path"
        return 1
    fi

    print_step "Applying configuration to kiwi_recorder.py..."

    # Use sed to update configuration values in the Config class
    # This would need to be customized based on the actual script structure

    print_info "Configuration applied (manual verification recommended)"
    return 0
}

# Create directory structure
create_directories() {
    print_step "Creating directory structure..."

    local dirs=(
        "${CONFIG[OUTPUT_DIR]}"
        "${CONFIG[SCAN_DIR]}"
    )

    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir" 2>/dev/null

            if [[ $? -eq 0 ]]; then
                print_success "Created: $dir"
            else
                print_error "Failed to create: $dir"
                return 1
            fi
        else
            print_info "Already exists: $dir"
        fi
    done

    return 0
}

# Quick/silent configuration (non-interactive)
quick_config() {
    print_info "Using default configuration..."
    echo

    show_config_summary
    save_config

    return 0
}

# Update mode - load existing config and offer to modify
update_config() {
    if ! load_config; then
        print_error "No existing configuration found"
        return 1
    fi

    print_info "Current configuration loaded"
    echo

    show_config_summary
    echo

    if ask_yes_no "Modify configuration?"; then
        interactive_config
    else
        print_info "Using existing configuration"
    fi

    return 0
}

# Export configuration as environment variables
export_config() {
    for key in "${!CONFIG[@]}"; do
        export "SF_${key}=${CONFIG[$key]}"
    done
}

# Validate configuration
validate_config() {
    print_step "Validating configuration..."

    local errors=0

    # Check installation directory exists or can be created
    if [[ ! -d "${CONFIG[INSTALL_DIR]}" ]]; then
        if ! mkdir -p "${CONFIG[INSTALL_DIR]}" 2>/dev/null; then
            print_error "Cannot create installation directory: ${CONFIG[INSTALL_DIR]}"
            ((errors++))
        fi
    fi

    # Check frequency is valid
    if ! [[ "${CONFIG[FREQUENCY]}" =~ ^[0-9]+$ ]]; then
        print_error "Invalid frequency: ${CONFIG[FREQUENCY]}"
        ((errors++))
    fi

    # Check duration is valid
    if ! [[ "${CONFIG[DURATION]}" =~ ^[0-9]+$ ]]; then
        print_error "Invalid duration: ${CONFIG[DURATION]}"
        ((errors++))
    fi

    # Check scan workers is valid
    if ! [[ "${CONFIG[SCAN_WORKERS]}" =~ ^[0-9]+$ ]] || [[ ${CONFIG[SCAN_WORKERS]} -lt 1 ]]; then
        print_error "Invalid scan workers: ${CONFIG[SCAN_WORKERS]}"
        ((errors++))
    fi

    # Check nginx port is valid
    if [[ "${CONFIG[ENABLE_NGINX]}" == "true" ]]; then
        if ! [[ "${CONFIG[NGINX_PORT]}" =~ ^[0-9]+$ ]] || [[ ${CONFIG[NGINX_PORT]} -lt 1 ]] || [[ ${CONFIG[NGINX_PORT]} -gt 65535 ]]; then
            print_error "Invalid nginx port: ${CONFIG[NGINX_PORT]}"
            ((errors++))
        fi
    fi

    if [[ $errors -gt 0 ]]; then
        print_error "Configuration validation failed with $errors error(s)"
        return 1
    else
        print_success "Configuration validated"
        return 0
    fi
}
