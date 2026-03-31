#!/usr/bin/env node
/**
 * Combine all SQL migrations into a single file for manual Supabase execution
 * Usage: node combine_migrations.js > combined_migrations.sql
 */

import fs from 'node:fs';
import path from 'node:path';

const MIGRATIONS_DIR = path.join(process.cwd(), 'deploy', 'migrations');

function main() {
  if (!fs.existsSync(MIGRATIONS_DIR)) {
    console.error(`Migrations directory not found: ${MIGRATIONS_DIR}`);
    process.exit(1);
  }

  const files = fs.readdirSync(MIGRATIONS_DIR)
    .filter(f => f.endsWith('.sql'))
    .sort();

  console.log(`-- Combined Supabase Migrations`);
  console.log(`-- Generated: ${new Date().toISOString()}`);
  console.log(`-- Files: ${files.length}`);
  console.log(`----------------------------------------\n`);

  for (const file of files) {
    const filePath = path.join(MIGRATIONS_DIR, file);
    console.log(`-- ----------------------------------------`);
    console.log(`-- Migration: ${file}`);
    console.log(`-- ----------------------------------------`);
    const sql = fs.readFileSync(filePath, 'utf8');
    console.log(sql.trim());
    console.log('\n'); // Separate migrations
  }
}

main();
