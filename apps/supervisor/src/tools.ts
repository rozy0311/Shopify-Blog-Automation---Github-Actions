const GH_API = "https://api.github.com";

function requireEnv(name: string) {
  const value = process.env[name];
  if (!value) throw new Error(`Missing ${name}`);
  return value;
}

function repoPath() {
  return process.env.GITHUB_REPOSITORY || `${requireEnv("GITHUB_OWNER")}/${requireEnv("GITHUB_REPO")}`;
}

function ghHeaders() {
  const token = process.env.GITHUB_TOKEN;
  if (!token) throw new Error("Missing GITHUB_TOKEN");
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "Content-Type": "application/json",
  };
}

function detectMode(name?: string | null) {
  if (!name) return "review";
  return /publish/i.test(name) ? "publish" : "review";
}

export type RunInfo = {
  id: number;
  status: string;
  conclusion: string | null;
  mode: "review" | "publish";
  url: string;
};

export async function getPipelineHealth(limitRuns = 3): Promise<{ runs: RunInfo[] }> {
  const repo = repoPath();
  const res = await fetch(`${GH_API}/repos/${repo}/actions/workflows/publish.yml/runs?per_page=${limitRuns}`, {
    headers: ghHeaders(),
  });
  if (!res.ok) {
    throw new Error(`GitHub runs ${res.status}`);
  }
  const json = await res.json();
  const runs: RunInfo[] = (json.workflow_runs || []).map((run: any) => ({
    id: run.id,
    status: run.status,
    conclusion: run.conclusion,
    mode: detectMode(run.name),
    url: run.html_url,
  }));
  return { runs };
}

export async function dispatchWorkflow(mode: "review" | "publish", reason: string) {
  if (!reason || reason.length < 10) throw new Error("Dispatch reason must be >= 10 characters");
  const repo = repoPath();
  const ref = process.env.DISPATCH_REF || process.env.GITHUB_REF || "main";
  const res = await fetch(`${GH_API}/repos/${repo}/actions/workflows/publish.yml/dispatches`, {
    method: "POST",
    headers: ghHeaders(),
    body: JSON.stringify({ ref, inputs: { mode, reason } }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Dispatch failed ${res.status}: ${text}`);
  }
}

export async function notifyHuman({
  subject,
  message,
  links = [],
}: {
  subject: string;
  message: string;
  links?: string[];
}) {
  const hook = process.env.SLACK_WEBHOOK;
  if (!hook) {
    console.log(`[notify] ${subject} -> ${message}`);
    return;
  }
  const text = [`*${subject}*`, message, ...links.map((link) => `• ${link}`)].filter(Boolean).join("\n");
  const res = await fetch(hook, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Slack webhook failed ${res.status}: ${body}`);
  }
}

export async function openIncident(severity: "low" | "medium" | "high" | "critical", summary: string, details?: string) {
  const repo = repoPath();
  const res = await fetch(`${GH_API}/repos/${repo}/issues`, {
    method: "POST",
    headers: ghHeaders(),
    body: JSON.stringify({
      title: `[${severity.toUpperCase()}] ${summary}`,
      body: details || summary,
      labels: ["incident", severity],
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`openIncident failed ${res.status}: ${text}`);
  }
}

export async function getActionsVariable(name: string) {
  const repo = repoPath();
  const res = await fetch(`${GH_API}/repos/${repo}/actions/variables/${name}`, {
    headers: ghHeaders(),
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`getActionsVariable ${name} ${res.status}`);
  const json = await res.json();
  return json.value as string;
}

export async function setActionsVariable(name: string, value: string) {
  const repo = repoPath();
  const patch = await fetch(`${GH_API}/repos/${repo}/actions/variables/${name}`, {
    method: "PATCH",
    headers: ghHeaders(),
    body: JSON.stringify({ name, value }),
  });
  if (patch.status === 404) {
    const create = await fetch(`${GH_API}/repos/${repo}/actions/variables`, {
      method: "POST",
      headers: ghHeaders(),
      body: JSON.stringify({ name, value }),
    });
    if (!create.ok) {
      const text = await create.text();
      throw new Error(`setActionsVariable create ${name} ${create.status}: ${text}`);
    }
    return;
  }
  if (!patch.ok) {
    const text = await patch.text();
    throw new Error(`setActionsVariable patch ${name} ${patch.status}: ${text}`);
  }
}
