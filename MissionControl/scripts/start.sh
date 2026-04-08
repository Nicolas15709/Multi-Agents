#!/bin/bash
# Arranca el runtime desde la raíz de MissionControl
set -e
cd "$(dirname "$0")/.."
source .env 2>/dev/null || true
pip install -r runtime/python/requirements.txt -q
python runtime/python/main.py
