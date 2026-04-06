#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Missing root virtual environment at .venv"
  echo "Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-cpu.txt"
  exit 1
fi

echo "Checking Python sources..."
.venv/bin/python -m compileall apps/api/src tools

echo "Building frontend..."
cd apps/web
npm install
npm run build

echo "Project checks passed."
