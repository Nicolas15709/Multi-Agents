-- Placeholder RLS policies. Adjust after auth strategy is confirmed.

alter table profiles enable row level security;
alter table projects enable row level security;
alter table missions enable row level security;
alter table mission_events enable row level security;
alter table saved_artifacts enable row level security;
alter table ui_preferences enable row level security;

-- Example starter policy pattern:
-- create policy "users can read own profile"
-- on profiles for select
-- using (auth.uid() = id);
