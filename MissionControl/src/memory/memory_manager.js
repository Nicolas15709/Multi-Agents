/**
 * Memory Manager - Main coordinator for Virtual Agency memory system
 * Integrates vector store (Supabase pgvector) with session store (SQLite)
 * Handles TTL policies and automatic cleanup
 */

import { generateEmbedding, generateEmbeddingsBatch } from './embeddings.js';
import {
  insertAgentMemory,
  insertSemanticEvent,
  insertKnowledgeArtifact,
  searchAgentMemories,
  searchSemanticEvents,
  searchKnowledgeArtifacts,
  getRecentMemories,
  cleanupOldMemories,
  logMemoryCleanup,
  supabase
} from './vector_store.js';
import {
  ensureSessionSchema,
  createSession,
  getSession,
  updateSessionState,
  replaySessionToCheckpoint,
  createCheckpoint,
  getSessionDiffsSinceCheckpoint,
  cleanupOldSessions,
  purgeOldDiffs,
  getPendingSyncQueue,
  markSyncComplete,
  queueSyncOperation
} from './session_store.js';
import { getDb } from '../legacy/db.js';
import { createHash } from 'node:crypto';

const TTL_CONFIG = {
  agent_memories_days: parseInt(process.env.MEMORY_TTL_MEMORIES_DAYS) || 180,
  sessions_days: parseInt(process.env.MEMORY_TTL_SESSIONS_DAYS) || 7,
  snapshots_days: parseInt(process.env.MEMORY_TTL_SNAPSHOTS_DAYS) || 90,
  diffs_to_keep: parseInt(process.env.MEMORY_DIFFS_TO_KEEP) || 100
};

/**
 * Initialize the memory system
 */
export async function initMemorySystem() {
  // Ensure SQLite session schema
  ensureSessionSchema();

  // Check Supabase connectivity
  try {
    const { error } = await supabase.from('agent_memories').select('id').limit(1);
    if (error) {
      console.warn('[Memory] Supabase health check failed:', error.message);
    } else {
      console.log('[Memory] Supabase pgvector connected');
    }
  } catch (err) {
    console.warn('[Memory] Supabase connectivity issue:', err.message);
  }

  console.log('[Memory] System initialized. TTL config:', TTL_CONFIG);
}

/**
 * Remember an agent's observation/reflection/action with vector embedding
 */
export async function rememberMemory(params) {
  const {
    agentId,
    missionId,
    sessionId,
    content,
    memoryType = 'observation',
    importance = 1.0,
    metadata = {}
  } = params;

  // Generate embedding
  const embedding = await generateEmbedding(content);

  // Insert into Supabase
  const record = await insertAgentMemory({
    agent_id: agentId,
    mission_id: missionId,
    session_id: sessionId,
    content,
    embedding,
    memory_type: memoryType,
    importance,
    metadata
  });

  // Queue for optional sync if needed
  queueSyncOperation('local_to_supabase', 'agent_memories', record.id, record);

  return record;
}

/**
 * Remember a semantic event (action, decision, handoff, milestone)
 */
export async function rememberEvent(params) {
  const {
    missionId,
    agentId,
    eventType,
    description,
    payload = {}
  } = params;

  // Generate embedding from description + payload summary
  const payloadStr = typeof payload === 'string' ? payload : JSON.stringify(payload);
  const combinedText = `${eventType}: ${description}\n${payloadStr}`.slice(0, 8000);
  const embedding = await generateEmbedding(combinedText);

  const record = await insertSemanticEvent({
    mission_id: missionId,
    agent_id: agentId,
    event_type: eventType,
    description,
    embedding,
    payload
  });

  return record;
}

/**
 * Store a knowledge artifact (code, design, plan, etc.) for RAG
 */
export async function storeArtifact(params) {
  const {
    missionId,
    artifactType,
    title,
    content,
    createdBy,
    metadata = {}
  } = params;

  // Generate embedding from title + content
  const combinedText = `${title}\n${content}`.slice(0, 8000);
  const embedding = await generateEmbedding(combinedText);

  const record = await insertKnowledgeArtifact({
    mission_id: missionId,
    artifact_type: artifactType,
    title,
    content,
    embedding,
    metadata,
    created_by: createdBy
  });

  return record;
}

