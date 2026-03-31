/**
 * Memory Configuration
 * TTL policies, embedding settings, and feature flags
 */

// Load from environment variables with defaults
export const MEMORY_CONFIG = {
  // Embedding settings
  embedding: {
    provider: process.env.EMBEDDING_PROVIDER || 'openai', // 'openai' | 'groq'
    model: process.env.EMBEDDING_MODEL || 'text-embedding-ada-002',
    batchSize: parseInt(process.env.EMBEDDING_BATCH_SIZE) || 100,
    cacheEnabled: process.env.EMBEDDING_CACHE !== 'false'
  },

  // TTL policies (in days)
  ttl: {
    agentMemories: parseInt(process.env.MEMORY_TTL_MEMORIES_DAYS) || 180,
    sessions: parseInt(process.env.MEMORY_TTL_SESSIONS_DAYS) || 7,
    snapshots: parseInt(process.env.MEMORY_TTL_SNAPSHOTS_DAYS) || 90,
    diffsPerSession: parseInt(process.env.MEMORY_DIFFS_TO_KEEP) || 100,
    cleanupIntervalHours: parseInt(process.env.MEMORY_CLEANUP_INTERVAL_HOURS) || 24
  },

  // Operational limits
  limits: {
    maxSearchResults: parseInt(process.env.MEMORY_MAX_SEARCH_RESULTS) || 50,
    similarityThreshold: parseFloat(process.env.MEMORY_SIMILARITY_THRESHOLD) || 0.6,
    maxSessionTokenLength: 256,
    maxMemoryContentLength: 10000
  },

  // Features
  features: {
    enableAutoCheckpoint: process.env.MEMORY_AUTO_CHECKPOINT !== 'false',
    checkpointIntervalMinutes: parseInt(process.env.MEMORY_CHECKPOINT_INTERVAL_MINUTES) || 30,
    enableSyncQueue: process.env.MEMORY_ENABLE_SYNC_QUEUE === 'true',
    enablePersistenceCompression: process.env.MEMORY_COMPRESSION !== 'false'
  },

  // Paths
  paths: {
    sqliteDb: process.env.MISSION_CONTROL_DB || './data/sessions.db'
  }
};

/**
 * Validate configuration
 */
export function validateMemoryConfig() {
  const errors = [];

  if (!process.env.SUPABASE_URL) {
    errors.push('SUPABASE_URL is required for vector store');
  }
  if (!process.env.SUPABASE_SERVICE_ROLE_KEY) {
    errors.push('SUPABASE_SERVICE_ROLE_KEY is required for vector store');
  }
  if (!process.env.OPENAI_API_KEY && (!process.env.GROQ_API_KEY || MEMORY_CONFIG.embedding.provider !== 'groq')) {
    errors.push('Either OPENAI_API_KEY or GROQ_API_KEY must be set for embeddings');
  }

  if (MEMORY_CONFIG.ttl.agentMemories < 1) errors.push('MEMORY_TTL_MEMORIES_DAYS must be >= 1');
  if (MEMORY_CONFIG.ttl.sessions < 1) errors.push('MEMORY_TTL_SESSIONS_DAYS must be >= 1');
  if (MEMORY_CONFIG.ttl.snapshots < 1) errors.push('MEMORY_TTL_SNAPSHOTS_DAYS must be >= 1');

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Get public config (non-secret)
 */
export function getPublicConfig() {
  return {
    embedding: {
      provider: MEMORY_CONFIG.embedding.provider,
      model: MEMORY_CONFIG.embedding.model,
      batchSize: MEMORY_CONFIG.embedding.batchSize
    },
    ttl: MEMORY_CONFIG.ttl,
    limits: MEMORY_CONFIG.limits,
    features: MEMORY_CONFIG.features
  };
}
