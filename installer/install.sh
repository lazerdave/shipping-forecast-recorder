#!/bin/bash
# install.sh - Shipping Forecast Recorder Installer v0.1
# Interactive installer for BBC Radio 4 Shipping Forecast automated recorder
# https://github.com/yourusername/shipping-forecast-recorder

set -e  # Exit on error (will be caught by rollback system)

# Get script directory
INSTALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$INSTALLER_DIR/lib"
PROJECT_DIR="$(dirname "$INSTALLER_DIR")"

# Source all libraries
source "$LIB_DIR/colors.sh"
source "$LIB_DIR/ui.sh"
source "$LIB_DIR/checks.sh"
source "$LIB_DIR/config.sh"
source "$LIB_DIR/packages.sh"
source "$LIB_DIR/rollback.sh"
source "$LIB_DIR/tailscale.sh"

# Installation modes
MODE="interactive"  # interactive, silent, update, dry-run, diagnose

# Parse command-line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --silent)
                MODE="silent"
                shift
                ;;
            --update)
                MODE="update"
                shift
                ;;
            --dry-run)
                MODE="dry-run"
                enable_dry_run
                shift
                ;;
            --diagnose)
                MODE="diagnose"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Show help
show_help() {
    cat << EOF
Shipping Forecast Recorder Installer v0.1

Usage: $0 [OPTIONS]

OPTIONS:
    --silent        Non-interactive installation with default settings
    --update        Update existing installation
    --dry-run       Show what would be done without making changes
    --diagnose      Run diagnostic checks only
    --help, -h      Show this help message

EXAMPLES:
    $0                      # Interactive installation
    $0 --silent             # Silent installation
    $0 --update             # Update existing installation
    $0 --dry-run            # Preview changes without installing

DESCRIPTION:
    This installer sets up the Shipping Forecast Recorder system for
    automated recording of BBC Radio 4 Shipping Forecast broadcasts
    at 198 kHz longwave via the KiwiSDR network.

    The installation includes:
    - KiwiSDR client for network SDR access
    - Python environment with dependencies
    - Nginx HTTP server for podcast feed
    - Tailscale for public internet access (optional)
    - Cron scheduling for automated recordings
    - Anthem detection via sonic fingerprinting

For more information, visit: https://github.com/yourusername/shipping-forecast-recorder

EOF
}

# Stage 1: Pre-flight Checks (already implemented in lib/checks.sh)

# Stage 2: User Configuration (already implemented in lib/config.sh)

# Stage 3 & 4: System and Python Dependencies (already implemented in lib/packages.sh)

# Stage 5: KiwiSDR Client Installation
stage_kiwi_client() {
    show_stage 5 "KiwiSDR Client"

    if ! install_kiwi_client "${CONFIG[INSTALL_DIR]}"; then
        mark_stage_failed "kiwi_client" "Failed to install KiwiSDR client"
        return 1
    fi

    track_git_clone "${CONFIG[KIWI_CLIENT_DIR]}"
    mark_stage_complete "kiwi_client"
    return 0
}

# Stage 6: Application Setup
stage_application() {
    show_stage 6 "Application Setup"

    print_info "Installing Shipping Forecast Recorder application..."
    echo

    # Copy kiwi_recorder.py from project
    local source_script="$PROJECT_DIR/kiwi_recorder.py"
    local dest_script="${CONFIG[INSTALL_DIR]}/kiwi_recorder.py"

    if [[ ! -f "$source_script" ]]; then
        print_error "kiwi_recorder.py not found in project directory"
        mark_stage_failed "application" "Source script not found"
        return 1
    fi

    # Backup existing if present
    if [[ -f "$dest_script" ]]; then
        backup_file "$dest_script"
    fi

    # Copy script
    print_step "Installing kiwi_recorder.py..."
    cp "$source_script" "$dest_script"
    chmod +x "$dest_script"

    if [[ $? -eq 0 ]]; then
        print_success "kiwi_recorder.py installed"
        track_file_creation "$dest_script"
    else
        print_error "Failed to install kiwi_recorder.py"
        return 1
    fi

    # Copy anthem template
    local source_anthem="$PROJECT_DIR/anthem_template.wav"
    local dest_anthem="${CONFIG[INSTALL_DIR]}/anthem_template.wav"

    if [[ -f "$source_anthem" ]]; then
        print_step "Installing anthem template..."
        cp "$source_anthem" "$dest_anthem"
        track_file_creation "$dest_anthem"
        print_success "Anthem template installed"
    else
        print_warning "anthem_template.wav not found (will need to be created later)"
    fi

    # Copy artwork if available
    local source_artwork="$PROJECT_DIR/artwork.jpg"
    local dest_artwork="${CONFIG[OUTPUT_DIR]}/artwork.jpg"

    if [[ -f "$source_artwork" ]]; then
        print_step "Installing podcast artwork..."
        mkdir -p "${CONFIG[OUTPUT_DIR]}"
        cp "$source_artwork" "$dest_artwork"
        track_file_creation "$dest_artwork"
        print_success "Artwork installed"
    fi

    # Create directories
    create_directories

    echo
    mark_stage_complete "application"
    return 0
}

