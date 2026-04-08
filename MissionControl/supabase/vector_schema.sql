-- Supabase pgvector schema for Virtual Agency Memory
-- IMPORTANT: Enable the extension first in your Supabase dashboard SQL editor:
-- CREATE EXTENSION IF NOT EXISTS vector;

-- Agent memories (vector searchable)
CREATE TABLE IF NOT EXISTS agent_memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL,
  mission_id UUID REFERENCES missions(id) ON DELETE CASCADE,
  session_id UUID, -- Optional session association
  content TEXT NOT NULL,
  embedding VECTOR(1536), -- OpenAI text-embedding-ada-002 dimension
  metadata JSONB DEFAULT '{}'::jsonb,
  memory_type TEXT NOT NULL DEFAULT 'observation', -- observation, reflection, learning, artifact
  importance FLOAT NOT NULL DEFAULT 1.0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS agent_memories_agent_idx ON agent_memories(agent_id);
CREATE INDEX IF NOT EXISTS agent_memories_mission_idx ON agent_memories(mission_id);
CREATE INDEX IF NOT EXISTS agent_memories_created_idx ON agent_memories(created_at DESC);
CREATE INDEX IF NOT EXISTS agent_memories_embedding_idx ON agent_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Semantic events log (full-text + vector search)
CREATE TABLE IF NOT EXISTS semantic_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID REFERENCES missions(id) ON DELETE CASCADE,
  agent_id TEXT,
  event_type TEXT NOT NULL,
  description TEXT NOT NULL,
  embedding VECTOR(1536),
  payload JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS semantic_events_mission_idx ON semantic_events(mission_id);
CREATE INDEX IF NOT EXISTS semantic_events_agent_idx ON semantic_events(agent_id);
CREATE INDEX IF NOT EXISTS semantic_events_embedding_idx ON semantic_events USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Knowledge artifacts (indexed for RAG)
CREATE TABLE IF NOT EXISTS knowledge_artifacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID REFERENCES missions(id) ON DELETE CASCADE,
  artifact_type TEXT NOT NULL, -- code, doc, design, plan, etc.
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(1536),
  metadata JSONB DEFAULT '{}'::jsonb,
  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS knowledge_artifacts_mission_idx ON knowledge_artifacts(mission_id);
CREATE INDEX IF NOT EXISTS knowledge_artifacts_type_idx ON knowledge_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS knowledge_artifacts_embedding_idx ON knowledge_artifacts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Session snapshots (compressed state differentials)
CREATE TABLE IF NOT EXISTS session_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID REFERENCES missions(id) ON DELETE CASCADE,
  session_token TEXT NOT NULL UNIQUE,
  snapshot_data BYTEA NOT NULL, -- gzipped JSON
  diff_base UUID REFERENCES session_snapshots(id), -- previous snapshot for diffing
  agent_states JSONB DEFAULT '{}'::jsonb,
  checksum TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ -- TTL cleanup
);

CREATE INDEX IF NOT EXISTS session_snapshots_mission_idx ON session_snapshots(mission_id);
CREATE INDEX IF NOT EXISTS session_snapshots_expires_idx ON session_snapshots(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS session_snapshots_created_idx ON session_snapshots(created_at DESC);

-- Memory TTL cleanup log (audit of automatic deletions)
CREATE TABLE IF NOT EXISTS memory_cleanup_log (
  id BIGSERIAL PRIMARY KEY,
  table_name TEXT NOT NULL,
  records_deleted INTEGER NOT NULL,
  cleanup_reason TEXT NOT NULL, -- ttl_expired, manual, etc.
  deleted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Policies (Row Level Security disabled for service role; enable if using auth)
-- enable_rls on all tables as needed in production

