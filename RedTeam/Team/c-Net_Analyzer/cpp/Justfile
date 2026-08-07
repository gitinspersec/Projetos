set shell := ["bash", "-uc"]

default:
    @just --list --unsorted

build:
    cmake -B build/debug -G Ninja -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    cmake --build build/debug

run *ARGS:
    sudo ./build/release/network-traffic-analyzer {{ARGS}}

run-debug *ARGS:
    sudo ./build/debug/network-traffic-analyzer {{ARGS}}

capture interface="eth0":
    sudo ./build/release/network-traffic-analyzer -i {{interface}}

interfaces:
    sudo ./build/release/network-traffic-analyzer --interfaces

lint:
    @sed -i 's/-fdeps-format=p1689r5//g; s/-fmodule-mapper=[^ ]*//g; s/-fmodules-ts//g' build/release/compile_commands.json
    clang-tidy -p build/release src/**/*.cpp 2>/dev/null

format:
    find src include \( -name '*.cpp' -o -name '*.hpp' \) | xargs clang-format -i

clean:
    rm -rf build/
