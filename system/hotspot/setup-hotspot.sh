#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# WiFi Hotspot Setup Script for Jetson Orin Nano Field Kit
# =============================================================================
# Creates a WiFi access point on a secondary adapter while maintaining
# internet connectivity through the primary WiFi connection.
#
# Requirements:
#   - Two WiFi adapters (one connected to internet, one for AP)
#   - NetworkManager
#   - iptables
#   - avahi-daemon (for mDNS)
#
# Usage:
#   sudo ./setup-hotspot.sh [options]
#
# Options:
#   --ssid NAME       Hotspot SSID (default: JetsonFieldKit)
#   --password PASS   Hotspot password (default: fieldkit123)
#   --ap-interface IF Force specific interface for AP mode
#   --channel NUM     WiFi channel for AP (default: auto/1)
#   --persist         Save iptables rules to persist across reboots
#   --stop            Stop the hotspot and clean up
#   --status          Show current hotspot status
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Default configuration
HOTSPOT_SSID="${HOTSPOT_SSID:-JetsonFieldKit}"
HOTSPOT_PASSWORD="${HOTSPOT_PASSWORD:-fieldkit123}"
HOTSPOT_CHANNEL="${HOTSPOT_CHANNEL:-1}"
AP_INTERFACE="${AP_INTERFACE:-}"
PERSIST_RULES=false
ACTION="start"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ssid)
            HOTSPOT_SSID="$2"
            shift 2
            ;;
        --password)
            HOTSPOT_PASSWORD="$2"
            shift 2
            ;;
        --ap-interface)
            AP_INTERFACE="$2"
            shift 2
            ;;
        --channel)
            HOTSPOT_CHANNEL="$2"
            shift 2
            ;;
        --persist)
            PERSIST_RULES=true
            shift
            ;;
        --stop)
            ACTION="stop"
            shift
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        -h|--help)
            head -30 "$0" | tail -25
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Get all WiFi interfaces
get_wifi_interfaces() {
    iw dev 2>/dev/null | grep "Interface" | awk '{print $2}'
}

# Get USB WiFi interfaces (for hotspot AP mode)
# USB WiFi adapters are identified by their driver path containing "usb"
get_usb_wifi_interface() {
    for iface in $(get_wifi_interfaces); do
        local driver_path
        driver_path=$(readlink -f "/sys/class/net/$iface/device/driver" 2>/dev/null) || continue
        if [[ "$driver_path" == *"/usb/"* ]]; then
            echo "$iface"
            return 0
        fi
    done
    return 1
}

# Get the WiFi interface currently connected to a network (STA mode)
get_sta_interface() {
    nmcli -t -f DEVICE,TYPE,STATE device status 2>/dev/null | \
        grep "wifi:connected" | \
        cut -d: -f1 | \
        head -1
}

# Get available WiFi interface for AP (not connected)
get_available_ap_interface() {
    local sta_if="$1"
    for iface in $(get_wifi_interfaces); do
        if [ "$iface" != "$sta_if" ]; then
            # Check if it's not already running as AP
            local state
            state=$(nmcli -t -f DEVICE,STATE device status 2>/dev/null | grep "^${iface}:" | cut -d: -f2)
            if [ "$state" != "connected" ] || nmcli -t -f DEVICE,CONNECTION device status 2>/dev/null | grep "^${iface}:Hotspot"; then
                echo "$iface"
                return 0
            fi
        fi
    done
    return 1
}

# Get the IP subnet used by the hotspot
get_hotspot_subnet() {
    ip addr show "$1" 2>/dev/null | grep "inet " | awk '{print $2}' | head -1
}

