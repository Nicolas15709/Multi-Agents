import fs from 'node:fs';
import path from 'node:path';
import Database from 'better-sqlite3';

const __dirname = path.dirname(new URL(import.meta.url).pathname);
const rootDir = path.resolve(__dirname, '..');
const dbPath = process.env.MISSION_CONTROL_DB || path.join(rootDir, 'data', 'sessions.db');
const schemaPath = path.join(rootDir, 'src', 'schema.sql');
const sessionSchemaPath = path.join(rootDir, 'src', 'session_schema.sql');

export function getDb() {
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  return new Database(dbPath);
}

export function initDb() {
  const db = getDb();
  const schema = fs.readFileSync(schemaPath, 'utf8');
  db.exec(schema);

  // Load session schema if exists
  if (fs.existsSync(sessionSchemaPath)) {
    const sessionSchema = fs.readFileSync(sessionSchemaPath, 'utf8');
    db.exec(sessionSchema);
  }

  return db;
}

export function createRun(db, goal) {
  const stmt = db.prepare(`INSERT INTO runs (goal, status, current_agent) VALUES (?, 'running', 'agent-0')`);
  const info = stmt.run(goal);
  return info.lastInsertRowid;
}

export function updateRun(db, runId, patch = {}) {
  const allowed = ['status', 'current_agent', 'retry_count', 'last_error'];
  const entries = Object.entries(patch).filter(([key]) => allowed.includes(key));
  if (!entries.length) return;
  const setClause = entries.map(([key]) => `${key} = ?`).concat('updated_at = CURRENT_TIMESTAMP').join(', ');
  const values = entries.map(([, value]) => value);
  db.prepare(`UPDATE runs SET ${setClause} WHERE id = ?`).run(...values, runId);
}

export function insertMessage(db, runId, agentId, messageType, content, summary = null, pinned = 0) {
  db.prepare(`INSERT INTO agent_messages (run_id, agent_id, message_type, content, summary, pinned) VALUES (?, ?, ?, ?, ?, ?)`)
    .run(runId, agentId, messageType, content, summary, pinned ? 1 : 0);
}

export function getMessages(db, runId) {
  return db.prepare(`SELECT * FROM agent_messages WHERE run_id = ? ORDER BY id ASC`).all(runId);
}

export function insertTask(db, runId, task) {
  db.prepare(`INSERT INTO task_queue (run_id, task_id, from_agent, to_agent, status, payload_json) VALUES (?, ?, ?, ?, 'pending', ?)`)
    .run(runId, task.task_id, task.from, task.to, JSON.stringify(task));
}

export function updateTaskStatus(db, taskId, status) {
  db.prepare(`UPDATE task_queue SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?`).run(status, taskId);
}

export function insertRetry(db, runId, taskId, agentId, attempt, reason) {
  db.prepare(`INSERT INTO retries (run_id, task_id, agent_id, attempt, reason) VALUES (?, ?, ?, ?, ?)`)
    .run(runId, taskId, agentId, attempt, reason);
}

if (process.argv.includes('--init')) {
  initDb();
  console.log(`Initialized database at ${dbPath}`);
}
