import 'dotenv/config';

export function getSupabaseConfig() {
  return {
    url: process.env.SUPABASE_URL || '',
    anonKey: process.env.SUPABASE_ANON_KEY || '',
    enabled: Boolean(process.env.SUPABASE_URL && process.env.SUPABASE_ANON_KEY)
  };
}

export async function publishMissionEvent(event) {
  const config = getSupabaseConfig();
  if (!config.enabled) {
    return { skipped: true, reason: 'Supabase not configured' };
  }

  return {
    skipped: true,
    reason: 'Supabase client wiring pending explicit credentials and package installation',
    event
  };
}
