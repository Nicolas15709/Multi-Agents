export async function withRetry(fn, options = {}) {
  const {
    retries = 3,
    onRetry = () => {},
    shouldRetry = () => true
  } = options;

  let attempt = 0;
  let lastError;

  while (attempt < retries) {
    try {
      return await fn(attempt + 1);
    } catch (error) {
      lastError = error;
      attempt += 1;
      if (attempt >= retries || !shouldRetry(error)) {
        throw lastError;
      }
      await onRetry(error, attempt);
      await new Promise((resolve) => setTimeout(resolve, 500 * attempt));
    }
  }

  throw lastError;
}
