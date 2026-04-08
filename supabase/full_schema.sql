-- ============================================================
-- MULTI-AGENTS / MISSION CONTROL - FULL DATABASE SCHEMA
-- Para Supabase (PostgreSQL)
-- ============================================================

-- 1. EXTENSIONS
-- Habilitar primero en el SQL Editor de Supabase:
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 2. CORE TABLES
-- ============================================================

-- Perfiles de usuario (vinculado a auth.users de Supabase)
CREATE TABLE IF NOT EXISTS profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username text UNIQUE,
  display_name text,
  avatar_url text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Preferencias de UI por usuario
CREATE TABLE IF NOT EXISTS ui_preferences (
  user_id uuid PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
  theme text DEFAULT 'virtual-agency-dark',
  density text DEFAULT 'comfortable',
  motion_enabled boolean NOT NULL DEFAULT true,
  layout jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Proyectos (contenedores de misiones)
CREATE TABLE IF NOT EXISTS projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid REFERENCES profiles(id) ON DELETE SET NULL,
  name text NOT NULL,
  slug text UNIQUE,
  description text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- 3. MISSION CONTROL TABLES
-- ============================================================

-- Misiones (unidad principal de trabajo del orquestador)
CREATE TABLE IF NOT EXISTS missions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES projects(id) ON DELETE CASCADE,
  title text NOT NULL,
  goal text NOT NULL,
  status text NOT NULL DEFAULT 'draft',  -- draft | running | paused | completed | failed
  created_by uuid REFERENCES profiles(id) ON DELETE SET NULL,
  current_agent text,
  retry_count integer NOT NULL DEFAULT 0,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Cola de tareas entre agentes
CREATE TABLE IF NOT EXISTS task_queue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id uuid NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
  task_id text NOT NULL,
  from_agent text NOT NULL,
  to_agent text NOT NULL,
  status text NOT NULL DEFAULT 'pending',  -- pending | running | done | failed
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Mensajes de agentes durante una misión
CREATE TABLE IF NOT EXISTS agent_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id uuid NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
  agent_id text NOT NULL,
  message_type text NOT NULL,  -- system | user | assistant | tool_result
  pinned boolean NOT NULL DEFAULT false,
  content text NOT NULL,
  summary text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Eventos de misión (log estructurado)
CREATE TABLE IF NOT EXISTS mission_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id uuid REFERENCES missions(id) ON DELETE CASCADE,
  event_type text NOT NULL,
  agent_id text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Reintentos de tareas fallidas
CREATE TABLE IF NOT EXISTS retries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id uuid NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
  task_id text NOT NULL,
  agent_id text NOT NULL,
  attempt integer NOT NULL,
  reason text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- 4. ARTIFACTS & KNOWLEDGE
-- ============================================================

-- Artefactos generados por agentes
CREATE TABLE IF NOT EXISTS saved_artifacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id uuid REFERENCES missions(id) ON DELETE CASCADE,
  artifact_type text,  -- code | doc | design | plan | etc.
  title text,
  path text,
  content text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Knowledge artifacts (RAG-ready, con embeddings vectoriales)
CREATE TABLE IF NOT EXISTS knowledge_artifacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id uuid REFERENCES missions(id) ON DELETE CASCADE,
  artifact_type text NOT NULL,  -- code | doc | design | plan | etc.
  title text NOT NULL,
  content text NOT NULL,
  embedding vector(1536),       -- OpenAI text-embedding-ada-002
  metadata jsonb DEFAULT '{}'::jsonb,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- 5. MEMORY SYSTEM (pgvector)
-- ============================================================

-- Memorias de agentes (búsqueda semántica)
CREATE TABLE IF NOT EXISTS agent_memories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id text NOT NULL,
  mission_id uuid REFERENCES missions(id) ON DELETE CASCADE,
  session_id uuid,
  content text NOT NULL,
  embedding vector(1536),
  metadata jsonb DEFAULT '{}'::jsonb,
  memory_type text NOT NULL DEFAULT 'observation',  -- observation | reflection | learning | artifact
  importance float NOT NULL DEFAULT 1.0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Eventos semánticos (full-text + vector search)
CREATE TABLE IF NOT EXISTS semantic_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id uuid REFERENCES missions(id) ON DELETE CASCADE,
  agent_id text,
  event_type text NOT NULL,
  description text NOT NULL,
  embedding vector(1536),
  payload jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Snapshots de sesión (estado comprimido para recuperación)
CREATE TABLE IF NOT EXISTS session_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id uuid REFERENCES missions(id) ON DELETE CASCADE,
  session_token text NOT NULL UNIQUE,
  snapshot_data bytea NOT NULL,            -- gzipped JSON
  diff_base uuid REFERENCES session_snapshots(id),
  agent_states jsonb DEFAULT '{}'::jsonb,
  checksum text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz
);

