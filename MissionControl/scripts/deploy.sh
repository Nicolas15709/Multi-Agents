#!/bin/bash
# Script de deploy en VPS
# Uso: ./scripts/deploy.sh
set -e
echo "Desplegando Virtual Agency Runtime..."
docker compose pull 2>/dev/null || true
docker compose build --no-cache
docker compose down 2>/dev/null || true
docker compose up -d
echo "Runtime corriendo en puerto 8787"
echo "Verificando health..."
sleep 3
curl -sf http://localhost:8787/health && echo " Health OK" || echo " Health check fallo - revisa los logs con: docker compose logs -f"
