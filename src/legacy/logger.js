export function log(level, message, meta = {}) {
  const ts = new Date().toISOString();
  const payload = Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : "";
  console.log(`[${ts}] [${level.toUpperCase()}] ${message}${payload}`);
}

export const logger = {
  info: (msg, meta) => log('info', msg, meta),
  warn: (msg, meta) => log('warn', msg, meta),
  error: (msg, meta) => log('error', msg, meta),
  debug: (msg, meta) => log('debug', msg, meta)
};
