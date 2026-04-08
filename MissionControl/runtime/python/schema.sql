CREATE TABLE IF NOT EXISTS missions (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  goal TEXT NOT NULL,
  mode TEXT NOT NULL,
  priority TEXT NOT NULL,
  status TEXT NOT NULL,
  source TEXT NOT NULL,
  schedule TEXT,
  allow_24x7 INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mission_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  actor TEXT,
  summary TEXT NOT NULL,
  payload_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(mission_id) REFERENCES missions(id)
);

CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  mission_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  priority TEXT NOT NULL,
  depends_on TEXT,
  details_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(mission_id) REFERENCES missions(id)
);

CREATE TABLE IF NOT EXISTS agent_status (
  agent_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  role TEXT NOT NULL,
  state TEXT NOT NULL,
  active_mission_id TEXT,
  current_task_id TEXT,
  personality TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_profiles (
  agent_id TEXT PRIMARY KEY,
  reports_to TEXT,
  capabilities_json TEXT,
  budget_monthly_cents INTEGER NOT NULL DEFAULT 0,
  origin TEXT NOT NULL DEFAULT 'core',
  mission_scope_id TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(agent_id) REFERENCES agent_status(agent_id),
  FOREIGN KEY(mission_scope_id) REFERENCES missions(id)
);

CREATE TABLE IF NOT EXISTS agent_hire_requests (
  id TEXT PRIMARY KEY,
  mission_id TEXT NOT NULL,
  requested_by_agent_id TEXT,
  display_name TEXT NOT NULL,
  role TEXT NOT NULL,
  personality TEXT,
  capabilities_json TEXT,
  budget_monthly_cents INTEGER NOT NULL DEFAULT 0,
  reports_to TEXT,
  notes TEXT,
  status TEXT NOT NULL,
  hired_agent_id TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(mission_id) REFERENCES missions(id),
  FOREIGN KEY(hired_agent_id) REFERENCES agent_status(agent_id)
);

CREATE TABLE IF NOT EXISTS mission_controls (
  mission_id TEXT PRIMARY KEY,
  max_autonomous_steps INTEGER NOT NULL DEFAULT 18,
  autonomous_steps_used INTEGER NOT NULL DEFAULT 0,
  max_estimated_tokens INTEGER NOT NULL DEFAULT 16000,
  estimated_tokens_used INTEGER NOT NULL DEFAULT 0,
  max_runtime_ticks INTEGER NOT NULL DEFAULT 64,
  runtime_ticks_used INTEGER NOT NULL DEFAULT 0,
  max_dynamic_hires INTEGER NOT NULL DEFAULT 3,
  dynamic_hires_used INTEGER NOT NULL DEFAULT 0,
  action_budgets_json TEXT,
  action_usage_json TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(mission_id) REFERENCES missions(id)
);

CREATE TABLE IF NOT EXISTS mission_memory_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id TEXT NOT NULL,
  source_task_id TEXT,
  author_agent_id TEXT,
  scope TEXT NOT NULL DEFAULT 'mission',
  memory_key TEXT,
  summary TEXT NOT NULL,
  content_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(mission_id) REFERENCES missions(id)
);

CREATE TABLE IF NOT EXISTS agent_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id TEXT NOT NULL,
  from_agent_id TEXT,
  to_agent_id TEXT,
  source_task_id TEXT,
  target_task_id TEXT,
  kind TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  summary TEXT NOT NULL,
  payload_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(mission_id) REFERENCES missions(id)
);

CREATE TABLE IF NOT EXISTS action_approvals (
  id TEXT PRIMARY KEY,
  mission_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  requested_by_agent_id TEXT,
  action_kind TEXT NOT NULL,
  policy_mode TEXT NOT NULL,
  status TEXT NOT NULL,
  reason TEXT,
  approved_by TEXT,
  decision_notes TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(mission_id) REFERENCES missions(id),
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS policies (
  id TEXT PRIMARY KEY,
  integration TEXT NOT NULL,
  account_resource TEXT NOT NULL,
  action TEXT NOT NULL,
  mode TEXT NOT NULL,
  conditions_json TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel TEXT NOT NULL,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  summary TEXT NOT NULL,
  payload_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS intake_requests (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL,
  priority TEXT NOT NULL,
  requested_by TEXT,
  channel TEXT NOT NULL,
  source TEXT NOT NULL,
  mode TEXT,
  fingerprint TEXT,
  mission_id TEXT,
  details_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(mission_id) REFERENCES missions(id)
);

CREATE INDEX IF NOT EXISTS idx_intake_requests_status_created
  ON intake_requests(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_intake_requests_fingerprint
  ON intake_requests(fingerprint);

CREATE INDEX IF NOT EXISTS idx_agent_messages_mission_status
  ON agent_messages(mission_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_action_approvals_mission_status
  ON action_approvals(mission_id, status, created_at DESC);
