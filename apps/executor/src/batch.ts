export const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const BACKOFFS = [2000, 5000, 10000];

export async function withRetry<T>(task: () => Promise<T>): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt < BACKOFFS.length; attempt += 1) {
    try {
      return await task();
    } catch (error) {
      lastError = error;
      if (attempt < BACKOFFS.length - 1) {
        await wait(BACKOFFS[attempt]);
      }
    }
  }
  throw lastError;
}
