#!/bin/bash
set -e

# Virtual Agency Startup Script
# =============================

echo "=== Virtual Agency Starting ==="

# Initialize database if it doesn't exist
if [ ! -f "/app/data/runtime.db" ]; then
    echo "Initializing database..."
    python3 -c "
from db import Database
from pathlib import Path
db = Database('/app/data/runtime.db')
db.init()
print('Database initialized at /app/data/runtime.db')
"
fi

# Start nginx in background
echo "Starting nginx..."
nginx -c /etc/nginx/nginx.conf

# Wait for nginx to be ready
sleep 2

# Start Python runtime (foreground)
echo "Starting Python runtime..."
cd /app
exec python3 main.py

