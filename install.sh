#!/bin/bash
set -e

# Gyra Installer Script
# Supports: Linux (x64, arm64), macOS (x64, arm64)
# Usage: curl -fsSL https://raw.githubusercontent.com/gyra-ai/Gyra/main/install.sh | bash

set -u

BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
CONFIG_DIR="${CONFIG_DIR:-$HOME/.gyra/configs}"
REPO_URL="https://github.com/gyra-ai/Gyra.git"
VERSION="${VERSION:-latest}"
DEFAULT_CONFIG="gyra-proxy-aliyun.toml"

# Colors - define first to avoid macOS system 'log' command conflict
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions - must be defined before any usage
log() {
    echo -e "${BLUE}[Gyra]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[Warning]${NC} $1"
}

error() {
    echo -e "${RED}[Error]${NC} $1" >&2
    exit 1
}

success() {
    echo -e "${GREEN}[Success]${NC} $1"
}

# Detect local mode: if running from within the project directory, skip clone
LOCAL_MODE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/pyproject.toml" ] && grep -q "Gyra\|gyra\|gyra" "$SCRIPT_DIR/pyproject.toml" 2>/dev/null; then
    LOCAL_MODE=true
    INSTALL_DIR="${INSTALL_DIR:-$SCRIPT_DIR}"
    log "Detected local source at $INSTALL_DIR, skipping git clone."
else
    INSTALL_DIR="${INSTALL_DIR:-$(pwd)/Gyra}"
fi

# Detect OS and architecture
detect_platform() {
    local os
    local arch
    
    os=$(uname -s | tr '[:upper:]' '[:lower:]')
    arch=$(uname -m)
    
    case "$os" in
        linux)
            os="linux"
            ;;
        darwin)
            os="macos"
            ;;
        *)
            error "Unsupported operating system: $os"
            ;;
    esac
    
    case "$arch" in
        x86_64|amd64)
            arch="x64"
            ;;
        aarch64|arm64)
            arch="arm64"
            ;;
        *)
            error "Unsupported architecture: $arch"
            ;;
    esac
    
    echo "${os}-${arch}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Auto-detect system environment and setup GYRA_HOME
setup_gyra_env() {
    local os_type
    os_type=$(uname -s | tr '[:upper:]' '[:lower:]')

    log "Platform: $os_type ($(uname -m))"

    # If GYRA_HOME already set by user, use it directly
    if [ -n "${GYRA_HOME:-}" ]; then
        mkdir -p "$GYRA_HOME" 2>/dev/null || true
        log "Config directory: $GYRA_HOME (GYRA_HOME)"
        export GYRA_HOME
        return 0
    fi

    # Try default ~/.gyra
    local default_home="${HOME:-}/.gyra"
    if [ -n "${HOME:-}" ] && mkdir -p "$default_home" 2>/dev/null; then
        log "Config directory: $default_home"
        return 0
    fi

    # Fallback for Linux servers without writable HOME
    warn "HOME directory not writable, auto-selecting GYRA_HOME..."
    for candidate in "/opt/gyra" "/var/lib/gyra" "/tmp/gyra"; do
        if mkdir -p "$candidate" 2>/dev/null; then
            export GYRA_HOME="$candidate"
            success "Using GYRA_HOME=$GYRA_HOME (auto-detected)"
            return 0
        fi
    done

    error "Cannot find writable directory for config. Set GYRA_HOME manually."
}

# Install uv if not present
install_uv() {
    if command_exists uv; then
        log "uv is already installed: $(uv --version)"
        return 0
    fi
    
    log "Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"
    
    if ! command_exists uv; then
        error "Failed to install uv. Please install manually: https://github.com/astral-sh/uv"
    fi
    
    success "uv installed successfully: $(uv --version)"
}

# Install Python 3.10+ if needed
ensure_python() {
    local python_version
    
    if command_exists python3; then
        python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
        log "Found Python $python_version"
        
        # Check if version is >= 3.10
        if printf '%s\n' "3.10" "$python_version" | sort -V -C; then
            success "Python version is compatible (>= 3.10)"
            return 0
        fi
    fi
    
    log "Installing Python 3.10+ via uv..."
    uv python install 3.10
    success "Python 3.10 installed"
}