# Stage 7: Nginx Setup
stage_nginx() {
    show_stage 7 "Nginx Configuration"

    if [[ "${CONFIG[ENABLE_NGINX]}" != "true" ]]; then
        print_info "Nginx disabled in configuration, skipping..."
        mark_stage_complete "nginx"
        return 0
    fi

    print_info "Configuring nginx HTTP server..."
    echo

    local nginx_conf="/etc/nginx/sites-available/shipping-forecast"
    local nginx_enabled="/etc/nginx/sites-enabled/shipping-forecast"

    # Backup existing configuration
    if [[ -f "$nginx_conf" ]]; then
        backup_file "$nginx_conf"
    fi

    # Create nginx configuration
    print_step "Creating nginx configuration..."

    sudo tee "$nginx_conf" > /dev/null <<EOF
server {
    listen ${CONFIG[NGINX_PORT]};
    listen [::]:${CONFIG[NGINX_PORT]};

    server_name _;

    root ${CONFIG[OUTPUT_DIR]};
    index feed.xml;

    # Enable directory listing
    autoindex on;
    autoindex_exact_size off;
    autoindex_localtime on;

    # CORS headers for podcast compatibility
    add_header Access-Control-Allow-Origin *;

    # Proper MIME types
    types {
        audio/mpeg mp3;
        audio/wav wav;
        application/rss+xml xml;
        image/jpeg jpg jpeg;
    }

    # Enable Range requests for streaming
    location / {
        try_files \$uri \$uri/ =404;
    }

    # Feed endpoint
    location = /feed.xml {
        try_files /feed.xml =404;
    }

    # Audio files
    location ~* \.(mp3|wav)$ {
        add_header Content-Disposition 'attachment';
        add_header Cache-Control 'public, max-age=86400';
    }
}
EOF

    if [[ $? -ne 0 ]]; then
        print_error "Failed to create nginx configuration"
        mark_stage_failed "nginx" "Configuration creation failed"
        return 1
    fi

    track_file_creation "$nginx_conf"
    print_success "Nginx configuration created"

    # Enable site
    print_step "Enabling nginx site..."
    if [[ ! -L "$nginx_enabled" ]]; then
        sudo ln -s "$nginx_conf" "$nginx_enabled"
        track_file_creation "$nginx_enabled"
    fi

    # Test configuration
    print_step "Testing nginx configuration..."
    if sudo nginx -t 2>&1 | tail -2; then
        print_success "Nginx configuration valid"
    else
        print_error "Nginx configuration test failed"
        return 1
    fi

    # Restart nginx
    print_step "Restarting nginx..."
    sudo systemctl restart nginx

    if [[ $? -eq 0 ]]; then
        print_success "Nginx restarted"
        track_service_start "nginx"
    else
        print_error "Failed to restart nginx"
        return 1
    fi

    # Enable nginx on boot
    sudo systemctl enable nginx
    track_service_enable "nginx"

    echo
    mark_stage_complete "nginx"
    return 0
}

# Stage 8: Tailscale Setup (already implemented in lib/tailscale.sh)
stage_tailscale() {
    if [[ "${CONFIG[ENABLE_TAILSCALE]}" != "true" ]]; then
        print_info "Tailscale disabled in configuration, skipping..."
        mark_stage_complete "tailscale"
        return 0
    fi

    if ! full_tailscale_setup "${CONFIG[NGINX_PORT]}"; then
        mark_stage_failed "tailscale" "Tailscale setup failed"
        return 1
    fi

    mark_stage_complete "tailscale"
    return 0
}

# Stage 9: Cron Scheduling
stage_cron() {
    show_stage 9 "Cron Scheduling"

    if [[ "${CONFIG[ENABLE_CRON]}" != "true" ]]; then
        print_info "Cron scheduling disabled in configuration, skipping..."
        mark_stage_complete "cron"
        return 0
    fi

    print_info "Setting up automated scheduling..."
    echo

    # Use the setup command from kiwi_recorder.py
    print_step "Running cron setup..."

    local kiwi_script="${CONFIG[INSTALL_DIR]}/kiwi_recorder.py"

    if [[ ! -f "$kiwi_script" ]]; then
        print_error "kiwi_recorder.py not found"
        return 1
    fi

    # Backup current crontab
    track_cron_add "shipping-forecast"

    # Run setup
    python3 "$kiwi_script" setup 2>&1 | tail -10

    if [[ $? -eq 0 ]]; then
        print_success "Cron jobs configured"

        # Show configured jobs
        echo
        print_info "Configured cron jobs:"
        crontab -l | grep "kiwi_recorder.py"
    else
        print_error "Failed to configure cron jobs"
        return 1
    fi

    echo
    mark_stage_complete "cron"
    return 0
}

