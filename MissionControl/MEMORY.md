# Memory System Configuration Guide

Mission Control implementa una arquitectura de memoria de tres capas:

1. **Memoria Vectorial** (Supabase pgvector) - Búsqueda semántica a largo plazo
2. **Memoria por Sesión** (SQLite local) - Estado en tiempo real con diffing
3. **Capa de Almacenamiento** (SQLite runtime + Supabase respaldo)

## Componentes

### Vector Store (Supabase pgvector)

Tablas en Supabase:
- `agent_memories` - Observaciones, reflexiones y aprendizajes de agentes
- `semantic_events` - Eventos de misión (acciones, decisiones, handoffs)
- `knowledge_artifacts` - Código, documentos, diseños para RAG
- `session_snapshots` - Snapshots comprimidos de estado de sesión
- `memory_cleanup_log` - Auditoría de limpiezas automáticas

**Requisitos**:
- Habilitar extensión `vector` en Supabase:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```
- Configurar índices IVFFLAT para rendimiento de búsqueda (ver `vector_schema.sql`)

### Session Store (SQLite)

Tablas locales:
- `runtime_sessions` - Estado actual de cada agente en misión
- `session_diffs` - Diferenciales secuenciales para replay/resume
- `session_checkpoints` - Metadatos de checkpoints (enlaza a Supabase)
- `memory_sync_queue` - Cola de sincronización (opcional)
- `session_ttl_policies` - Políticas de retención configurables

### Embeddings Service

Soporta:
- **OpenAI**: `text-embedding-ada-002` (1536 dims)
- **Groq**: Compatible con OpenAI embeddings API

Configuración vía `.env`:
```bash
EMBEDDING_PROVIDER=openai  # o 'groq'
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_BATCH_SIZE=100
EMBEDDING_CACHE=true
```

## Instalación Paso a Paso

### 1. Configurar Supabase

A. Crear proyecto en Supabase (dashboard)

B. Habilitar extensión pgvector:
```sql
-- Ejecutar en SQL Editor
CREATE EXTENSION IF NOT EXISTS vector;
```

C. Aplicar esquema vectorial:
```bash
# Opción A: Manual (recomendado inicial)
# Copiar y ejecutar deploy/migrations/combined_migrations.sql en SQL Editor

# Opción B: Script automático (requiere Edge Function)
node deploy/apply_migrations.js
```

D. Configurar Row Level Security (opcional, si usas auth):
```sql
-- Habilitar RLS en tablas de memoria
ALTER TABLE agent_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_artifacts ENABLE ROW LEVEL SECURITY;
-- Crear políticas adecuadas para tu modelo de roles
```

E. Obtener credentials:
- `SUPABASE_URL` (Settings → API)
- `SUPABASE_SERVICE_ROLE_KEY` (Settings → API → Service Role Key)

### 2. Configurar Embeddings API

**OpenAI**:
```bash
export OPENAI_API_KEY="sk-..."
```

**Groq** (alternativa gratuita/rápida):
```bash
export GROQ_API_KEY="gsk_..."
export EMBEDDING_PROVIDER="groq"
```

### 3. Inicializar SQLite local

```bash
cd MissionControl
npm run init-db
```

Esto crea:
- `data/sessions.db` con esquema legacy + session
- Tablas de TTL policies insertadas

### 4. Configurar Variables de Entorno

Copiar `.env.example` a `.env`:
```bash
cp .env.example .env
# Editar con tus valores reales
```

Variables mínimas requeridas:
```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
EMBEDDING_PROVIDER=openai  # o groq
OPENAI_API_KEY=sk-...       # o GROQ_API_KEY
```

Variables opcionales (TTL):
```bash
MEMORY_TTL_MEMORIES_DAYS=180   # cuánto guardar recuerdos
MEMORY_TTL_SESSIONS_DAYS=7    # sesiones inactivas
MEMORY_TTL_SNAPSHOTS_DAYS=90  # snapshots en Supabase
MEMORY_DIFFS_TO_KEEP=100      # diffs por sesión
```

## Uso del Sistema

### JavaScript/Node (Runtime)

```javascript
import {
  initMemorySystem,
  rememberMemory,
  searchMemories,
  openAgentSession,
  updateAgentSession,
  checkpointSession,
  unifiedSearch
} from './src/memory/index.js';

// Inicializar
await initMemorySystem();

// Crear sesión para agente
const session = openAgentSession('mission-uuid', 'researcher-1');

// Recordar observación
await rememberMemory({
  agentId: 'researcher-1',
  missionId: 'mission-uuid',
  sessionId: session.sessionToken,
  content: 'Found 3 relevant APIs for integration',
  memoryType: 'observation',
  importance: 2.0,
  metadata: { topic: 'api-research' }
});

