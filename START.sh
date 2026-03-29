#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR/backend_python"

if [ -x ".venv/bin/python" ]; then
  exec ".venv/bin/python" app.py
elif [ -x "venv/bin/python" ]; then
  exec "venv/bin/python" app.py
elif command -v python3 >/dev/null 2>&1; then
  exec python3 app.py
else
  exec python app.py
fi