# Clone or update repository (skipped in local mode)
clone_repo() {
    if [ "$LOCAL_MODE" = true ]; then
        log "Local mode: using source at $INSTALL_DIR (skipping git clone)"
        return 0
    fi

    if [ -d "$INSTALL_DIR/.git" ]; then
        log "Gyra already exists at $INSTALL_DIR"
        log "Updating to latest version..."
        cd "$INSTALL_DIR"
        git pull origin main
    else
        log "Cloning Gyra repository..."
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
        success "Repository cloned to $INSTALL_DIR"
    fi
}

# Install Gyra dependencies
install_dependencies() {
    log "Installing Gyra dependencies..."
    cd "$INSTALL_DIR"
    
    uv sync --all-packages --frozen \
        --extra "proxy_openai" \
        --extra "storage_chromadb" \
        --extra "gyras" \
        --extra "storage_oss2" \
        --extra "client" \
        --extra "ext_base"
    
    success "Dependencies installed successfully"
}

# Initialize default configuration
init_config() {
    local src_config="$INSTALL_DIR/configs/$DEFAULT_CONFIG"
    local dest_config="$CONFIG_DIR/$DEFAULT_CONFIG"

    mkdir -p "$CONFIG_DIR"

    if [ -f "$dest_config" ]; then
        log "Configuration file already exists: $dest_config (skipping)"
        return 0
    fi

    if [ -f "$src_config" ]; then
        cp "$src_config" "$dest_config"
        success "Default configuration initialized: $dest_config"
        warn "Please edit $dest_config and set your API keys before starting the server."
    else
        warn "Template config not found at $src_config, skipping config initialization."
    fi
}

# Create wrapper scripts
create_wrappers() {
    log "Creating wrapper scripts..."
    
    mkdir -p "$BIN_DIR"
    
    # Create main gyra command
    local gyra_home_line=""
    if [ -n "${GYRA_HOME:-}" ]; then
        gyra_home_line="export GYRA_HOME=\"$GYRA_HOME\""
    fi

    cat > "$BIN_DIR/gyra" << EOF
#!/bin/bash
# Gyra Launcher with auto-dependency sync
$gyra_home_line
cd "$INSTALL_DIR" || exit 1

# Auto-sync dependencies before running (skip with GYRA_NO_SYNC=1)
if [ -f "uv.lock" ] && [ "\${GYRA_NO_SYNC:-}" != "1" ]; then
    echo -e "\033[34m[Gyra]\033[0m Checking dependencies..."
    uv sync --all-packages --frozen \\
        --extra "proxy_openai" \\
        --extra "storage_chromadb" \\
        --extra "gyras" \\
        --extra "storage_oss2" \\
        --extra "client" \\
        --extra "ext_base" 2>&1 | sed 's/^/  /'
fi

exec uv run gyra "\$@"
EOF
    
    chmod +x "$BIN_DIR/gyra"
    
    # Create gyra-server command
    cat > "$BIN_DIR/gyra-server" << EOF
#!/bin/bash
# Gyra Server Launcher with auto-dependency sync
$gyra_home_line
DEFAULT_CONFIG="$CONFIG_DIR/$DEFAULT_CONFIG"

cd "$INSTALL_DIR" || exit 1

# Auto-sync dependencies before running (skip with GYRA_NO_SYNC=1)
if [ -f "uv.lock" ] && [ "\${GYRA_NO_SYNC:-}" != "1" ]; then
    echo -e "\033[34m[Gyra]\033[0m Checking dependencies..."
    uv sync --all-packages --frozen \\
        --extra "proxy_openai" \\
        --extra "storage_chromadb" \\
        --extra "gyras" \\
        --extra "storage_oss2" \\
        --extra "client" \\
        --extra "ext_base" 2>&1 | sed 's/^/  /'
fi

# If no arguments provided and default config exists, use it
if [ \$# -eq 0 ] && [ -f "\$DEFAULT_CONFIG" ]; then
    exec uv run gyra start webserver -c "\$DEFAULT_CONFIG"
else
    exec uv run gyra start webserver "\$@"
fi
EOF
    
    chmod +x "$BIN_DIR/gyra-server"
    
    success "Wrapper scripts created in $BIN_DIR"
}

# Add to shell config
add_to_path() {
    local shell_config=""
    
    case "$SHELL" in
        */bash)
            shell_config="$HOME/.bashrc"
            [ -f "$HOME/.bash_profile" ] && shell_config="$HOME/.bash_profile"
            ;;
        */zsh)
            shell_config="$HOME/.zshrc"
            ;;
        */fish)
            shell_config="$HOME/.config/fish/config.fish"
            ;;
    esac
    
    if [ -n "$shell_config" ] && [ -f "$shell_config" ]; then
        if ! grep -q "$BIN_DIR" "$shell_config" 2>/dev/null; then
            log "Adding $BIN_DIR to PATH in $shell_config"
            echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$shell_config"
        fi
        # Persist GYRA_HOME if it was auto-detected
        if [ -n "${GYRA_HOME:-}" ] && ! grep -q "GYRA_HOME" "$shell_config" 2>/dev/null; then
            log "Adding GYRA_HOME=$GYRA_HOME to $shell_config"
            echo "export GYRA_HOME=\"$GYRA_HOME\"" >> "$shell_config"
        fi
        warn "Please restart your shell or run: source $shell_config"
    fi
}

