import "dotenv/config";
import fs from "node:fs";
import path from "node:path";
import OpenAI, { APIError } from "openai";
import { wait } from "./batch.js";

type OpenAIError = Error & { status?: number; retryAfterMs?: number };

type Provider = "github_models" | "gemini" | "openai";

type LlmPayload = {
  title: string;
  seo_title?: string;
  meta_desc?: string;
  html: string;
  images?: Array<{ src: string; alt?: string }>;
};

export type BatchJobItem = {
  id: string;
  systemPrompt: string;
  userPrompt?: string;
};

export type BatchGenerationResult = {
  outputs: Record<string, LlmPayload>;
  errors: Record<string, string>;
};

const JSON_ONLY_MESSAGE = "Return only a single minified JSON object. No markdown, no code fences, no commentary.";
const TERMINAL_BATCH_STATUSES = new Set(["completed", "failed", "expired", "canceled"]);
let cachedOpenAIClient: OpenAI | null = null;

export async function callLLM(
  systemPrompt: string,
  model: string,
  userPrompt: string = JSON_ONLY_MESSAGE,
): Promise<LlmPayload> {
  const providers = resolveProviderOrder();
  let lastError: Error | null = null;

  for (const provider of providers) {
    try {
      const resolvedModel = resolveModelForProvider(provider, model);
      if (provider === "gemini") {
        return await callGemini(systemPrompt, userPrompt, resolvedModel);
      }
      return await callOpenAICompatible(provider, systemPrompt, userPrompt, resolvedModel);
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      lastError = err;
      if (shouldFallback(provider, err)) {
        continue;
      }
      throw err;
    }
  }

  if (lastError) throw lastError;
  throw new Error("No LLM providers configured");
}

export async function generateBatch(items: BatchJobItem[], model: string): Promise<BatchGenerationResult> {
  if (!items.length) return { outputs: {}, errors: {} };
  const providers = resolveProviderOrder();
  const primaryProvider = providers[0] ?? "openai";
  if (process.env.USE_BATCH !== "true" || primaryProvider !== "openai") {
    return generateSequential(items, model);
  }
  return runBatchWorkflow(items, model);
}

async function generateSequential(items: BatchJobItem[], model: string): Promise<BatchGenerationResult> {
  const result: BatchGenerationResult = { outputs: {}, errors: {} };
  for (const item of items) {
    try {
      result.outputs[item.id] = await callLLM(item.systemPrompt, model, item.userPrompt);
    } catch (error) {
      result.errors[item.id] = error instanceof Error ? error.message : String(error);
    }
  }
  return result;
}

async function runBatchWorkflow(items: BatchJobItem[], model: string): Promise<BatchGenerationResult> {
  const client = getOpenAIClient();
  const ndjsonLines = items.map((item) =>
    JSON.stringify({
      custom_id: item.id,
      method: "POST",
      url: "/v1/chat/completions",
      body: {
        model,
        response_format: { type: "json_object" },
        temperature: 0.6,
        messages: [
          { role: "system", content: item.systemPrompt },
          { role: "user", content: item.userPrompt ?? JSON_ONLY_MESSAGE },
        ],
      },
    }),
  );

  const batchDir = path.join(process.cwd(), "out", "batches");
  await fs.promises.mkdir(batchDir, { recursive: true });
  const batchFile = path.join(batchDir, `batch-${Date.now()}.ndjson`);
  await fs.promises.writeFile(batchFile, ndjsonLines.join("\n"), "utf8");

  try {
    const upload = await callOpenAIWithMeta(() =>
      client.files.create({ file: fs.createReadStream(batchFile), purpose: "batch" }),
    );
    let batch = await callOpenAIWithMeta(() =>
      client.batches.create({
        input_file_id: upload.id,
        endpoint: "/v1/chat/completions",
        completion_window: "24h",
      }),
    );

    while (!TERMINAL_BATCH_STATUSES.has(batch.status)) {
      await wait(5000);
      batch = await callOpenAIWithMeta(() => client.batches.retrieve(batch.id));
    }

    if (batch.status !== "completed" || !batch.output_file_id) {
      throw new Error(`Batch ${batch.id} ended with status ${batch.status}`);
    }

    const text = await readBatchOutput(client, batch.output_file_id);
    return parseBatchOutput(text);
  } finally {
    void fs.promises.unlink(batchFile).catch(() => {});
  }
}

function parseBatchOutput(rawText: string): BatchGenerationResult {
  const result: BatchGenerationResult = { outputs: {}, errors: {} };
  for (const line of rawText.split("\n")) {
    if (!line.trim()) continue;
    const payload = JSON.parse(line);
    const id = payload.custom_id as string;
    if (payload.response?.status_code !== 200) {
      const message =
        payload.response?.body?.error?.message || `Batch item failed with status ${payload.response?.status_code}`;
      result.errors[id] = message;
      continue;
    }
    const content = payload.response?.body?.choices?.[0]?.message?.content ?? "";
    try {
      result.outputs[id] = parseJsonRelaxed(content) as LlmPayload;
    } catch (error) {
      result.errors[id] = error instanceof Error ? error.message : "LLM returned non-JSON";
    }
  }
  return result;
}