// Buscar memorias similares
const results = await searchMemories({
  query: 'integration options',
  agentId: 'researcher-1',
  limit: 5
});

// Checkpoint manual
await checkpointSession(session.sessionToken, 'manual', 'pre-research-phase');
```

### Python (Agents)

```python
# Mission Control incluye un cliente Python (runtime/python/memory_client.py)
from memory_client import MemoryClient

client = MemoryClient(base_url='http://localhost:8000')  # si expones API

# O acceder directamente via imports si está en el mismo proceso
# from memory import MemoryManager
```

## TTL y Limpieza Automática

El sistema incluye limpieza automática basada en políticas:

- **Agent memories**: Elimina >180 días (configurable)
- **Sessions**: Desactiva inactivas >7 días
- **Diffs**: Purguejea dejando solo los últimos 100 por sesión
- **Snapshots**: Elimina >90 días de Supabase

Ejecutar limpieza manual:
```javascript
import { runMemoryCleanup } from './src/memory/index.js';
await runMemoryCleanup();
```

O vía cron:
```bash
0 */6 * * * cd /path/to/MissionControl && node -e "import('./src/memory/index.js').then(m => m.runMemoryCleanup())"
```

## Búsqueda Unificada

```javascript
const results = await unifiedSearch({
  query: 'previous design decisions',
  missionId: 'mission-uuid',
  agentId: 'designer-1',
  types: ['memories', 'artifacts', 'events'],
  limit: 10
});
// Returns: { memories: [], events: [], artifacts: [] }
```

## Snapshot y Resume

```javascript
// Crear checkpoint (guarda en Supabase y registra local)
const { checkpointId } = await checkpointSession(token, 'pre-handoff', 'Switching agents');

// Restaurar desde checkpoint
const restoredState = resumeSessionFromCheckpoint(token, checkpointId);

// Obtener diffs incrementales (para sync)
const diffs = getSessionIncrementalDiff(token);
```

## Verificación y Salud

```javascript
import { healthCheck } from './src/memory/index.js';
const status = healthCheck();
// { sqlite: 'connected', active_sessions: 2, total_diffs: 145, config: {...} }
```

## Debugging

Ver estadísticas de embeddings cache:
```javascript
import { getEmbeddingCacheStats } from './src/memory/embeddings.js';
console.log(getEmbeddingCacheStats());
```

Ver sesiones activas:
```sql
SELECT agent_id, mission_id, last_activity, token_usage
FROM runtime_sessions
WHERE is_active = 1
ORDER BY last_activity DESC;
```

Logs de limpieza (Supabase):
```sql
SELECT * FROM memory_cleanup_log ORDER BY deleted_at DESC LIMIT 10;
```

## Despliegue en Producción

1. Asegurar Supabase URL y Service Role Key en `.env`
2. Verificar que la extensión `vector` está habilitada
3. Aplicar migraciones `deploy/migrations/*.sql`
4. Inicializar SQLite con `npm run init-db`
5. Configurar TTL según políticas de retención
6. Agregar cron job para limpieza automática
7. Monitorear con `healthCheck()` y logs

## Fallback sin Supabase

Si `SUPABASE_URL` no está configurada:
- Vec store: No disponible
- Session store: SQLite local funciona (state + diffs + checkpoints locales)
- El sistema continue con funcionalidad reducida (no hay búsqueda semántica persistente)

Para pruebas locales, puedes deshabilitar Supabase y usar solo SQLite.

## Referencia de Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `SUPABASE_URL` | URL del proyecto Supabase | (requerido) |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key de Supabase | (requerido) |
| `EMBEDDING_PROVIDER` | `openai` o `groq` | `openai` |
| `OPENAI_API_KEY` | API key de OpenAI | - |
| `GROQ_API_KEY` | API key de Groq | - |
| `EMBEDDING_MODEL` | Modelo de embedding | `text-embedding-ada-002` |
| `EMBEDDING_BATCH_SIZE` | Lote para embeddings batch | `100` |
| `MEMORY_TTL_MEMORIES_DAYS` | Retención memorias (días) | `180` |
| `MEMORY_TTL_SESSIONS_DAYS` | Retención sesiones (días) | `7` |
| `MEMORY_TTL_SNAPSHOTS_DAYS` | Retención snapshots (días) | `90` |
| `MEMORY_DIFFS_TO_KEEP` | Diffs a conservar por sesión | `100` |
| `MEMORY_CLEANUP_INTERVAL_HOURS` | Intervalo limpieza automática | `24` |

## Soporte

- Issues: reportar en GitHub del proyecto
- Documentación adicional: `docs/MEMORY_ARCHITECTURE.md`
