#!/bin/bash
# rollback.sh - Error handling and rollback functionality
# Part of installer v0.1

# Source dependencies
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
source "$SCRIPT_DIR/colors.sh"
source "$SCRIPT_DIR/ui.sh"

# Rollback state tracking
declare -g ROLLBACK_LOG="/tmp/shipping-forecast-rollback.log"
declare -a ROLLBACK_ACTIONS=()
declare -g INSTALLATION_STATE_FILE="/tmp/shipping-forecast-install.state"

# Initialize rollback system
init_rollback() {
    : > "$ROLLBACK_LOG"
    : > "$INSTALLATION_STATE_FILE"
    ROLLBACK_ACTIONS=()

    # Register exit trap
    trap 'on_exit' EXIT
    trap 'on_error' ERR

    print_info "Rollback system initialized"
}

# Log a rollback action
# Usage: log_rollback "action_type" "description" "rollback_command"
log_rollback() {
    local action_type="$1"
    local description="$2"
    local rollback_cmd="$3"

    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Add to array
    ROLLBACK_ACTIONS+=("$action_type|$description|$rollback_cmd")

    # Log to file
    echo "$timestamp|$action_type|$description|$rollback_cmd" >> "$ROLLBACK_LOG"
}

# Execute rollback
execute_rollback() {
    print_warning "Executing rollback..."
    echo

    local num_actions=${#ROLLBACK_ACTIONS[@]}

    if [[ $num_actions -eq 0 ]]; then
        print_info "No rollback actions to execute"
        return 0
    fi

    print_info "Rolling back $num_actions action(s)..."
    echo

    # Execute in reverse order
    for ((i=${num_actions}-1; i>=0; i--)); do
        IFS='|' read -r action_type description rollback_cmd <<< "${ROLLBACK_ACTIONS[$i]}"

        print_step "Rolling back: $description"

        if [[ -n "$rollback_cmd" ]]; then
            eval "$rollback_cmd" 2>&1 | tail -5

            if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
                print_success "Rolled back: $description"
            else
                print_warning "Failed to rollback: $description"
            fi
        fi
    done

    echo
    print_success "Rollback completed"
}

# Exit handler
on_exit() {
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        show_error_detail "Installation failed" "Exit code: $exit_code"

        if ask_yes_no "Attempt to rollback changes?"; then
            execute_rollback
        else
            print_warning "Rollback skipped - manual cleanup may be required"
        fi
    fi
}

# Error handler
on_error() {
    local line_number=$1
    print_error "Error occurred at line $line_number"
}

# Backup a file before modification
backup_file() {
    local file_path="$1"

    if [[ ! -f "$file_path" ]]; then
        return 0
    fi

    local backup_path="${file_path}.backup.$(date +%Y%m%d_%H%M%S)"

    cp "$file_path" "$backup_path" 2>/dev/null

    if [[ $? -eq 0 ]]; then
        print_info "Backed up: $file_path → $backup_path"
        log_rollback "FILE_BACKUP" "Backup of $file_path" "mv '$backup_path' '$file_path'"
        return 0
    else
        print_warning "Failed to backup: $file_path"
        return 1
    fi
}

# Track file creation
track_file_creation() {
    local file_path="$1"
    log_rollback "FILE_CREATE" "Created $file_path" "rm -f '$file_path'"
}

# Track directory creation
track_dir_creation() {
    local dir_path="$1"
    log_rollback "DIR_CREATE" "Created directory $dir_path" "rmdir '$dir_path' 2>/dev/null"
}

# Track package installation
track_package_install() {
    local package_name="$1"
    local pkg_manager="${2:-apt}"

    case "$pkg_manager" in
        apt)
            log_rollback "PKG_INSTALL" "Installed $package_name" "sudo apt-get remove -y '$package_name'"
            ;;
        dnf|yum)
            log_rollback "PKG_INSTALL" "Installed $package_name" "sudo $pkg_manager remove -y '$package_name'"
            ;;
        pacman)
            log_rollback "PKG_INSTALL" "Installed $package_name" "sudo pacman -R --noconfirm '$package_name'"
            ;;
        zypper)
            log_rollback "PKG_INSTALL" "Installed $package_name" "sudo zypper remove -y '$package_name'"
            ;;
    esac
}

# Track systemd service changes
track_service_start() {
    local service_name="$1"
    log_rollback "SERVICE_START" "Started service $service_name" "sudo systemctl stop '$service_name'"
}

