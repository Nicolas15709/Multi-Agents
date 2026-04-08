/**
 * Embeddings Service for Virtual Agency Memory
 * Supports OpenAI and Groq embeddings models
 */

import dotenv from 'dotenv';
dotenv.config();

const DEFAULT_MODEL = 'text-embedding-ada-002';
const DIMENSION = 1536;

// Cache para evitar llamadas repetitivas
const embeddingCache = new Map();

/**
 * Generate embedding for a single text
 * @param {string} text - Text to embed
 * @param {object} options - { provider: 'openai'|'groq', apiKey?: string, model?: string }
 * @returns {Promise<number[]>}
 */
export async function generateEmbedding(text, options = {}) {
  const {
    provider = process.env.EMBEDDING_PROVIDER || 'openai',
    apiKey = process.env[`${provider.toUpperCase()}_API_KEY`],
    model = process.env.EMBEDDING_MODEL || DEFAULT_MODEL
  } = options;

  if (!apiKey) {
    throw new Error(`Missing API key for ${provider}. Set ${provider.toUpperCase()}_API_KEY env var.`);
  }

  // Normalize and cache key
  const normalized = text.trim().slice(0, 8000); // limit input
  const cacheKey = `${provider}:${model}:${normalized.slice(0, 200)}`;

  if (embeddingCache.has(cacheKey)) {
    return embeddingCache.get(cacheKey);
  }

  let embedding;
  if (provider === 'openai') {
    embedding = await callOpenAI(text, apiKey, model);
  } else if (provider === 'groq') {
    embedding = await callGroq(text, apiKey, model);
  } else {
    throw new Error(`Unknown embedding provider: ${provider}`);
  }

  embeddingCache.set(cacheKey, embedding);
  return embedding;
}

/**
 * Generate embeddings for multiple texts (batch)
 * @param {string[]} texts
 * @param {object} options
 * @returns {Promise<number[][]>}
 */
export async function generateEmbeddingsBatch(texts, options = {}) {
  const batchSize = parseInt(process.env.EMBEDDING_BATCH_SIZE || '100');
  const results = [];

  for (let i = 0; i < texts.length; i += batchSize) {
    const batch = texts.slice(i, i + batchSize);
    const embeddings = await Promise.all(batch.map(text => generateEmbedding(text, options)));
    results.push(...embeddings);

    // Small delay to avoid rate limits
    if (i + batchSize < texts.length) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }

  return results;
}

async function callOpenAI(text, apiKey, model) {
  const response = await fetch('https://api.openai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      input: text,
      model: model
    })
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`OpenAI embedding error: ${response.status} - ${err}`);
  }

  const data = await response.json();
  return data.data[0].embedding;
}

async function callGroq(text, apiKey, model) {
  // Groq uses OpenAI-compatible endpoint for embeddings
  const response = await fetch('https://api.groq.com/openai/v1/embeddings', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      input: text,
      model: model || 'text-embedding-ada-002' // Groq supports this model via OpenAI API
    })
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Groq embedding error: ${response.status} - ${err}`);
  }

  const data = await response.json();
  return data.data[0].embedding;
}

/**
 * Clear embedding cache (useful for testing or forced refresh)
 */
export function clearEmbeddingCache() {
  embeddingCache.clear();
}

/**
 * Get cache statistics
 */
export function getEmbeddingCacheStats() {
  return {
    size: embeddingCache.size,
    keys: Array.from(embeddingCache.keys()).slice(0, 10) // sample
  };
}

