#!/usr/bin/env bash
# Starts AstroMuni on http://127.0.0.1:8000 (Mac / Linux). First run creates a private .venv and installs the app.
set -e
cd "$(dirname "$0")"
PY=""
for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "AstroMuni needs Python 3.10 or newer. Install it from https://www.python.org/downloads/ and run this again."; exit 1
fi
if [ ! -x .venv/bin/python ]; then echo "First run: setting up (about a minute)..."; "$PY" -m venv .venv; fi
if ! .venv/bin/python -c 'import aipandit' >/dev/null 2>&1 || [ pyproject.toml -nt .venv/.installed ]; then
  .venv/bin/python -m pip install --quiet --upgrade pip
  .venv/bin/python -m pip install --quiet -e .
  touch .venv/.installed
fi
( sleep 2; (command -v open >/dev/null && open "http://127.0.0.1:8000") || (command -v xdg-open >/dev/null && xdg-open "http://127.0.0.1:8000") || true ) &
exec .venv/bin/astromuni-web "$@"
