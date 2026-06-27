#!/usr/bin/env bash
set -euo pipefail

VENV_PATH="${1:-.venv}"

python3 -m venv "$VENV_PATH"
"$VENV_PATH/bin/python" -m pip install --upgrade pip
"$VENV_PATH/bin/python" -m pip install -e .

cat <<EOF

Installed codex-cheap-worker.
Activate with:
  source "$VENV_PATH/bin/activate"

Configure a worker model:
  export WORKER_API_KEY="your-key"
  export WORKER_BASE_URL="https://api.moonshot.ai/v1"
  export WORKER_MODEL="kimi-k2.5"

Try:
  ask-worker --paths "src/**/*.py" --question "Summarize the modules" --dry-run
EOF

