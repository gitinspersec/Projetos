#!/usr/bin/env bash
# ©AngelaMos | 2026
# install.sh
#
# Zero-friction install script. Anyone who clones this project should
# be able to run `./install.sh` and end up with a working setup,
# regardless of whether they have uv or just installed yet.
#
# What this script does, in order:
#   1. Verifies Python 3.13+ is installed (we need modern type-hint syntax)
#   2. Installs uv if it is missing (uv is the Python package manager we use)
#   3. Installs just if it is missing (just is the command runner)
#   4. Calls `just setup` to create the venv and install dependencies
#   5. Prints next steps
#
# Run with:  ./install.sh
# Or:        bash install.sh

# -----------------------------------------------------------------------------
# Bash safety flags — fail fast and loud
# -----------------------------------------------------------------------------
# -e : exit immediately if any command returns a non-zero (error) status
# -u : treat unset variables as an error
# -o pipefail : if any command in a pipeline fails, the whole pipeline fails
set -euo pipefail

# -----------------------------------------------------------------------------
# Color helpers — pretty terminal output without external dependencies
# -----------------------------------------------------------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'  # "no color" — resets the terminal back to default

info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }

# -----------------------------------------------------------------------------
# Step 1 — Confirm Python 3.13+ is on the system
# -----------------------------------------------------------------------------
check_python() {
    info "Checking for Python 3.13+..."

    if ! command -v python3 &>/dev/null; then
        error "python3 not found. Please install Python 3.13 or newer."
        error "  macOS:  brew install python@3.13"
        error "  Linux:  sudo apt install python3.13   (Debian/Ubuntu)"
        error "  Windows: download from python.org"
        exit 1
    fi

    # Extract version "3.13.1" → split on dots → take major.minor
    local version
    version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

    local major minor
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)

    if (( major < 3 )) || { (( major == 3 )) && (( minor < 13 )); }; then
        error "Python 3.13+ is required, found Python $version"
        exit 1
    fi

    success "Python $version detected"
}

# -----------------------------------------------------------------------------
# Step 2 — Install uv if missing (https://docs.astral.sh/uv)
# -----------------------------------------------------------------------------
install_uv() {
    if command -v uv &>/dev/null; then
        success "uv already installed ($(uv --version))"
        return 0
    fi

    info "Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # The installer drops uv into ~/.local/bin or ~/.cargo/bin.
    # Add it to PATH for the rest of THIS script's run.
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

    if ! command -v uv &>/dev/null; then
        error "uv install completed but `uv` is still not on PATH."
        error "Restart your shell and re-run this script, or add uv to PATH manually."
        exit 1
    fi
    success "uv installed"
}

# -----------------------------------------------------------------------------
# Step 3 — Install just if missing (https://github.com/casey/just)
# -----------------------------------------------------------------------------
install_just() {
    if command -v just &>/dev/null; then
        success "just already installed ($(just --version))"
        return 0
    fi

    info "Installing just (command runner)..."
    # uv can install Cargo binaries via Cargo, but easier: use the
    # official installer. Drops binary into ~/.local/bin.
    mkdir -p "$HOME/.local/bin"
    curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh \
        | bash -s -- --to "$HOME/.local/bin"

    export PATH="$HOME/.local/bin:$PATH"
    success "just installed"
}

# -----------------------------------------------------------------------------
# Step 4 — Use just to set up the project (venv + dependencies)
# -----------------------------------------------------------------------------
project_setup() {
    info "Running 'just setup'..."
    just setup
}

# -----------------------------------------------------------------------------
# Main — orchestrate the steps and print next instructions
# -----------------------------------------------------------------------------
main() {
    echo ""
    echo "================================================"
    echo "  password-vault — install"
    echo "================================================"
    echo ""

    check_python
    install_uv
    install_just
    project_setup

    echo ""
    echo "================================================"
    success "Install complete!"
    echo "================================================"
    echo ""
    echo "Next steps:"
    echo "  just run -- --help          # see available commands"
    echo "  just run -- init            # create your first vault"
    echo "  just test                   # run the test suite"
    echo ""
}

main "$@"