track_service_enable() {
    local service_name="$1"
    log_rollback "SERVICE_ENABLE" "Enabled service $service_name" "sudo systemctl disable '$service_name'"
}

# Track cron job changes
track_cron_add() {
    local cron_entry="$1"

    # Save current crontab
    local backup_cron="/tmp/crontab.backup.$(date +%Y%m%d_%H%M%S)"
    crontab -l > "$backup_cron" 2>/dev/null

    log_rollback "CRON_ADD" "Added cron job" "crontab '$backup_cron'"
}

# Track git clone
track_git_clone() {
    local repo_dir="$1"
    log_rollback "GIT_CLONE" "Cloned repository to $repo_dir" "rm -rf '$repo_dir'"
}

# Save installation state
save_state() {
    local stage="$1"
    local status="$2"

    echo "$stage|$status|$(date '+%Y-%m-%d %H:%M:%S')" >> "$INSTALLATION_STATE_FILE"
}

# Load installation state
load_state() {
    if [[ -f "$INSTALLATION_STATE_FILE" ]]; then
        cat "$INSTALLATION_STATE_FILE"
    fi
}

# Check if stage completed successfully
is_stage_complete() {
    local stage="$1"

    if [[ -f "$INSTALLATION_STATE_FILE" ]]; then
        grep -q "^${stage}|success|" "$INSTALLATION_STATE_FILE"
        return $?
    fi

    return 1
}

# Mark stage as complete
mark_stage_complete() {
    local stage="$1"
    save_state "$stage" "success"
    print_success "Stage $stage completed"
}

# Mark stage as failed
mark_stage_failed() {
    local stage="$1"
    local error_msg="$2"

    save_state "$stage" "failed"
    print_error "Stage $stage failed: $error_msg"
}

# Resume installation from failed state
can_resume() {
    [[ -f "$INSTALLATION_STATE_FILE" ]] && [[ -s "$INSTALLATION_STATE_FILE" ]]
}

get_last_completed_stage() {
    if can_resume; then
        grep "|success|" "$INSTALLATION_STATE_FILE" | tail -1 | cut -d'|' -f1
    fi
}

# Clean up rollback system
cleanup_rollback() {
    print_step "Cleaning up installation artifacts..."

    rm -f "$ROLLBACK_LOG"
    rm -f "$INSTALLATION_STATE_FILE"

    print_success "Cleanup complete"
}

# Disable rollback (for successful installations)
disable_rollback() {
    trap - EXIT ERR
    print_info "Rollback system disabled (installation successful)"
}

# Manual rollback trigger
manual_rollback() {
    print_warning "Manual rollback requested"

    if [[ ! -f "$ROLLBACK_LOG" ]]; then
        print_error "No rollback log found"
        return 1
    fi

    # Show rollback log
    print_info "Rollback log:"
    cat "$ROLLBACK_LOG"
    echo

    if ask_yes_no "Execute rollback?"; then
        # Reconstruct rollback actions from log
        ROLLBACK_ACTIONS=()
        while IFS='|' read -r timestamp action_type description rollback_cmd; do
            ROLLBACK_ACTIONS+=("$action_type|$description|$rollback_cmd")
        done < "$ROLLBACK_LOG"

        execute_rollback
    else
        print_info "Rollback cancelled"
    fi
}

# Dry-run mode - show what would be done without executing
enable_dry_run() {
    export DRY_RUN=true
    print_warning "DRY-RUN MODE ENABLED - No changes will be made"
}

# Execute command with dry-run support
dry_run_execute() {
    local description="$1"
    local command="$2"

    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        print_info "[DRY-RUN] Would execute: $description"
        show_code "$command"
        return 0
    else
        print_step "$description"
        eval "$command"
        return $?
    fi
}

# Create installation marker
create_install_marker() {
    local marker_file="/home/$USER/.shipping-forecast-installed"

    {
        echo "# Shipping Forecast Recorder Installation Marker"
        echo "INSTALLED_DATE=$(date '+%Y-%m-%d %H:%M:%S')"
        echo "INSTALLED_BY=$USER"
        echo "INSTALLER_VERSION=0.1"
        echo "HOSTNAME=$(hostname)"
    } > "$marker_file"

    track_file_creation "$marker_file"

    print_success "Installation marker created"
}

# Remove installation marker
remove_install_marker() {
    local marker_file="/home/$USER/.shipping-forecast-installed"

    if [[ -f "$marker_file" ]]; then
        rm -f "$marker_file"
        print_info "Installation marker removed"
    fi
}