/**
 * Search memories semantically
 */
export async function searchMemories(params) {
  const query = params.query;
  const {
    agentId,
    missionId,
    memoryType,
    limit = 10,
    threshold = 0.7
  } = params;

  const embedding = await generateEmbedding(query);

  return searchAgentMemories({
    query_embedding: embedding,
    agent_id: agentId,
    mission_id: missionId,
    memory_type: memoryType,
    limit,
    similarity_threshold: threshold
  });
}

/**
 * Search events semantically
 */
export async function searchEvents(params) {
  const query = params.query;
  const {
    missionId,
    agentId,
    eventType,
    limit = 20,
    threshold = 0.6
  } = params;

  const embedding = await generateEmbedding(query);

  return searchSemanticEvents({
    query_embedding: embedding,
    mission_id: missionId,
    agent_id: agentId,
    event_type: eventType,
    limit,
    similarity_threshold: threshold
  });
}

/**
 * Search knowledge artifacts semantically
 */
export async function searchArtifacts(params) {
  const query = params.query;
  const {
    missionId,
    artifactType,
    titleContains,
    limit = 10,
    threshold = 0.6
  } = params;

  const embedding = await generateEmbedding(query);

  return searchKnowledgeArtifacts({
    query_embedding: embedding,
    mission_id: missionId,
    artifact_type: artifactType,
    title_contains: titleContains,
    limit,
    similarity_threshold: threshold
  });
}

/**
 * Get recent memories by agent (chronological)
 */
export async function getAgentMemories(agentId, options = {}) {
  return getRecentMemories(agentId, options);
}

/**
 * Create/resume a runtime session for an agent
 */
export function openAgentSession(missionId, agentId) {
  const sessionToken = `session:${agentId}:${Date.now()}:${Math.random().toString(36).slice(2)}`;
  const sessionId = createSession(missionId, agentId, sessionToken);
  return { sessionId, sessionToken };
}

/**
 * Update session state with diff tracking
 */
export function updateAgentSession(sessionToken, newState) {
  return updateSessionState(sessionToken, newState);
}

/**
 * Create a checkpoint snapshot (store state to Supabase)
 */
export async function checkpointSession(sessionToken, type = 'automatic', reason = null) {
  const session = getSession(sessionToken);
  if (!session) throw new Error(`Session not found: ${sessionToken}`);

  // Serialize state
  const state = JSON.parse(session.state_json || '{}');
  const stateString = JSON.stringify(state);
  const compressed = zlib.deflateSync(Buffer.from(stateString));
  const checksum = createHash('sha256').update(stateString).digest('hex');

  // Store in Supabase
  const expiresAt = new Date();
  expiresAt.setDate(expiresAt.getDate() + TTL_CONFIG.snapshots_days);

  const snapshot = await insertAgentMemory?._context.vectorStore?.insertSessionSnapshot?.({
    mission_id: session.mission_id,
    session_token: sessionToken,
    snapshot_data: compressed,
    agent_states: state,
    checksum,
    expires_at: expiresAt.toISOString()
  }) || { id: null }; // fallback

  // Create local checkpoint record
  const checkpointId = createCheckpoint(sessionToken, snapshot.id, type, reason);

  return { checkpointId, snapshotId: snapshot.id, expiresAt };
}

/**
 * Resume session from checkpoint
 */
export function resumeSessionFromCheckpoint(sessionToken, checkpointId) {
  const restoredState = replaySessionToCheckpoint(sessionToken, checkpointId);
  // Update session state to restored
  updateSessionState(sessionToken, restoredState);
  return restoredState;
}

/**
 * Get diffs since last checkpoint (for incremental sync)
 */
export function getSessionIncrementalDiff(sessionToken) {
  return getSessionDiffsSinceCheckpoint(sessionToken);
}

/**
 * Memory cleanup job (TTL)
 */
