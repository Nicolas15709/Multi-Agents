#!/bin/bash
# Limpia la BD local SQLite para empezar desde cero
set -e
echo "Reseteando base de datos local..."
rm -f data/runtime.db data/sessions.db
mkdir -p data
echo "BD reseteada. Arranca el runtime con: python runtime/python/main.py"
