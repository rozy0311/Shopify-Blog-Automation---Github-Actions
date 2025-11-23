import "dotenv/config";

type OpenAIError = Error & { status?: number; retryAfterMs?: number };

type LlmPayload = {
  title: string;
  seo_title?: string;
  meta_desc?: string;
  html: string;
  images?: Array<{ src: string; alt?: string }>;
};

export async function callOpenAI(systemPrompt: string, model: string): Promise<LlmPayload> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("Missing OPENAI_API_KEY");

  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      temperature: 0.3,
      max_tokens: 2200,
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: systemPrompt },
        {
          role: "user",
          content: "Return only a single minified JSON object. No markdown, no code fences, no commentary.",
        },
      ],
    }),
  });

  if (!response.ok) {
    const message = await extractErrorMessage(response);
    const error = new Error(message) as OpenAIError;
    error.status = response.status;
    const retryAfterMs = computeRetryAfter(response);
    if (retryAfterMs) {
      error.retryAfterMs = retryAfterMs;
    }
    throw error;
  }

  const json = await response.json();
  const text = json?.choices?.[0]?.message?.content ?? "";
  return parseJsonRelaxed(text) as LlmPayload;
}

async function extractErrorMessage(response: Response): Promise<string> {
  const fallback = `OpenAI HTTP ${response.status}`;
  try {
    const bodyText = await response.text();
    if (!bodyText) return fallback;
    const parsed = JSON.parse(bodyText);
    return parsed?.error?.message || fallback;
  } catch {
    return fallback;
  }
}

function computeRetryAfter(response: Response): number | undefined {
  if (response.status !== 429) return undefined;

  const retryAfter = response.headers.get("retry-after");
  const retryAfterMs = parseRetryAfterHeader(retryAfter);
  if (retryAfterMs) return retryAfterMs;

  const reset = response.headers.get("x-ratelimit-reset-requests");
  const resetDelay = parseResetHeader(reset);
  if (resetDelay) return resetDelay;

  return 15000; // default wait 15s when rate limited and no guidance provided
}

function parseRetryAfterHeader(headerValue: string | null): number | undefined {
  if (!headerValue) return undefined;
  const numeric = Number(headerValue);
  if (Number.isFinite(numeric) && numeric >= 0) {
    return numeric * 1000;
  }
  const dateValue = Date.parse(headerValue);
  if (!Number.isNaN(dateValue)) {
    return Math.max(0, dateValue - Date.now());
  }
  return undefined;
}

function parseResetHeader(headerValue: string | null): number | undefined {
  if (!headerValue) return undefined;
  const numeric = Number(headerValue);
  if (!Number.isFinite(numeric) || numeric <= 0) return undefined;

  // Header may either be "seconds until reset" or an epoch timestamp in seconds.
  if (numeric < 10_000) {
    return numeric * 1000;
  }

  const candidate = numeric * 1000 - Date.now();
  return candidate > 0 ? candidate : undefined;
}

export function parseJsonRelaxed(input: string) {
  const stripped = input
    .replace(/^```[a-zA-Z]*\n?/, "")
    .replaceAll(/```$/g, "")
    .replaceAll(/[“”]/g, '"')
    .replaceAll(/[‘’]/g, "'");

  try {
    return JSON.parse(stripped);
  } catch {
    const start = stripped.indexOf("{");
    const end = stripped.lastIndexOf("}");
    if (start >= 0 && end > start) {
      return JSON.parse(stripped.slice(start, end + 1));
    }
  }
  throw new Error("LLM returned non-JSON");
}

export function validateNoYears(payload: LlmPayload) {
  const rx = /\b(19|20)\d{2}\b/;
  const blob = `${payload.title} ${payload.seo_title || ""} ${payload.meta_desc || ""} ${payload.html}`;
  if (rx.test(blob)) {
    throw new Error("NO YEARS violation");
  }
}

export type { LlmPayload };