-- Log de limpieza de memoria (auditoría)
CREATE TABLE IF NOT EXISTS memory_cleanup_log (
  id bigserial PRIMARY KEY,
  table_name text NOT NULL,
  records_deleted integer NOT NULL,
  cleanup_reason text NOT NULL,  -- ttl_expired | manual | etc.
  deleted_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- 6. INDEXES
-- ============================================================

-- Missions
CREATE INDEX IF NOT EXISTS missions_project_idx ON missions(project_id);
CREATE INDEX IF NOT EXISTS missions_status_idx ON missions(status);
CREATE INDEX IF NOT EXISTS missions_created_idx ON missions(created_at DESC);

-- Task queue
CREATE INDEX IF NOT EXISTS task_queue_mission_idx ON task_queue(mission_id);
CREATE INDEX IF NOT EXISTS task_queue_status_idx ON task_queue(status);
CREATE INDEX IF NOT EXISTS task_queue_to_agent_idx ON task_queue(to_agent);

-- Agent messages
CREATE INDEX IF NOT EXISTS agent_messages_mission_idx ON agent_messages(mission_id);
CREATE INDEX IF NOT EXISTS agent_messages_agent_idx ON agent_messages(agent_id);
CREATE INDEX IF NOT EXISTS agent_messages_pinned_idx ON agent_messages(pinned) WHERE pinned = true;

-- Mission events
CREATE INDEX IF NOT EXISTS mission_events_mission_idx ON mission_events(mission_id);
CREATE INDEX IF NOT EXISTS mission_events_type_idx ON mission_events(event_type);

-- Agent memories (vector + metadata)
CREATE INDEX IF NOT EXISTS agent_memories_agent_idx ON agent_memories(agent_id);
CREATE INDEX IF NOT EXISTS agent_memories_mission_idx ON agent_memories(mission_id);
CREATE INDEX IF NOT EXISTS agent_memories_created_idx ON agent_memories(created_at DESC);
CREATE INDEX IF NOT EXISTS agent_memories_embedding_idx ON agent_memories
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Semantic events
CREATE INDEX IF NOT EXISTS semantic_events_mission_idx ON semantic_events(mission_id);
CREATE INDEX IF NOT EXISTS semantic_events_agent_idx ON semantic_events(agent_id);
CREATE INDEX IF NOT EXISTS semantic_events_embedding_idx ON semantic_events
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Knowledge artifacts
CREATE INDEX IF NOT EXISTS knowledge_artifacts_mission_idx ON knowledge_artifacts(mission_id);
CREATE INDEX IF NOT EXISTS knowledge_artifacts_type_idx ON knowledge_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS knowledge_artifacts_embedding_idx ON knowledge_artifacts
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Session snapshots
CREATE INDEX IF NOT EXISTS session_snapshots_mission_idx ON session_snapshots(mission_id);
CREATE INDEX IF NOT EXISTS session_snapshots_expires_idx ON session_snapshots(expires_at)
  WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS session_snapshots_created_idx ON session_snapshots(created_at DESC);

-- ============================================================
-- 7. ROW LEVEL SECURITY (RLS)
-- ============================================================

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE ui_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE missions ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE mission_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE retries ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_cleanup_log ENABLE ROW LEVEL SECURITY;

-- Políticas básicas

-- Profiles: usuario ve/edita su propio perfil
CREATE POLICY "profiles_select_own" ON profiles FOR SELECT
  USING (auth.uid() = id);
CREATE POLICY "profiles_update_own" ON profiles FOR UPDATE
  USING (auth.uid() = id);

-- UI Preferences: usuario gestiona sus propias preferencias
CREATE POLICY "ui_preferences_own" ON ui_preferences FOR ALL
  USING (auth.uid() = user_id);

-- Projects: propietario tiene acceso completo
CREATE POLICY "projects_owner_all" ON projects FOR ALL
  USING (auth.uid() = owner_id);

-- Missions: acceso a través de proyecto propio
CREATE POLICY "missions_via_project" ON missions FOR ALL
  USING (
    project_id IN (SELECT id FROM projects WHERE owner_id = auth.uid())
  );

-- service_role bypasses RLS (para backend/agentes)
-- Usar SUPABASE_SERVICE_ROLE_KEY en el servidor, nunca en el cliente.
