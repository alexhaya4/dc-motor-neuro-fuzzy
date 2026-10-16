#!/usr/bin/env bash
# Copy source only. Installation is an explicit separate step on the target.
set -euo pipefail
if [[ $# != 1 || ! $1 =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]*@[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]; then
    echo 'Usage: ./deploy_to_pi.sh USER@HOST' >&2
    exit 2
fi
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
rsync -avz --safe-links -e 'ssh -o ConnectTimeout=10' \
    --exclude '.git/' --exclude '.venv/' --exclude 'venv/' --exclude '.env' \
    --exclude '__pycache__/' --exclude '.pytest_cache/' --exclude '.ruff_cache/' \
    --exclude 'models/' --exclude 'data/' --exclude 'logs/' --exclude '*.log' \
    --exclude 'htmlcov/' --exclude 'coverage.xml' --exclude '.coverage' \
    "$script_dir/" "$1:dc-motor-neuro-fuzzy/"
printf '%s\n' 'Source copied to dc-motor-neuro-fuzzy. On the Pi, review .env.example, then run ./install.sh --hardware.'
