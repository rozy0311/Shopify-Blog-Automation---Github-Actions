export const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

type RetryableError = Error & { retryAfterMs?: number };

type RetryOptions = {
  maxAttempts?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
};

const DEFAULT_OPTIONS: Required<RetryOptions> = {
  maxAttempts: 6,
  baseDelayMs: 2000,
  maxDelayMs: 60000,
};

const MAX_JITTER_MS = 250;

export async function withRetry<T>(task: () => Promise<T>, options: RetryOptions = {}): Promise<T> {
  const { maxAttempts, baseDelayMs, maxDelayMs } = { ...DEFAULT_OPTIONS, ...options };
  let lastError: unknown;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await task();
    } catch (error) {
      lastError = error;
      if (attempt >= maxAttempts) break;

      const retryAfterMs = extractRetryAfterMs(error);
      const exponentialDelay = baseDelayMs * 2 ** (attempt - 1);
      const jitter = Math.floor(Math.random() * MAX_JITTER_MS);
      const delay = Math.min(maxDelayMs, (retryAfterMs ?? exponentialDelay) + jitter);
      await wait(delay);
    }
  }

  throw lastError;
}

function extractRetryAfterMs(error: unknown): number | undefined {
  if (error && typeof error === "object" && "retryAfterMs" in error) {
    const value = (error as RetryableError).retryAfterMs;
    if (typeof value === "number" && Number.isFinite(value) && value > 0) {
      return value;
    }
  }
  return undefined;
}
