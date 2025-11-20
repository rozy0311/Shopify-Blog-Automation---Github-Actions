import "dotenv/config";

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
    throw new Error(`OpenAI HTTP ${response.status}`);
  }

  const json = await response.json();
  const text = json?.choices?.[0]?.message?.content ?? "";
  return parseJsonRelaxed(text) as LlmPayload;
}

export function parseJsonRelaxed(input: string) {
  const stripped = input
    .replace(/^```[a-zA-Z]*\n?/, "")
    .replace(/```$/g, "")
    .replace(/[“”]/g, '"')
    .replace(/[‘’]/g, "'");

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
