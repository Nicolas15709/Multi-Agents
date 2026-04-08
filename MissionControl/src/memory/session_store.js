/**
 * Session Store for Virtual Agency
 * Manages runtime session state, diffs, and local checkpoints
 */

import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { getDb, initDb } from '../legacy/db.js';
import { zlib } from 'node:zlib';

const SESSION_SCHEMA_PATH = path.join(path.dirname(new URL(import.meta.url).pathname), '..', 'legacy', 'session_schema.sql');

/**
 * Ensure session schema is loaded in SQLite
 */
export function ensureSessionSchema() {
  const db = getDb();
  if (!fs.existsSync(SESSION_SCHEMA_PATH)) {
    throw new Error(`Session schema not found: ${SESSION_SCHEMA_PATH}`);
  }
  const schema = fs.readFileSync(SESSION_SCHEMA_PATH, 'utf8');
  db.exec(schema);
}

/**
 * Create or resume a runtime session
 */
export function createSession(missionId, agentId, sessionToken) {
  ensureSessionSchema();
  const db = getDb();

  // Check if session already exists
  const existing = db.prepare(
    'SELECT id FROM runtime_sessions WHERE session_token = ? AND is_active = 1'
  ).get(sessionToken);

  if (existing) {
    return existing.id;
  }

  const stmt = db.prepare(`
    INSERT INTO runtime_sessions (mission_id, agent_id, session_token, state_json, last_activity)
    VALUES (?, ?, ?, '{}', CURRENT_TIMESTAMP)
  `);
  const info = stmt.run(missionId, agentId, sessionToken);
  return info.lastInsertRowid;
}

/**
 * Get session by token
 */
export function getSession(sessionToken) {
  const db = getDb();
  return db.prepare('SELECT * FROM runtime_sessions WHERE session_token = ?').get(sessionToken);
}

/**
 * Update session state and create a diff entry
 */
export function updateSessionState(sessionToken, newState, diffOperations = null) {
  const db = getDb();
  const session = getSession(sessionToken);
  if (!session) throw new Error(`Session not found: ${sessionToken}`);

  const prevState = JSON.parse(session.state_json || '{}');
  const newStateJson = JSON.stringify(newState);
  const prevHash = calculateStateHash(prevState);
  const newHash = calculateStateHash(newState);

  // Update session
  db.prepare(`
    UPDATE runtime_sessions
    SET state_json = ?, last_activity = CURRENT_TIMESTAMP, token_usage = token_usage + ?
    WHERE session_token = ?
  `).run(newStateJson, estimateTokenDelta(prevState, newState), sessionToken);

  // Calculate diff if not provided
  if (diffOperations === null) {
    diffOperations = computeJsonDiff(prevState, newState);
  }

  // Insert diff if there are changes
  if (Object.keys(diffOperations).length > 0) {
    const seq = db.prepare(`
      SELECT COALESCE(MAX(seq_num), 0) + 1 as next_seq
      FROM session_diffs
      WHERE session_id = ?
    `).get(session.id).next_seq;

    db.prepare(`
      INSERT INTO session_diffs (session_id, seq_num, diff_json, prev_state_hash, new_state_hash)
      VALUES (?, ?, ?, ?, ?)
    `).run(session.id, seq, JSON.stringify(diffOperations), prevHash, newHash);
  }

  return { prevHash, newHash, diff: diffOperations };
}

/**
 * Replay session state from a given checkpoint
 */
export function replaySessionToCheckpoint(sessionToken, checkpointId = null) {
  const db = getDb();
  const session = getSession(sessionToken);
  if (!session) throw new Error(`Session not found: ${sessionToken}`);

  let baseState = {};
  let startSeq = 0;

  if (checkpointId) {
    // Load checkpoint state from associated snapshot
    const checkpoint = db.prepare(`
      SELECT sc.*, ss.snapshot_data
      FROM session_checkpoints sc
      JOIN session_snapshots ss ON sc.supabase_snapshot_id = ss.id
      WHERE sc.id = ? AND sc.session_id = ?
    `).get(checkpointId, session.id);

    if (checkpoint) {
      baseState = JSON.parse(zlib.inflateSync(Buffer.from(checkpoint.snapshot_data, 'base64')).toString());
      // Find diffs after checkpoint
      const minSeq = db.prepare(`
        SELECT seq_num FROM session_diffs
        WHERE session_id = ? AND created_at > (SELECT created_at FROM session_checkpoints WHERE id = ?)
        ORDER BY seq_num ASC LIMIT 1
      `).get(session.id, checkpointId);
      startSeq = minSeq ? minSeq.seq_num : 0;
    }
  }

  // Replay diffs from startSeq onwards
  const diffs = db.prepare(`
    SELECT diff_json FROM session_diffs
    WHERE session_id = ? AND seq_num >= ?
    ORDER BY seq_num ASC
  `).all(session.id, startSeq);

  let currentState = baseState;
  for (const diffRow of diffs) {
    const diff = JSON.parse(diffRow.diff_json);
    currentState = applyJsonPatch(currentState, diff);
  }

  return currentState;
}

/**
 * Create a checkpoint linking to Supabase snapshot
 */
