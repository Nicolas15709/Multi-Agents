#!/usr/bin/env node
/**
 * Supabase Migration Applier
 * Applies all pending .sql migrations to Supabase via REST API
 * Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars
 */

import fs from 'node:fs';
import path from 'node:path';
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
dotenv.config();

const { SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY } = process.env;

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error('Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables are required');
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

const MIGRATIONS_DIR = path.join(process.cwd(), 'deploy', 'migrations');

async function getAppliedMigrations() {
  const { data, error } = await supabase
    .from('_ migrations')
    .select('name')
    .order('created_at', { ascending: true });

  if (error) {
    // Table may not exist yet
    if (error.code === '42P01') { // undefined_table
      return [];
    }
    throw error;
  }

  return data.map(m => m.name);
}

async function applyMigration(name, sql) {
  console.log(`[Migration] Applying ${name}...`);

  // Supabase PostgREST does not support raw SQL execution directly.
  // Use the SQL API via the PostgREST /rpc endpoint if a stored proc exists,
  // otherwise we must use psql or the dashboard.
  // Here we will print instructions for manual execution if direct exec fails.

  try {
    // Try to use the supabase sql execution via background tasks
    // This is advanced; simpler approach: output to file and instruct manual
    const { error } = await supabase.functions.invoke('execute-sql', {
      body: { sql }
    });

    if (error) {
      throw error;
    }

    console.log(`[Migration] Applied ${name} via Edge Function`);
  } catch (err) {
    console.warn(`[Migration] Could not apply via API (likely no Edge Function).`);
    console.log(`[Migration] MANUAL ACTION REQUIRED:`);
    console.log(`  1. Open Supabase dashboard SQL Editor`);
    console.log(`  2. Run the following from file: deploy/migrations/${name}`);
    console.log(`  3. After success, record this migration manually in _migrations table.`);
    process.exitCode = 2;
  }
}

async function main() {
  if (!fs.existsSync(MIGRATIONS_DIR)) {
    console.error(`Migrations directory not found: ${MIGRATIONS_DIR}`);
    process.exit(1);
  }

  const files = fs.readdirSync(MIGRATIONS_DIR)
    .filter(f => f.endsWith('.sql'))
    .sort();

  if (files.length === 0) {
    console.log('No migrations found.');
    return;
  }

  console.log(`Found ${files.length} migrations. Checking applied status...`);

  const applied = await getAppliedMigrations();
  const pending = files.filter(f => !applied.includes(f));

  if (pending.length === 0) {
    console.log('All migrations are already applied.');
    return;
  }

  console.log(`Pending migrations: ${pending.join(', ')}`);

  for (const file of pending) {
    const filePath = path.join(MIGRATIONS_DIR, file);
    const sql = fs.readFileSync(filePath, 'utf8');
    await applyMigration(file, sql);

    // Record in _migrations table manually if API didn't
    // This table is managed by Supabase Migrations feature
    // For our custom system, we might need to create it manually:
    // CREATE TABLE _migrations (name text primary key, applied_at timestamptz default now());
    try {
      await supabase.from('_migrations').upsert({ name: file }).select();
    } catch (e) {
      // ignore if table doesn't exist
    }
  }

  console.log('Migration process complete.');
}

main().catch(err => {
  console.error('Migration failed:', err);
  process.exit(1);
});
