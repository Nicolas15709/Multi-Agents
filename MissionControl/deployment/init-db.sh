#!/bin/bash
# Database Initialization and Migration Script
# ============================================
# Este script debe ejecutarse DESPUÃ‰S de tener docker-compose listo
# Usa el contenedor para inicializar la base de datos

set -e

echo "=== Virtual Agency Database Initialization ==="
echo ""

# Verificar que docker-compose existe
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose no estÃ¡ instalado"
    exit 1
fi

# Verificar que el servicio estÃ¡ definido
if ! docker-compose config &> /dev/null; then
    echo "Error: docker-compose.yml no es vÃ¡lido o no existe en el directorio actual"
    exit 1
fi

# Asegurar que el directorio data existe localmente
mkdir -p ./data

echo "Step 1: Verificando que la imagen estÃ© construida..."
docker-compose build

echo ""
echo "Step 2: Inicializando base de datos en el contenedor..."
docker-compose exec -T virtual-agency python3 -c "
from pathlib import Path
from db import Database

db_path = Path('/app/data/runtime.db')
db = Database(str(db_path))
db.init()
print('âœ“ Database schema created at /app/data/runtime.db')
"

echo ""
echo "Step 3: Sembrando agentes iniciales..."
docker-compose exec -T virtual-agency python3 -c "
from pathlib import Path
import json
from db import Database

db_path = Path('/app/data/runtime.db')
db = Database(str(db_path))

# Verificar si ya hay agentes
existing = db.fetchone('SELECT COUNT(*) as count FROM agent_status')
if existing and existing['count'] > 0:
    print('âœ“ Agents already seeded')
    exit(0)

# Leer configuraciÃ³n de agentes
config_path = Path('/app/config/agents.json')
if config_path.exists():
    agents = json.loads(config_path.read_text())
    for agent in agents.get('agents', []):
        db.execute('''
            INSERT OR REPLACE INTO agent_status
            (agent_id, display_name, role, state, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        ''', [agent['id'], agent['name'], agent['role'], 'idle'])
    print(f'âœ“ Seeded {len(agents.get(\"agents\", []))} agents')
else:
    print('âš  No agents config found at /app/config/agents.json')
"

echo ""
echo "=== Database initialization complete ==="
echo ""
echo "Next steps:"
echo "1. Start Virtual Agency: docker-compose up -d"
echo "2. Check status: docker-compose ps"
echo "3. View logs: docker-compose logs -f"
echo "4. Open dashboard: http://localhost/ (or your VPS IP)"
echo ""
echo "NOTE: If this is the first run, the dashboard may take ~10s to appear"
echo "      while the Python runtime boots and generates the initial snapshot."



