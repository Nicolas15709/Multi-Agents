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
