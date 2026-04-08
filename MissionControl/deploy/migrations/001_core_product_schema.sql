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

