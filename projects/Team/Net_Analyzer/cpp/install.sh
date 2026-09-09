#!/usr/bin/env bash
set -euo pipefail

install_just() {
    if command -v just &>/dev/null; then
        echo "==> just already installed, skipping."
        return
    fi

    echo "==> Installing just..."
    if command -v apt &>/dev/null; then
        sudo apt install -y just || {
            curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin
        }
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y just
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --needed just
    else
        curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin
    fi
}

install_deps() {
    echo "==> Installing build dependencies..."
    if command -v apt &>/dev/null; then
        sudo apt install -y libboost-program-options-dev libpcap-dev cmake ninja-build g++ clang-tidy clang-format
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y boost-devel libpcap-devel cmake ninja-build gcc-c++ clang-tools-extra
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --needed boost libpcap cmake ninja gcc clang
    else
        echo "Unsupported package manager. Install manually: boost, libpcap, cmake, ninja, g++, clang-tidy, clang-format"
        exit 1
    fi
    echo "==> Dependencies ready."
}

build() {
    echo "==> Configuring..."
    cmake -B build/release -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    echo "==> Building..."
    cmake --build build/release
    echo ""
    echo "Setup complete! Run 'just' to see available commands."
}

install_just
install_deps
build
