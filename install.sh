#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd -- "$script_dir"
python_command=${PYTHON:-python3}
"$python_command" -c 'import sys; assert (3, 11) <= sys.version_info[:2] <= (3, 12), "Use Python 3.11 or 3.12"'
if [[ ${1:-} == --hardware ]]; then
    "$python_command" -c 'from pathlib import Path; assert any("Raspberry Pi" in p.read_text(errors="replace") for p in [Path("/proc/device-tree/model"), Path("/proc/cpuinfo")] if p.exists()), "Hardware installation requires a Raspberry Pi"'
    "$python_command" -c 'import PyQt5' || { echo 'Install OS prerequisites: sudo apt install python3-venv python3-dev python3-pyqt5 build-essential'; exit 1; }
    "$python_command" -m venv --system-site-packages .venv
    dependency_file=requirements-pi.txt
elif [[ $# == 0 ]]; then
    "$python_command" -m venv .venv
    dependency_file=requirements.txt
else
    echo 'Usage: ./install.sh [--hardware]' >&2
    exit 2
fi
.venv/bin/python -m pip install --require-hashes -r "$dependency_file"
printf '%s\n' 'Installation complete. Use ./run.sh on the Pi or ./run.sh --offline to inspect without hardware.'
