#!/bin/bash
# tailscale.sh - Tailscale authentication and configuration
# Part of installer v0.1

# Source dependencies
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "$SCRIPT_DIR/colors.sh"
source "$SCRIPT_DIR/ui.sh"

# Check if Tailscale is installed
check_tailscale() {
    command -v tailscale &>/dev/null
}

# Check if Tailscale is authenticated
is_tailscale_authenticated() {
    if ! check_tailscale; then
        return 1
    fi

    tailscale status &>/dev/null
    return $?
}

# Get Tailscale authentication URL
get_auth_url() {
    # Start tailscale and capture the auth URL
    local auth_output=$(sudo tailscale up 2>&1)

    # Extract URL from output
    local auth_url=$(echo "$auth_output" | grep -oP 'https://login\.tailscale\.com/[^ ]+')

    echo "$auth_url"
}

# Generate QR code from URL (using qrencode if available, or ASCII art)
generate_qr_code() {
    local url="$1"

    if command -v qrencode &>/dev/null; then
        # Use qrencode for better QR code
        qrencode -t ANSIUTF8 "$url"
    else
        # Fallback: ASCII QR code using curl
        curl -s "https://qrenco.de/${url}" 2>/dev/null || {
            print_warning "Could not generate QR code"
            return 1
        }
    fi
}

# Interactive Tailscale setup
setup_tailscale() {
    show_stage 8 "Tailscale Setup"

    print_info "Setting up Tailscale for public access..."
    echo

    # Check if already authenticated
    if is_tailscale_authenticated; then
        local ts_status=$(tailscale status --json 2>/dev/null | grep -oP '"Self":\s*{[^}]*"DNSName":\s*"\K[^"]+' || echo "connected")
        print_success "Tailscale already authenticated: $ts_status"

        if ask_yes_no "Reconfigure Tailscale?"; then
            sudo tailscale down
        else
            print_info "Using existing Tailscale configuration"
            return 0
        fi
    fi

    # Start Tailscale and get auth URL
    print_step "Starting Tailscale authentication..."
    echo

    local auth_url=$(get_auth_url)

    if [[ -z "$auth_url" ]]; then
        print_error "Failed to get Tailscale authentication URL"
        return 1
    fi

    # Display authentication options
    print_notice "Tailscale Authentication" "Choose your authentication method"
    echo

    local auth_method=$(show_menu "Authentication Method" \
        "Open browser automatically" \
        "Display QR code for mobile" \
        "Show URL for manual entry")

    echo

    case "$auth_method" in
        "Open browser automatically")
            print_step "Opening browser..."
            if command -v xdg-open &>/dev/null; then
                xdg-open "$auth_url" &>/dev/null &
            elif command -v open &>/dev/null; then
                open "$auth_url" &>/dev/null &
            else
                print_warning "Could not open browser automatically"
                print_info "Please open this URL manually:"
                show_code "$auth_url"
            fi
            ;;

        "Display QR code for mobile")
            echo
            print_info "Scan this QR code with your mobile device:"
            echo
            generate_qr_code "$auth_url"
            echo
            print_info "Or visit: $auth_url"
            ;;

        "Show URL for manual entry")
            echo
            print_info "Please visit this URL to authenticate:"
            show_code "$auth_url"
            ;;
    esac

    echo
    print_step "Waiting for authentication..."

    # Wait for authentication (with timeout)
    local timeout=300  # 5 minutes
    local elapsed=0

    while [[ $elapsed -lt $timeout ]]; do
        if is_tailscale_authenticated; then
            echo
            print_success "Tailscale authenticated successfully!"
            break
        fi

        sleep 2
        ((elapsed += 2))

        # Show progress
        if [[ $((elapsed % 10)) -eq 0 ]]; then
            printf "\r${MUTED_GRAY}Waiting... ${elapsed}s / ${timeout}s${RESET}"
        fi
    done

    if [[ $elapsed -ge $timeout ]]; then
        echo
        print_error "Authentication timeout"
        return 1
    fi

    # Get Tailscale information
    local ts_ip=$(tailscale ip -4 2>/dev/null | head -1)
    local ts_hostname=$(tailscale status --json 2>/dev/null | grep -oP '"HostName":\s*"\K[^"]+' | head -1)

    echo
    print_success "Tailscale IP: $ts_ip"
    print_success "Tailscale hostname: $ts_hostname"

    # Store Tailscale info in config
    export TAILSCALE_IP="$ts_ip"
    export TAILSCALE_HOSTNAME="$ts_hostname"

    return 0
}

