# Multi-stage Dockerfile for Mission Control
# ===========================================
# Stage 1: Build the React dashboard (Vite)
FROM node:20-slim AS dashboard-builder

WORKDIR /app

# Install system deps for native modules (e.g., better-sqlite3)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy dashboard package files
COPY MissionControl/apps/dashboard/package*.json ./
COPY MissionControl/package*.json ./

# Install dependencies
RUN npm ci

# Copy dashboard source
COPY MissionControl/apps/dashboard/ ./
COPY MissionControl/public/ ./public/ 2>/dev/null || true

# Build the dashboard
RUN npm run build

# Stage 2: Python runtime builder
FROM python:3.11-slim AS python-builder

WORKDIR /app

# Install Python dependencies
COPY MissionControl/runtime/python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Production image
FROM python:3.11-slim

WORKDIR /app

# Install nginx and supervisor
RUN apt-get update && apt-get install -y \
    nginx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Configure nginx
COPY deployment/nginx.conf /etc/nginx/nginx.conf

# Copy Python dependencies from builder
COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Copy Python runtime code
COPY MissionControl/runtime/python/ ./
COPY MissionControl/config/ ./config/
COPY MissionControl/data/ ./data/ 2>/dev/null || true

# Copy built dashboard from builder
COPY --from=dashboard-builder /app/dist/ ./apps/dashboard/dist/
COPY --from=dashboard-builder /app/public/ ./apps/dashboard/public/ 2>/dev/null || true

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/apps/dashboard/dist

# Expose ports
EXPOSE 80 8765

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start script
COPY deployment/start.sh ./
RUN chmod +x start.sh

CMD ["./start.sh"]
