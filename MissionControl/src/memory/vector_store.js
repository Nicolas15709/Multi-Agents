/**
 * Vector Store for Supabase pgvector integration
 * Handles semantic search, insertions, and CRUD operations
 */

import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
dotenv.config();

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY; // Service role for bypassing RLS

if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
  throw new Error('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables');
}

export const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

/**
 * Insert a memory into agent_memories table
 */
export async function insertAgentMemory(params) {
  const {
    agent_id,
    mission_id,
    session_id,
    content,
    embedding,
    metadata = {},
    memory_type = 'observation',
    importance = 1.0
  } = params;

  const { data, error } = await supabase
    .from('agent_memories')
    .insert({
      agent_id,
      mission_id,
      session_id,
      content,
      embedding,
      metadata,
      memory_type,
      importance
    })
    .select()
    .single();

  if (error) throw error;
  return data;
}

/**
 * Insert a semantic event
 */
export async function insertSemanticEvent(params) {
  const {
    mission_id,
    agent_id,
    event_type,
    description,
    embedding,
    payload = {}
  } = params;

  const { data, error } = await supabase
    .from('semantic_events')
    .insert({
      mission_id,
      agent_id,
      event_type,
      description,
      embedding,
      payload
    })
    .select()
    .single();

  if (error) throw error;
  return data;
}

/**
 * Insert a knowledge artifact
 */
export async function insertKnowledgeArtifact(params) {
  const {
    mission_id,
    artifact_type,
    title,
    content,
    embedding,
    metadata = {},
    created_by
  } = params;

  const { data, error } = await supabase
    .from('knowledge_artifacts')
    .insert({
      mission_id,
      artifact_type,
      title,
      content,
      embedding,
      metadata,
      created_by
    })
    .select()
    .single();

  if (error) throw error;
  return data;
}

/**
 * Upload a session snapshot to Supabase
 */
export async function insertSessionSnapshot(params) {
  const {
    mission_id,
    session_token,
    snapshot_data, // Buffer -> base64
    diff_base,
    agent_states = {},
    checksum,
    expires_at
  } = params;

  // Convert Buffer to base64 string for JSONB compatibility
  const snapshotBase64 = snapshot_data instanceof Buffer
    ? snapshot_data.toString('base64')
    : snapshot_data;

  const { data, error } = await supabase
    .from('session_snapshots')
    .insert({
      mission_id,
      session_token,
      snapshot_data: snapshotBase64,
      diff_base,
      agent_states,
      checksum,
      expires_at
    })
    .select()
    .single();

  if (error) throw error;
  return data;
}

/**
 * Semantic search across agent memories
 */
export async function searchAgentMemories(params) {
  const {
    query_embedding,
    agent_id,
    mission_id,
    memory_type,
    limit = 10,
    similarity_threshold = 0.7
  } = params;

  let query = supabase
    .from('agent_memories')
    .select('*, similarity: 1 - (embedding <=> query_embedding)')
    .order('embedding <=> query_embedding', { ascending: true })
    .limit(limit);

  if (agent_id) query = query.eq('agent_id', agent_id);
  if (mission_id) query = query.eq('mission_id', mission_id);
  if (memory_type) query = query.eq('memory_type', memory_type);

  const { data, error } = await query;
  if (error) throw error;

  // Filter by threshold client-side
  return data.filter(item => item.similarity >= similarity_threshold);
}

/**
 * Semantic search across knowledge artifacts
 */
export async function searchKnowledgeArtifacts(params) {
  const {
    query_embedding,
    mission_id,
    artifact_type,
    title_contains,
    limit = 10,
    similarity_threshold = 0.6
  } = params;

  let query = supabase
    .from('knowledge_artifacts')
    .select('*, similarity: 1 - (embedding <=> query_embedding)')
    .order('embedding <=> query_embedding', { ascending: true })
    .limit(limit);

  if (mission_id) query = query.eq('mission_id', mission_id);
  if (artifact_type) query = query.eq('artifact_type', artifact_type);
  if (title_contains) query = query.ilike('title', `%${title_contains}%`);

  const { data, error } = await query;
  if (error) throw error;

  return data.filter(item => item.similarity >= similarity_threshold);
}

/**
 * Retrieve recent memories for an agent (chronological fallback)
 */
export async function getRecentMemories(agentId, options = {}) {
  const { limit = 50, mission_id, memory_type } = options;

  let query = supabase
    .from('agent_memories')
    .select('*')
    .eq('agent_id', agentId)
    .order('created_at', { ascending: false })
    .limit(limit);

  if (mission_id) query = query.eq('mission_id', mission_id);
  if (memory_type) query = query.eq('memory_type', memory_type);

  const { data, error } = await query;
  if (error) throw error;
  return data;
}

/**
 * Semantic search across semantic events
 */
export async function searchSemanticEvents(params) {
  const {
    query_embedding,
    mission_id,
    agent_id,
    event_type,
    limit = 20,
    similarity_threshold = 0.6
  } = params;

  let query = supabase
    .from('semantic_events')
    .select('*, similarity: 1 - (embedding <=> query_embedding)')
    .order('embedding <=> query_embedding', { ascending: true })
    .limit(limit);

  if (mission_id) query = query.eq('mission_id', mission_id);
  if (agent_id) query = query.eq('agent_id', agent_id);
  if (event_type) query = query.eq('event_type', event_type);

  const { data, error } = await query;
  if (error) throw error;

  return data.filter(item => item.similarity >= similarity_threshold);
}

/**
 * Delete old memories based on TTL
 */
export async function cleanupOldMemories(params) {
  const { table = 'agent_memories', older_than_days = 180 } = params;
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - older_than_days);

  const { data, error } = await supabase
    .from(table)
    .delete()
    .lt('created_at', cutoff.toISOString())
    .select('id');

  if (error) throw error;
  return { deleted: data.length, ids: data.map(r => r.id) };
}

/**
 * Log cleanup operation for audit
 */
export async function logMemoryCleanup(params) {
  const { table_name, records_deleted, cleanup_reason } = params;

  const { error } = await supabase
    .from('memory_cleanup_log')
    .insert({
      table_name,
      records_deleted,
      cleanup_reason
    });

  if (error) throw error;
}