function resolveProviderOrder(): Provider[] {
  const raw = (process.env.LLM_PROVIDER_ORDER || process.env.LLM_PROVIDER || "gemini,github_models,openai")
    .split(",")
    .map((entry) => entry.trim().toLowerCase())
    .filter(Boolean);

  const seen = new Set<Provider>();
  const providers: Provider[] = [];
  for (const value of raw) {
    if (value === "github_models" || value === "github" || value === "githubmodels") {
      if (!seen.has("github_models")) {
        providers.push("github_models");
        seen.add("github_models");
      }
      continue;
    }
    if (value === "gemini") {
      if (!seen.has("gemini")) {
        providers.push("gemini");
        seen.add("gemini");
      }
      continue;
    }
    if (value === "openai") {
      if (!seen.has("openai")) {
        providers.push("openai");
        seen.add("openai");
      }
    }
  }
  return providers.length ? providers : ["openai"];
}

function resolveModelForProvider(provider: Provider, fallbackModel: string): string {
  if (provider === "github_models") {
    const explicit = process.env.GH_MODELS_MODEL || process.env.GITHUB_MODELS_MODEL;
    if (explicit) return explicit;
    return fallbackModel.includes("/") ? fallbackModel : `openai/${fallbackModel}`;
  }
  if (provider === "gemini") {
    return process.env.GEMINI_MODEL || "gemini-1.5-flash";
  }
  return fallbackModel;
}

function shouldFallback(provider: Provider, error: Error): boolean {
  const message = error.message.toLowerCase();
  const status = (error as OpenAIError).status;
  if (message.includes("missing")) return true;
  if (status && [401, 403, 429].includes(status)) return true;
  if (message.includes("quota") || message.includes("rate limit") || message.includes("insufficient")) return true;
  return provider !== "openai" && message.includes("timed out");
}

async function callOpenAICompatible(
  provider: "github_models" | "openai",
  systemPrompt: string,
  userPrompt: string,
  model: string,
): Promise<LlmPayload> {
  const apiKey =
    provider === "github_models"
      ? process.env.GH_MODELS_API_KEY || process.env.GITHUB_MODELS_API_KEY || process.env.GITHUB_TOKEN
      : process.env.OPENAI_API_KEY;

  if (!apiKey) {
    throw new Error(
      provider === "github_models" ? "Missing GH_MODELS_API_KEY" : "Missing OPENAI_API_KEY",
    );
  }

  const timeoutMs = Number(process.env.OPENAI_TIMEOUT_MS || "120000");
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 120000,
  );

  const baseUrl =
    provider === "github_models"
      ? process.env.GH_MODELS_API_BASE ||
        process.env.GITHUB_MODELS_API_BASE ||
        "https://models.github.ai/inference"
      : "https://api.openai.com/v1";

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "api-key": apiKey,
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
            content: userPrompt,
          },
        ],
      }),
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error(`${provider} request timed out`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }

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

async function callGemini(systemPrompt: string, userPrompt: string, model: string): Promise<LlmPayload> {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) throw new Error("Missing GEMINI_API_KEY");

  const timeoutMs = Number(process.env.OPENAI_TIMEOUT_MS || "120000");
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 120000,
  );

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        systemInstruction: {
          role: "system",
          parts: [{ text: systemPrompt }],
        },
        contents: [
          {
            role: "user",
            parts: [{ text: userPrompt }],
          },
        ],
        generationConfig: {
          temperature: 0.3,
          maxOutputTokens: 2200,
        },
      }),
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("gemini request timed out");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    const message = await extractErrorMessage(response);
    const error = new Error(message) as OpenAIError;
    error.status = response.status;
    throw error;
  }

  const json = await response.json();
  const text = json?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
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

function getOpenAIClient() {
  if (cachedOpenAIClient) return cachedOpenAIClient;
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("Missing OPENAI_API_KEY");
  cachedOpenAIClient = new OpenAI({ apiKey });
  return cachedOpenAIClient;
}

async function readBatchOutput(client: OpenAI, fileId: string): Promise<string> {
  const response = await callOpenAIWithMeta(() => client.files.content(fileId));
  if (typeof (response as any).text === "function") {
    return (response as any).text();
  }
  if (isAsyncIterable<Uint8Array>(response)) {
    const chunks: Buffer[] = [];
    for await (const chunk of response) {
      chunks.push(Buffer.from(chunk));
    }
    return Buffer.concat(chunks).toString("utf8");
  }
  if (typeof (response as any).arrayBuffer === "function") {
    const buffer = await (response as any).arrayBuffer();
    return Buffer.from(buffer).toString("utf8");
  }
  return "";
}

async function callOpenAIWithMeta<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    if (error instanceof APIError) {
      const enriched = new Error(error.message) as OpenAIError;
      enriched.status = error.status;
      const apiResponse = (error as APIError & { response?: Response }).response;
      const retryAfterHeader = apiResponse?.headers?.get?.("retry-after") ?? null;
      const resetHeader = apiResponse?.headers?.get?.("x-ratelimit-reset-requests") ?? null;
      const retryAfterMs = parseRetryAfterHeader(retryAfterHeader) ?? parseResetHeader(resetHeader);
      if (retryAfterMs) enriched.retryAfterMs = retryAfterMs;
      throw enriched;
    }
    throw error;
  }
}

function isAsyncIterable<T>(value: unknown): value is AsyncIterable<T> {
  return Boolean(value && typeof (value as any)[Symbol.asyncIterator] === "function");
}

export type { LlmPayload };
