-- SQLite schema for session state management
-- This complements the legacy schema.sql (runs, task_queue, etc.)
-- Run this as a separate migration or merge into schema.sql

-- Runtime sessions (current active state per agent/mission)
CREATE TABLE IF NOT EXISTS runtime_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id TEXT NOT NULL, -- UUID string or legacy run_id
  agent_id TEXT NOT NULL,
  session_token TEXT UNIQUE NOT NULL,
  state_json TEXT NOT NULL DEFAULT '{}',
  context_window INTEGER NOT NULL DEFAULT 0,
  token_usage INTEGER NOT NULL DEFAULT 0,
  last_activity TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS runtime_sessions_mission_idx ON runtime_sessions(mission_id);
CREATE INDEX IF NOT EXISTS runtime_sessions_agent_idx ON runtime_sessions(agent_id);
CREATE INDEX IF NOT EXISTS runtime_sessions_active_idx ON runtime_sessions(is_active, last_activity);

-- Session diffs (state changes for replay/resume)
CREATE TABLE IF NOT EXISTS session_diffs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL REFERENCES runtime_sessions(id) ON DELETE CASCADE,
  seq_num INTEGER NOT NULL, -- sequence number within session
  diff_json TEXT NOT NULL, -- JSON Patch operations
  prev_state_hash TEXT NOT NULL,
  new_state_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(session_id, seq_num)
);

CREATE INDEX IF NOT EXISTS session_diffs_session_idx ON session_diffs(session_id);
CREATE INDEX IF NOT EXISTS session_diffs_seq_idx ON session_diffs(session_id, seq_num);

-- Session checkpoint metadata (links to snapshot in Supabase)
CREATE TABLE IF NOT EXISTS session_checkpoints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL REFERENCES runtime_sessions(id) ON DELETE CASCADE,
  supabase_snapshot_id UUID, -- Foreign key to session_snapshots.id
  local_snapshot_path TEXT, -- Fallback local path
  checkpoint_type TEXT NOT NULL DEFAULT 'automatic', -- automatic, manual, pre_agent_switch
  reason TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS session_checkpoints_session_idx ON session_checkpoints(session_id);
CREATE INDEX IF NOT EXISTS session_checkpoints_created_idx ON session_checkpoints(created_at DESC);

-- Memory bridge: local SQLite <-> Supabase vector (for syncing recent items)
CREATE TABLE IF NOT EXISTS memory_sync_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  direction TEXT NOT NULL CHECK(direction IN ('local_to_supabase', 'supabase_to_local')),
  table_name TEXT NOT NULL,
  record_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS memory_sync_queue_status_idx ON memory_sync_queue(status, created_at);
CREATE INDEX IF NOT EXISTS memory_sync_queue_direction_idx ON memory_sync_queue(direction);

-- Session TTL tracking (for cleanup policies)
CREATE TABLE IF NOT EXISTS session_ttl_policies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_type TEXT NOT NULL UNIQUE, -- runtime, snapshot, archive
  max_age_days INTEGER NOT NULL,
  max_snapshots_per_session INTEGER NOT NULL DEFAULT 10,
  cleanup_interval_hours INTEGER NOT NULL DEFAULT 24,
  last_cleanup_run TEXT,
  CONSTRAINT valid_max_age CHECK(max_age_days > 0)
);

INSERT OR REPLACE INTO session_ttl_policies (session_type, max_age_days, max_snapshots_per_session, cleanup_interval_hours)
VALUES
  ('runtime', 7, 100, 6),
  ('snapshot', 90, 50, 24),
  ('archive', 365, 1, 168);