export function createCheckpoint(sessionToken, supabaseSnapshotId, type = 'automatic', reason = null) {
  const db = getDb();
  const session = getSession(sessionToken);
  if (!session) throw new Error(`Session not found: ${sessionToken}`);

  const stmt = db.prepare(`
    INSERT INTO session_checkpoints (session_id, supabase_snapshot_id, checkpoint_type, reason)
    VALUES (?, ?, ?, ?)
  `);
  const info = stmt.run(session.id, supabaseSnapshotId, type, reason);
  return info.lastInsertRowid;
}

/**
 * Get session diffs since last checkpoint
 */
export function getSessionDiffsSinceCheckpoint(sessionToken) {
  const db = getDb();
  const session = getSession(sessionToken);
  if (!session) return [];

  const lastCheckpoint = db.prepare(`
    SELECT created_at FROM session_checkpoints
    WHERE session_id = ? ORDER BY created_at DESC LIMIT 1
  `).get(session.id);

  if (!lastCheckpoint) {
    return db.prepare(`
      SELECT seq_num, diff_json, created_at FROM session_diffs
      WHERE session_id = ? ORDER BY seq_num ASC
    `).all(session.id);
  }

  return db.prepare(`
    SELECT seq_num, diff_json, created_at FROM session_diffs
    WHERE session_id = ? AND created_at >= ?
    ORDER BY seq_num ASC
  `).all(session.id, lastCheckpoint.created_at);
}

/**
 * Compute JSON diff (simple key-level diff, not RFC 6902 full patch)
 */
function computeJsonDiff(oldState, newState) {
  const diff = {};

  // Detect added/changed keys
  for (const key of Object.keys(newState)) {
    if (!Object.prototype.hasOwnProperty.call(oldState, key)) {
      diff[key] = { op: 'add', value: newState[key] };
    } else if (JSON.stringify(oldState[key]) !== JSON.stringify(newState[key])) {
      diff[key] = { op: 'replace', value: newState[key] };
    }
  }

  // Detect removed keys
  for (const key of Object.keys(oldState)) {
    if (!Object.prototype.hasOwnProperty.call(newState, key)) {
      diff[key] = { op: 'remove' };
    }
  }

  return diff;
}

/**
 * Apply JSON diff to reconstruct state
 */
function applyJsonPatch(state, diff) {
  const newState = { ...state };
  for (const [key, operation] of Object.entries(diff)) {
    if (operation.op === 'add' || operation.op === 'replace') {
      newState[key] = operation.value;
    } else if (operation.op === 'remove') {
      delete newState[key];
    }
  }
  return newState;
}

/**
 * Calculate a simple hash for state comparison
 */
function calculateStateHash(state) {
  return createHash('sha256').update(JSON.stringify(state, Object.keys(state).sort())).digest('hex');
}

/**
 * Estimate token delta between states (rough approximation)
 */
function estimateTokenDelta(oldState, newState) {
  const oldStr = JSON.stringify(oldState);
  const newStr = JSON.stringify(newState);
  // 1 token â‰ˆ 4 characters (very rough)
  return Math.max(0, Math.floor((newStr.length - oldStr.length) / 4));
}

/**
 * TTL cleanup: deactivate old sessions
 */
export function cleanupOldSessions(maxAgeDays = 7) {
  const db = getDb();
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - maxAgeDays);

  const stmt = db.prepare(`
    UPDATE runtime_sessions
    SET is_active = 0
    WHERE is_active = 1 AND datetime(last_activity) < datetime(?)
  `);
  const info = stmt.run(cutoff.toISOString());
  return info.changes;
}

/**
 * Purge old diffs beyond checkpoint retention limit
 */
export function purgeOldDiffs(keepCheckpoints = 10) {
  const db = getDb();
  const rows = db.prepare(`
    SELECT session_id, seq_num FROM session_diffs
    WHERE (session_id, seq_num) IN (
      SELECT session_id, seq_num FROM session_diffs sd
      WHERE seq_num < (
        SELECT seq_num FROM session_diffs sd2
        WHERE sd2.session_id = sd.session_id
        ORDER BY seq_num DESC
        LIMIT 1 OFFSET ?
      )
    )
  `).all(keepCheckpoints);

  for (const row of rows) {
    db.prepare('DELETE FROM session_diffs WHERE session_id = ? AND seq_num = ?')
      .run(row.session_id, row.seq_num);
  }

  return rows.length;
}

/**
 * Get sync queue for background processing
 */
export function getPendingSyncQueue() {
  const db = getDb();
  return db.prepare(`
    SELECT * FROM memory_sync_queue
    WHERE status = 'pending'
    ORDER BY created_at ASC
    LIMIT 50
  `).all();
}

/**
 * Mark sync item as completed
 */
export function markSyncComplete(queueId) {
  const db = getDb();
  db.prepare('DELETE FROM memory_sync_queue WHERE id = ?').run(queueId);
}

/**
 * Queue a sync operation
 */
export function queueSyncOperation(direction, tableName, recordId, payload) {
  const db = getDb();
  const stmt = db.prepare(`
    INSERT INTO memory_sync_queue (direction, table_name, record_id, payload_json)
    VALUES (?, ?, ?, ?)
  `);
  return stmt.run(direction, tableName, recordId, JSON.stringify(payload)).lastInsertRowid;
}