# Stage 10: Validation (already implemented in lib/checks.sh)

# Main installation workflow
main() {
    # Parse arguments
    parse_args "$@"

    # Show welcome
    show_welcome

    # Initialize rollback system
    init_rollback

    # Handle different modes
    case "$MODE" in
        diagnose)
            # Run diagnostics only
            run_preflight_checks
            exit $?
            ;;

        update)
            # Update mode
            print_info "Running in UPDATE mode"
            echo
            if ! update_config; then
                print_error "Update failed"
                exit 1
            fi
            ;;

        silent)
            # Silent mode - use defaults
            print_info "Running in SILENT mode (non-interactive)"
            echo
            ;;

        dry-run)
            # Dry-run mode
            print_warning "Running in DRY-RUN mode (no changes will be made)"
            echo
            ;;
    esac

    # Stage 1: Pre-flight Checks
    if ! run_preflight_checks; then
        print_error "Pre-flight checks failed"
        exit 1
    fi

    pause

    # Stage 2: Configuration
    if [[ "$MODE" == "silent" ]]; then
        quick_config
    elif [[ "$MODE" != "update" ]]; then
        if ! interactive_config; then
            print_error "Configuration failed"
            exit 1
        fi
    fi

    if ! validate_config; then
        print_error "Invalid configuration"
        exit 1
    fi

    pause

    # Stage 3: System Dependencies
    if ! install_system_deps; then
        mark_stage_failed "system_deps" "Failed to install system dependencies"
        exit 1
    fi
    mark_stage_complete "system_deps"

    pause

    # Stage 4: Python Dependencies
    generate_requirements
    if ! install_python_deps "${CONFIG[INSTALL_DIR]}/requirements.txt"; then
        mark_stage_failed "python_deps" "Failed to install Python dependencies"
        exit 1
    fi
    mark_stage_complete "python_deps"

    pause

    # Install Tailscale if enabled
    if [[ "${CONFIG[ENABLE_TAILSCALE]}" == "true" ]]; then
        if ! install_tailscale; then
            print_warning "Tailscale installation failed (will skip Tailscale setup)"
            CONFIG[ENABLE_TAILSCALE]="false"
        fi
    fi

    pause

    # Stage 5: KiwiSDR Client
    if ! stage_kiwi_client; then
        exit 1
    fi

    pause

    # Stage 6: Application
    if ! stage_application; then
        exit 1
    fi

    pause

    # Stage 7: Nginx
    if ! stage_nginx; then
        exit 1
    fi

    pause

    # Stage 8: Tailscale
    if ! stage_tailscale; then
        print_warning "Tailscale setup failed (continuing anyway)"
    fi

    pause

    # Stage 9: Cron
    if ! stage_cron; then
        exit 1
    fi

    pause

    # Stage 10: Validation
    validate_installation
    local validation_result=$?

    # Create installation marker
    create_install_marker

    # Success!
    disable_rollback
    cleanup_rollback

    show_completion "true"

    # Display final information
    print_header "Installation Complete!"
    echo

    if [[ "${CONFIG[ENABLE_NGINX]}" == "true" ]]; then
        local local_url="http://$(hostname -I | awk '{print $1}'):${CONFIG[NGINX_PORT]}/feed.xml"
        show_config_item "Local Feed URL" "$local_url"
    fi

    if [[ "${CONFIG[ENABLE_TAILSCALE]}" == "true" ]] && [[ -n "${TAILSCALE_FUNNEL_URL:-}" ]]; then
        show_config_item "Public Feed URL" "${TAILSCALE_FUNNEL_URL}/feed.xml"
    fi

    echo
    show_config_item "Output Directory" "${CONFIG[OUTPUT_DIR]}"
    show_config_item "Configuration File" "$CONFIG_FILE"
    show_config_item "Main Script" "${CONFIG[INSTALL_DIR]}/kiwi_recorder.py"

    echo

    print_notice "Next Steps" "$(cat <<EOF
1. Test recording:  python3 ${CONFIG[INSTALL_DIR]}/kiwi_recorder.py record
2. Generate feed:   python3 ${CONFIG[INSTALL_DIR]}/kiwi_recorder.py feed
3. Run a scan:      python3 ${CONFIG[INSTALL_DIR]}/kiwi_recorder.py scan
4. Check logs:      tail -f ~/Shipping_Forecast_SDR_Recordings.log
EOF
)"

    echo

    if [[ $validation_result -ne 0 ]]; then
        print_warning "Installation completed with warnings - manual verification recommended"
        exit 2
    fi

    print_success "All done! Your Shipping Forecast Recorder is ready."
    echo
}

# Run main installation
main "$@"