# Print usage
print_usage() {
    cat << EOF
Gyra Installer

Usage:
  Remote mode (clone from GitHub):
    curl -fsSL https://raw.githubusercontent.com/gyra-ai/Gyra/main/install.sh | bash

  Local mode (run from project directory, skips git clone):
    cd /path/to/Gyra && bash install.sh

Environment Variables:
  INSTALL_DIR    Installation directory (default: \$(pwd)/Gyra)
  BIN_DIR        Binary directory (default: $HOME/.local/bin)
  CONFIG_DIR     Configuration directory (default: $HOME/.gyra/configs)
  VERSION        Version to install (default: latest)
  GYRA_NO_SYNC   Set to '1' to skip automatic dependency sync on launch

Options:
  --help         Show this help message
  --version      Show version information

After Installation:
  1. Edit config and set your API keys
  2. gyra-server    Start Gyra Server (uses default config)
  3. gyra           Start Gyra CLI

Notes:
  - Dependencies are auto-synced on each launch (uses uv.lock)
  - Skip auto-sync with: GYRA_NO_SYNC=1 gyra-server
  - Independent install script: bash install.sh

For more information, visit: https://github.com/gyra-ai/Gyra
EOF
}

# Print version
print_version() {
    echo "Gyra Installer v0.1.0"
}

# Main installation
main() {
    # Parse arguments
    for arg in "$@"; do
        case "$arg" in
            --help|-h)
                print_usage
                exit 0
                ;;
            --version|-v)
                print_version
                exit 0
                ;;
        esac
    done
    
    log "Starting Gyra installation..."
    log "Platform: $(detect_platform)"
    if [ "$LOCAL_MODE" = true ]; then
        log "Mode: local (using existing source)"
    else
        log "Mode: remote (cloning from GitHub)"
    fi
    log "Install directory: $INSTALL_DIR"
    log "Config directory: $CONFIG_DIR"
    log "Binary directory: $BIN_DIR"
    
    # Auto-detect system and setup config directory
    setup_gyra_env

    # Installation steps
    install_uv
    ensure_python
    clone_repo
    install_dependencies
    init_config
    create_wrappers
    add_to_path
    
    success "Gyra installed successfully!"
    echo ""
    echo "=========================================="
    echo "  Quick Start (zero configuration):"
    echo "=========================================="
    echo "  gyra quickstart"
    echo "  # Then open http://localhost:8888 to configure models and settings in the web UI."
    echo ""
    echo "  Options:"
    echo "    gyra quickstart -p 8888        # Use custom port"
    echo "    gyra quickstart -h 127.0.0.1   # Use custom host"
    echo ""
    echo "=========================================="
    echo "  Config-based Start:"
    echo "=========================================="
    echo "  1. Edit config: $CONFIG_DIR/$DEFAULT_CONFIG"
    echo "     Set your API keys (e.g., DASHSCOPE_API_KEY)"
    echo "  2. Start server:"
    echo "     gyra-server                              # Use default config"
    echo "     gyra-server -c /path/to/config.toml      # Use custom config"
    echo "  3. Open browser: http://localhost:8888"
    echo ""
    echo "Available config templates in: $INSTALL_DIR/configs/"
    echo "  - gyra-proxy-aliyun.toml    (Aliyun/DashScope)"
    echo "  - gyra-proxy-openai.toml    (OpenAI compatible)"
    echo ""
    echo "Documentation: https://github.com/gyra-ai/Gyra"
}

main "$@"