# Show current status
show_status() {
    echo "=== WiFi Hotspot Status ==="
    echo ""

    echo "WiFi Interfaces:"
    iw dev 2>/dev/null | grep -E "Interface|ssid|type|channel" | sed 's/^/  /'
    echo ""

    echo "Network Manager Connections:"
    nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status 2>/dev/null | grep wifi | sed 's/^/  /'
    echo ""

    local hotspot_con
    hotspot_con=$(nmcli -t -f NAME,TYPE con show --active 2>/dev/null | grep "802-11-wireless" | grep -i hotspot | cut -d: -f1)
    if [ -n "$hotspot_con" ]; then
        echo "Active Hotspot: $hotspot_con"
        nmcli con show "$hotspot_con" 2>/dev/null | grep -E "802-11-wireless.ssid|ipv4.addresses" | sed 's/^/  /'
    else
        echo "No active hotspot found"
    fi
    echo ""

    echo "NAT Rules (POSTROUTING):"
    iptables -t nat -L POSTROUTING -n -v 2>/dev/null | grep -E "10.42|MASQ" | sed 's/^/  /' || echo "  None"
    echo ""

    echo "Avahi mDNS Status:"
    systemctl status avahi-daemon 2>/dev/null | grep -E "Active:|running \[" | sed 's/^/  /'
}

# Stop the hotspot
stop_hotspot() {
    log_info "Stopping hotspot..."

    # Find and deactivate hotspot connection
    local hotspot_con
    hotspot_con=$(nmcli -t -f NAME con show 2>/dev/null | grep -i hotspot | head -1)

    if [ -n "$hotspot_con" ]; then
        log_info "Deactivating connection: $hotspot_con"
        nmcli con down "$hotspot_con" 2>/dev/null || true
        nmcli con delete "$hotspot_con" 2>/dev/null || true
    fi

    # Remove iptables rules for hotspot subnet
    log_info "Cleaning up iptables rules..."
    iptables -t nat -D POSTROUTING -s 10.42.0.0/24 -j MASQUERADE 2>/dev/null || true

    # Clean up forward rules for any USB WiFi interface
    local usb_wifi
    usb_wifi=$(get_usb_wifi_interface) || true
    if [ -n "$usb_wifi" ]; then
        iptables -D FORWARD -i "$usb_wifi" -j ACCEPT 2>/dev/null || true
    fi
    iptables -D FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true

    # Clean up any rules mentioning 10.42.0.0
    while iptables -t nat -D POSTROUTING -s 10.42.0.0/24 -j MASQUERADE 2>/dev/null; do :; done

    log_info "Hotspot stopped"
}

# Setup NAT and forwarding rules
setup_nat() {
    local ap_if="$1"
    local sta_if="$2"
    local subnet="$3"

    log_info "Configuring NAT and forwarding..."

    # Enable IP forwarding
    echo 1 > /proc/sys/net/ipv4/ip_forward

    # Add NAT masquerade rule if not exists
    if ! iptables -t nat -C POSTROUTING -s "$subnet" -o "$sta_if" -j MASQUERADE 2>/dev/null; then
        iptables -t nat -A POSTROUTING -s "$subnet" -o "$sta_if" -j MASQUERADE
        log_info "Added NAT rule for $subnet -> $sta_if"
    fi

    # Add forwarding rules if not exists
    if ! iptables -C FORWARD -i "$ap_if" -o "$sta_if" -j ACCEPT 2>/dev/null; then
        iptables -A FORWARD -i "$ap_if" -o "$sta_if" -j ACCEPT
        log_info "Added forward rule: $ap_if -> $sta_if"
    fi

    if ! iptables -C FORWARD -i "$sta_if" -o "$ap_if" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null; then
        iptables -A FORWARD -i "$sta_if" -o "$ap_if" -m state --state RELATED,ESTABLISHED -j ACCEPT
        log_info "Added forward rule: $sta_if -> $ap_if (established)"
    fi

    # Persist rules if requested
    if [ "$PERSIST_RULES" = true ]; then
        if command -v netfilter-persistent &>/dev/null; then
            netfilter-persistent save
            log_info "iptables rules saved with netfilter-persistent"
        elif command -v iptables-save &>/dev/null; then
            iptables-save > /etc/iptables.rules
            log_info "iptables rules saved to /etc/iptables.rules"

            # Create restore script if it doesn't exist
            if [ ! -f /etc/network/if-pre-up.d/iptables ]; then
                cat > /etc/network/if-pre-up.d/iptables << 'IPTABLES_RESTORE'
#!/bin/sh
/sbin/iptables-restore < /etc/iptables.rules
IPTABLES_RESTORE
                chmod +x /etc/network/if-pre-up.d/iptables
                log_info "Created iptables restore script"
            fi
        fi

        # Make IP forwarding persistent
        if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf 2>/dev/null; then
            echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
            log_info "Made IP forwarding persistent in sysctl.conf"
        fi
    fi
}