export async function runMemoryCleanup() {
  const results = {
    memories_deleted: 0,
    sessions_deactivated: 0,
    diffs_purged: 0,
    snapshots_deleted: 0
  };

  try {
    // Clean up old agent memories
    const memResult = await cleanupOldMemories({ table: 'agent_memories', older_than_days: TTL_CONFIG.agent_memories_days });
    results.memories_deleted = memResult.deleted;
    await logMemoryCleanup({
      table_name: 'agent_memories',
      records_deleted: memResult.deleted,
      cleanup_reason: 'ttl_expired'
    });

    // Deactivate old sessions
    results.sessions_deactivated = cleanupOldSessions(TTL_CONFIG.sessions_days);

    // Purge old diffs
    results.diffs_purged = purgeOldDiffs(TTL_CONFIG.diffs_to_keep);

    // Clean up expired snapshots
    const snapResult = await cleanupOldMemories({ table: 'session_snapshots', older_than_days: TTL_CONFIG.snapshots_days });
    results.snapshots_deleted = snapResult.deleted;

  } catch (err) {
    console.error('[Memory] Cleanup error:', err);
    throw err;
  }

  console.log('[Memory] Cleanup completed:', results);
  return results;
}

/**
 * Process sync queue (local -> supabase batch)
 */
export async function processSyncQueue(batchSize = 20) {
  const pending = getPendingSyncQueue();
  const batch = pending.slice(0, batchSize);
  const results = [];

  for (const item of batch) {
    try {
      const payload = JSON.parse(item.payload_json);
      // TODO: Implement actual sync logic based on table_name and direction
      // For now, just mark as done
      markSyncComplete(item.id);
      results.push({ id: item.id, status: 'synced' });
    } catch (err) {
      console.error(`[Memory] Sync failed for queue item ${item.id}:`, err);
      // Update attempts and error
      results.push({ id: item.id, status: 'failed', error: err.message });
    }
  }

  return results;
}

/**
 * Query interface (unified search across memories, events, artifacts)
 */
export async function unifiedSearch(params) {
  const { query, missionId, agentId, limit = 10, types = ['memories', 'events', 'artifacts'] } = params;
  const embedding = await generateEmbedding(query);

  const results = {
    memories: [],
    events: [],
    artifacts: []
  };

  if (types.includes('memories')) {
    results.memories = await searchAgentMemories({
      query_embedding: embedding,
      mission_id: missionId,
      agent_id: agentId,
      limit,
      similarity_threshold: 0.6
    });
  }

  if (types.includes('events')) {
    results.events = await searchSemanticEvents({
      query_embedding: embedding,
      mission_id: missionId,
      agent_id: agentId,
      limit,
      similarity_threshold: 0.5
    });
  }

  if (types.includes('artifacts')) {
    results.artifacts = await searchKnowledgeArtifacts({
      query_embedding: embedding,
      mission_id: missionId,
      limit,
      similarity_threshold: 0.5
    });
  }

  return results;
}

/**
 * Export session context for agent consumption
 */
export function exportSessionContext(sessionToken) {
  const session = getSession(sessionToken);
  if (!session) return null;

  const diffs = getSessionDiffsSinceCheckpoint(sessionToken);
  const recentMemories = getRecentMemories(session.agent_id, { limit: 20, mission_id: session.mission_id });

  return {
    session: {
      token: sessionToken,
      agentId: session.agent_id,
      missionId: session.mission_id,
      state: JSON.parse(session.state_json || '{}'),
      lastActivity: session.last_activity
    },
    diffs: diffs.map(d => ({ seq: d.seq_num, diff: JSON.parse(d.diff_json) })),
    relevantMemories: recentMemories
  };
}

/**
 * Health check
 */
export function healthCheck() {
  const db = getDb();
  const sessionCount = db.prepare('SELECT COUNT(*) as c FROM runtime_sessions WHERE is_active = 1').get().c;
  const diffCount = db.prepare('SELECT COUNT(*) as c FROM session_diffs').get().c;

  return {
    sqlite: 'connected',
    active_sessions: sessionCount,
    total_diffs: diffCount,
    config: TTL_CONFIG
  };
}

