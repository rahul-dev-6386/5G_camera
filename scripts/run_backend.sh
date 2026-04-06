#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Missing root virtual environment at .venv"
  echo "Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-cpu.txt"
  exit 1
fi

exec .venv/bin/python -m uvicorn apps.api.src.app.main:app --host 0.0.0.0 --port 8000 --reload
