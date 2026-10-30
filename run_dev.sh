#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
(cd frontend && npm install)
python backend/scripts/seed.py
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT
cd frontend
npm run dev -- --host 127.0.0.1
