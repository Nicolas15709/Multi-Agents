-- Combined Supabase Migrations
-- Generated: 2026-03-31T05:03:53.373Z
-- Files: 3
----------------------------------------

-- ----------------------------------------
-- Migration: 001_core_product_schema.sql
-- ----------------------------------------
create table if not exists profiles (
  id uuid primary key,
  username text unique,
  display_name text,
  avatar_url text,
  created_at timestamptz not null default now()
);

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid,
  name text not null,
  slug text unique,
  description text,
  created_at timestamptz not null default now()
);

create table if not exists missions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete cascade,
  title text not null,
  goal text not null,
  status text not null default 'draft',
  created_by uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists mission_events (
  id uuid primary key default gen_random_uuid(),
  mission_id uuid references missions(id) on delete cascade,
  event_type text not null,
  agent_id text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists saved_artifacts (
  id uuid primary key default gen_random_uuid(),
  mission_id uuid references missions(id) on delete cascade,
  artifact_type text,
  title text,
  path text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists ui_preferences (
  user_id uuid primary key,
  theme text default 'virtual-agency-dark',
  density text default 'comfortable',
  motion_enabled boolean not null default true,
  layout jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);


-- ----------------------------------------
-- Migration: 002_vector_schema.sql
-- ----------------------------------------
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


-- ----------------------------------------
-- Migration: 003_vector_functions.sql
-- ----------------------------------------
-- Supabase RPC functions for vector similarity search
-- These are needed because some clients (e.g., Python supabase-py) don't support
-- raw SQL expressions in SELECT easily. Use RPC for consistent cross-language access.

-- Search agent memories with similarity filter
create or replace function search_agent_memories(
  query_embedding vector(1536),
  p_agent_id text default null,
  p_mission_id uuid default null,
  p_memory_type text default null,
  p_limit integer default 10,
  p_similarity_threshold float default 0.7
)
returns table (
  id uuid,
  agent_id text,
  mission_id uuid,
  session_id uuid,
  content text,
  memory_type text,
  importance float,
  metadata jsonb,
  created_at timestamptz,
  updated_at timestamptz,
  similarity float
)
language sql stable
as $$
  select
    am.*,
    1 - (am.embedding <=> query_embedding) as similarity
  from agent_memories am
  where
    1 - (am.embedding <=> query_embedding) >= p_similarity_threshold and
    (p_agent_id is null or am.agent_id = p_agent_id) and
    (p_mission_id is null or am.mission_id = p_mission_id) and
    (p_memory_type is null or am.memory_type = p_memory_type)
  order by am.embedding <=> query_embedding
  limit p_limit;
$$;

-- Search knowledge artifacts
create or replace function search_knowledge_artifacts(
  query_embedding vector(1536),
  p_mission_id uuid default null,
  p_artifact_type text default null,
  p_title_contains text default null,
  p_limit integer default 10,
  p_similarity_threshold float default 0.6
)
returns table (
  id uuid,
  mission_id uuid,
  artifact_type text,
  title text,
  content text,
  metadata jsonb,
  created_by text,
  created_at timestamptz,
  updated_at timestamptz,
  similarity float
)
language sql stable
as $$
  select
    ka.*,
    1 - (ka.embedding <=> query_embedding) as similarity
  from knowledge_artifacts ka
  where
    1 - (ka.embedding <=> query_embedding) >= p_similarity_threshold and
    (p_mission_id is null or ka.mission_id = p_mission_id) and
    (p_artifact_type is null or ka.artifact_type = p_artifact_type) and
    (p_title_contains is null or ka.title ilike '%' || p_title_contains || '%')
  order by ka.embedding <=> query_embedding
  limit p_limit;
$$;

-- Search semantic events
create or replace function search_semantic_events(
  query_embedding vector(1536),
  p_mission_id uuid default null,
  p_agent_id text default null,
  p_event_type text default null,
  p_limit integer default 20,
  p_similarity_threshold float default 0.6
)
returns table (
  id uuid,
  mission_id uuid,
  agent_id text,
  event_type text,
  description text,
  payload jsonb,
  created_at timestamptz,
  similarity float
)
language sql stable
as $$
  select
    se.*,
    1 - (se.embedding <=> query_embedding) as similarity
  from semantic_events se
  where
    1 - (se.embedding <=> query_embedding) >= p_similarity_threshold and
    (p_mission_id is null or se.mission_id = p_mission_id) and
    (p_agent_id is null or se.agent_id = p_agent_id) and
    (p_event_type is null or se.event_type = p_event_type)
  order by se.embedding <=> query_embedding
  limit p_limit;
$$;

-- Cleanup old records by age (admin function)
create or replace function cleanup_old_memories(
  table_name text,
  older_than_days integer
)
returns integer
language plpgsql
security definer
as $$
declare
  rows_deleted integer;
begin
  execute format('
    delete from %I
    where created_at < (now() - interval ''%s days'')
    returning 1
  ', table_name, older_than_days) into rows_deleted;
  return rows_deleted;
end;
$$;

-- Grant execute on RPC functions to service role (implicitly via owner)
-- No additional grants needed for service role



