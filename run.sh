#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd -- "$script_dir"
if [[ -x .venv/bin/python ]]; then
    python_command=.venv/bin/python
elif [[ -x venv/bin/python ]]; then
    python_command=venv/bin/python
else
    echo 'Run ./install.sh first.' >&2
    exit 1
fi
exec "$python_command" modern_motor_gui.py "$@"