# Configure Tailscale funnel for public access
setup_tailscale_funnel() {
    local port="${1:-8080}"

    print_step "Setting up Tailscale funnel for public access..."
    echo

    if ! is_tailscale_authenticated; then
        print_error "Tailscale not authenticated"
        return 1
    fi

    # Enable HTTPS
    print_step "Enabling HTTPS on Tailscale..."
    sudo tailscale cert $(tailscale status --json 2>/dev/null | grep -oP '"DNSName":\s*"\K[^"]+' | head -1) 2>&1 | tail -5

    # Start funnel
    print_step "Starting Tailscale funnel on port $port..."
    sudo tailscale funnel --bg $port 2>&1 | tail -5

    if [[ $? -eq 0 ]]; then
        print_success "Tailscale funnel enabled"

        # Get public URL
        local funnel_url=$(tailscale funnel status 2>/dev/null | grep -oP 'https://[^ ]+' | head -1)

        if [[ -n "$funnel_url" ]]; then
            print_success "Public URL: $funnel_url"
            export TAILSCALE_FUNNEL_URL="$funnel_url"

            # Update config with feed URL
            CONFIG[FEED_URL]="${funnel_url}/feed.xml"
        fi

        return 0
    else
        print_error "Failed to enable Tailscale funnel"
        return 1
    fi
}

# Create systemd service for Tailscale funnel
create_funnel_service() {
    local port="${1:-8080}"
    local service_file="/etc/systemd/system/shipping-forecast-funnel.service"

    print_step "Creating Tailscale funnel service..."

    sudo tee "$service_file" > /dev/null <<EOF
[Unit]
Description=Tailscale Funnel for Shipping Forecast
After=tailscaled.service nginx.service
Requires=tailscaled.service

[Service]
Type=oneshot
ExecStart=/usr/bin/tailscale funnel --bg ${port}
RemainAfterExit=yes
User=root

[Install]
WantedBy=multi-user.target
EOF

    if [[ $? -ne 0 ]]; then
        print_error "Failed to create funnel service"
        return 1
    fi

    # Enable and start service
    print_step "Enabling funnel service..."
    sudo systemctl daemon-reload
    sudo systemctl enable shipping-forecast-funnel.service
    sudo systemctl start shipping-forecast-funnel.service

    if [[ $? -eq 0 ]]; then
        print_success "Tailscale funnel service created and started"
        track_service_enable "shipping-forecast-funnel"
        track_service_start "shipping-forecast-funnel"
        return 0
    else
        print_error "Failed to start funnel service"
        return 1
    fi
}

# Display Tailscale status and public URLs
show_tailscale_info() {
    print_header "Tailscale Information"

    if ! is_tailscale_authenticated; then
        print_warning "Tailscale not authenticated"
        return 1
    fi

    # Get status
    local ts_ip=$(tailscale ip -4 2>/dev/null | head -1)
    local ts_hostname=$(tailscale status --json 2>/dev/null | grep -oP '"HostName":\s*"\K[^"]+' | head -1)
    local ts_dns=$(tailscale status --json 2>/dev/null | grep -oP '"DNSName":\s*"\K[^"]+' | head -1)

    show_config_item "Tailscale IP" "$ts_ip"
    show_config_item "Hostname" "$ts_hostname"
    show_config_item "DNS Name" "$ts_dns"

    # Check if funnel is active
    if sudo tailscale funnel status &>/dev/null; then
        local funnel_url=$(tailscale funnel status 2>/dev/null | grep -oP 'https://[^ ]+' | head -1)
        show_config_item "Public URL" "$funnel_url"
        show_config_item "Feed URL" "${funnel_url}/feed.xml"
    else
        show_config_item "Funnel Status" "Not enabled"
    fi

    echo
}

# Disable Tailscale funnel
disable_tailscale_funnel() {
    print_step "Disabling Tailscale funnel..."

    # Stop service if it exists
    if systemctl is-active --quiet shipping-forecast-funnel.service; then
        sudo systemctl stop shipping-forecast-funnel.service
        sudo systemctl disable shipping-forecast-funnel.service
    fi

    # Disable funnel
    sudo tailscale funnel --bg=false 2>&1 | tail -5

    print_success "Tailscale funnel disabled"
}

# Check Tailscale service status
check_tailscale_service() {
    if systemctl is-active --quiet tailscaled; then
        print_success "Tailscale service is running"
        return 0
    else
        print_warning "Tailscale service is not running"

        if ask_yes_no "Start Tailscale service?"; then
            sudo systemctl start tailscaled
            sudo systemctl enable tailscaled

            if systemctl is-active --quiet tailscaled; then
                print_success "Tailscale service started"
                return 0
            else
                print_error "Failed to start Tailscale service"
                return 1
            fi
        fi
        return 1
    fi
}

# Full Tailscale setup workflow
full_tailscale_setup() {
    local nginx_port="${1:-8080}"

    # Check service
    if ! check_tailscale_service; then
        return 1
    fi

    # Authenticate
    if ! setup_tailscale; then
        return 1
    fi

    echo

    # Ask about funnel
    if ask_yes_no "Enable Tailscale funnel for public access?"; then
        if ! setup_tailscale_funnel "$nginx_port"; then
            print_warning "Funnel setup failed, but Tailscale is still configured for private access"
        else
            # Create systemd service
            if ask_yes_no "Create systemd service for automatic funnel startup?"; then
                create_funnel_service "$nginx_port"
            fi
        fi
    else
        print_info "Tailscale configured for private network access only"
    fi

    echo
    show_tailscale_info

    return 0
}