# Restart avahi for mDNS
restart_avahi() {
    log_info "Restarting avahi-daemon for mDNS..."
    systemctl restart avahi-daemon
    sleep 2

    local hostname
    hostname=$(systemctl status avahi-daemon 2>/dev/null | grep "running \[" | sed 's/.*running \[\(.*\)\].*/\1/')
    if [ -n "$hostname" ]; then
        log_info "mDNS hostname: $hostname"
    fi
}

# Clean up any auto-created WiFi connections on the AP interface
cleanup_ap_interface() {
    local ap_if="$1"

    log_info "Cleaning up auto-created connections on $ap_if..."

    # Get all connections currently using the AP interface (except Hotspot)
    local connections
    connections=$(nmcli -t -f NAME,DEVICE con show --active 2>/dev/null | grep ":${ap_if}$" | cut -d: -f1 | grep -v "^Hotspot$") || true

    for conn in $connections; do
        log_info "  Disconnecting: $conn"
        nmcli con down "$conn" 2>/dev/null || true
    done

    # Delete any duplicate WiFi connections that might auto-connect on AP interface
    # These are typically created when NM auto-connects the USB adapter to known networks
    local all_wifi_connections
    all_wifi_connections=$(nmcli -t -f NAME,TYPE con show 2>/dev/null | grep ":802-11-wireless$" | cut -d: -f1) || true

    for conn in $all_wifi_connections; do
        # Skip the Hotspot connection
        if [ "$conn" = "Hotspot" ]; then
            continue
        fi

        # Check if this connection is bound to the AP interface
        local conn_interface
        conn_interface=$(nmcli -t -f connection.interface-name con show "$conn" 2>/dev/null | cut -d: -f2) || true

        if [ "$conn_interface" = "$ap_if" ]; then
            log_info "  Deleting connection bound to AP interface: $conn"
            nmcli con delete "$conn" 2>/dev/null || true
        fi

        # Also check for duplicate connections (e.g., "NetworkName 1", "NetworkName 2")
        if [[ "$conn" =~ [[:space:]][0-9]+$ ]]; then
            log_info "  Deleting duplicate connection: $conn"
            nmcli con delete "$conn" 2>/dev/null || true
        fi
    done
}

