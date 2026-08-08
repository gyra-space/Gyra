#!/bin/bash

# Gyra Quick Start Script
# This script starts Gyra server with zero configuration
# Automatically detects OS and adapts startup behavior
# Default: daemon mode (background)
# Use -f/--foreground for foreground mode

set -e

# Parse arguments
DAEMON_MODE=true
EXTRA_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--foreground)
            DAEMON_MODE=false
            shift
            ;;
        -h|--help)
            echo "Usage: ./start.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -f, --foreground    Run in foreground mode (default: daemon)"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./start.sh              # Start in daemon mode (background)"
            echo "  ./start.sh -f           # Start in foreground mode"
            echo "  ./stop.sh               # Stop the server"
            exit 0
            ;;
        *)
            EXTRA_ARGS="$EXTRA_ARGS $1"
            shift
            ;;
    esac
done

# Auto-detect system environment and setup GYRA_HOME
setup_gyra_env() {
    local os_type
    os_type=$(uname -s | tr '[:upper:]' '[:lower:]')

    echo "  Platform: $os_type ($(uname -m))"

    # If GYRA_HOME already set by user, use it directly
    if [ -n "${GYRA_HOME:-}" ]; then
        mkdir -p "$GYRA_HOME" 2>/dev/null || true
        echo "  Config:   $GYRA_HOME (GYRA_HOME)"
        export GYRA_HOME
        return 0
    fi

    # Try default ~/.gyra
    local default_home="${HOME:-}/.gyra"
    if [ -n "${HOME:-}" ] && mkdir -p "$default_home" 2>/dev/null; then
        export GYRA_HOME="$default_home"
        echo "  Config:   $GYRA_HOME"
        return 0
    fi

    # Fallback for Linux servers without writable HOME
    echo ""
    echo "  WARNING: HOME directory not writable, auto-selecting GYRA_HOME..."
    for candidate in "/opt/gyra" "/var/lib/gyra" "/tmp/gyra"; do
        if mkdir -p "$candidate" 2>/dev/null; then
            export GYRA_HOME="$candidate"
            echo "  Config:   $GYRA_HOME (auto-detected)"
            return 0
        fi
    done

    echo "  ERROR: Cannot find writable directory for config."
    echo "  Please set GYRA_HOME environment variable manually."
    echo "  Example: export GYRA_HOME=/your/path"
    exit 1
}

echo ""
echo "================================"
echo "  Gyra Server Quick Start"
echo "================================"

# Setup environment
setup_gyra_env

# Setup log directory
LOG_DIR="${GYRA_HOME}/logs"
mkdir -p "$LOG_DIR" 2>/dev/null || true
LOG_FILE="${LOG_DIR}/gyra.log"
PID_FILE="${LOG_DIR}/gyra.pid"

echo ""

# Check if virtual environment exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "  Activated virtual environment"
fi

echo ""
echo "  Service: http://localhost:7777"
echo "  Config:  ${GYRA_HOME}"
echo "  Logs:    ${LOG_FILE}"

if [ "$DAEMON_MODE" = true ]; then
    echo ""
    echo "  Mode:    Daemon (background)"
    echo ""
    echo "  After starting, you can:"
    echo "    1. Open http://localhost:7777 in your browser"
    echo "    2. Configure models through the web UI"
    echo "    3. View logs: tail -f ${LOG_FILE}"
    echo "    4. Stop server: ./stop.sh"
    echo ""
    echo "================================"
    echo ""
    
    # Check if already running
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$OLD_PID" ] && ps -p "$OLD_PID" > /dev/null 2>&1; then
            echo "ERROR: Gyra server already running (PID: $OLD_PID)"
            echo "       Stop it first with: ./stop.sh"
            exit 1
        fi
        rm -f "$PID_FILE"
    fi
    
    # Run the server in background
    echo "Starting Gyra server..."
    nohup gyra quickstart $EXTRA_ARGS > "$LOG_FILE" 2>&1 &
    SERVER_PID=$!
    
    # Save PID
    echo $SERVER_PID > "$PID_FILE"
    
    # Wait a moment and check if process started successfully
    sleep 2
    if ps -p "$SERVER_PID" > /dev/null 2>&1; then
        echo "✓ Gyra server started successfully"
        echo "  PID:     $SERVER_PID"
        echo ""
        echo "  Waiting for service to be ready..."
        sleep 3
        
        # Check if port is listening
        if lsof -ti:7777 > /dev/null 2>&1; then
            echo "✓ Service is ready at http://localhost:7777"
        else
            echo "⚠ Service may still be initializing, check logs:"
            echo "    tail -f ${LOG_FILE}"
        fi
    else
        echo "ERROR: Failed to start Gyra server"
        echo "       Check logs: ${LOG_FILE}"
        rm -f "$PID_FILE"
        exit 1
    fi
else
    echo ""
    echo "  Mode:    Foreground"
    echo ""
    echo "  After starting, you can:"
    echo "    1. Open http://localhost:7777 in your browser"
    echo "    2. Configure models through the web UI"
    echo "    3. All configurations will be saved automatically"
    echo ""
    echo "  Press Ctrl+C to stop the server"
    echo "================================"
    echo ""
    
    # Run the server in foreground
    gyra quickstart $EXTRA_ARGS
fi