# Main setup function
setup_hotspot() {
    log_info "Setting up WiFi hotspot..."
    log_info "  SSID: $HOTSPOT_SSID"
    log_info "  Password: ${HOTSPOT_PASSWORD:0:3}***"

    # If AP_INTERFACE is specified, verify it exists first
    if [ -n "$AP_INTERFACE" ]; then
        if ! ip link show "$AP_INTERFACE" &>/dev/null; then
            log_warn "Specified AP interface '$AP_INTERFACE' not found"
            log_warn "USB WiFi adapter may not be connected - skipping hotspot setup"
            exit 0  # Exit gracefully, don't retry
        fi
        log_info "Using configured AP interface: $AP_INTERFACE"
    fi

    # Find STA interface (connected to internet) - optional
    local sta_if
    sta_if=$(get_sta_interface) || true

    if [ -z "$sta_if" ]; then
        log_warn "No WiFi interface connected to internet found"
        log_warn "Hotspot will run without internet sharing (local access only)"
    else
        log_info "STA interface (internet): $sta_if"
    fi

    # Find or use specified AP interface
    local ap_if
    if [ -n "$AP_INTERFACE" ]; then
        ap_if="$AP_INTERFACE"
        # Make sure we're not trying to use the same interface for both
        if [ "$ap_if" = "$sta_if" ]; then
            log_error "AP interface '$ap_if' is already used for internet connection"
            exit 1
        fi
    else
        # Auto-detect USB WiFi adapter for AP mode (only USB adapters allowed)
        ap_if=$(get_usb_wifi_interface) || true
        if [ -n "$ap_if" ]; then
            log_info "Auto-detected USB WiFi adapter: $ap_if"
        fi
    fi

    if [ -z "$ap_if" ]; then
        log_error "No USB WiFi adapter found for AP mode"
        log_error "Please connect a USB WiFi adapter"
        exit 1
    fi
    log_info "AP interface (hotspot): $ap_if"

    # Clean up any auto-created connections on the AP interface
    cleanup_ap_interface "$ap_if"

    # Check if hotspot already exists and is active
    local existing_hotspot
    existing_hotspot=$(nmcli -t -f DEVICE,CONNECTION device status 2>/dev/null | grep "^${ap_if}:" | cut -d: -f2)
    if [ "$existing_hotspot" = "Hotspot" ]; then
        log_warn "Hotspot already active on $ap_if"
        log_info "Use --stop to stop it first, or --status to see details"
        return 0
    fi

    # Stop any existing hotspot on this interface
    nmcli con down Hotspot 2>/dev/null || true
    nmcli con delete Hotspot 2>/dev/null || true

    # Create the hotspot
    log_info "Creating hotspot on $ap_if..."
    if ! nmcli device wifi hotspot ifname "$ap_if" ssid "$HOTSPOT_SSID" password "$HOTSPOT_PASSWORD"; then
        log_error "Failed to create hotspot"
        exit 1
    fi

    # Configure the Hotspot connection to auto-connect and be bound to this interface
    log_info "Configuring Hotspot for auto-connect on $ap_if..."
    nmcli con mod Hotspot connection.autoconnect yes 2>/dev/null || true
    nmcli con mod Hotspot connection.interface-name "$ap_if" 2>/dev/null || true
    nmcli con mod Hotspot connection.autoconnect-priority 100 2>/dev/null || true

    # Wait for interface to get IP
    sleep 3

    # Get the subnet assigned to the hotspot
    local subnet
    subnet=$(get_hotspot_subnet "$ap_if")
    if [ -z "$subnet" ]; then
        subnet="10.42.0.0/24"  # NetworkManager default
    fi
    log_info "Hotspot subnet: $subnet"

    # Setup NAT and forwarding only if internet connection is available
    if [ -n "$sta_if" ]; then
        setup_nat "$ap_if" "$sta_if" "$subnet"
    else
        log_warn "Skipping NAT setup - no internet connection available"
        log_info "Hotspot is running in local-only mode"
    fi

    # Restart avahi for clean mDNS
    restart_avahi

    echo ""
    log_info "=========================================="
    log_info "Hotspot setup complete!"
    log_info "=========================================="
    echo ""
    echo "  SSID:      $HOTSPOT_SSID"
    echo "  Password:  $HOTSPOT_PASSWORD"
    echo "  Gateway:   10.42.0.1"
    echo ""
    echo "  Clients can access:"
    echo "    - http://box.local (via mDNS)"
    echo "    - http://10.42.0.1"
    echo ""
}

# Main
check_root

case "$ACTION" in
    start)
        setup_hotspot
        ;;
    stop)
        stop_hotspot
        ;;
    status)
        show_status
        ;;
esac
