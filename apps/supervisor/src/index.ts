import "./tracing.js";
import "dotenv/config";
import {
  dispatchWorkflow,
  getActionsVariable,
  getPipelineHealth,
  notifyHuman,
  openIncident,
  setActionsVariable,
  RunInfo,
} from "./tools.js";
import { getQueueStatus } from "./sheets.js";

function coerceBoolFlag(value: string | null | undefined, fallback = false) {
  if (value === undefined || value === null) return fallback;
  return value.toLowerCase() === "true";
}

async function fetchQueueSafe() {
  try {
    return await getQueueStatus();
  } catch (error) {
    console.warn("Failed to read queue status", error);
    return null;
  }
}

function unstable(runs: RunInfo[]) {
  return runs.filter((run) => run.conclusion === "failure").length >= 2;
}

async function disablePipeline(reason: string, runs: RunInfo[], pending?: number | null) {
  const wfUpdated = await setActionsVariable("WF_ENABLED", "false");
  const allowUpdated = await setActionsVariable("ALLOW_PUBLISH", "human_disabled");
  const flagNote = wfUpdated && allowUpdated
    ? "WF_ENABLED=false, ALLOW_PUBLISH=human_disabled."
    : "Could not update WF_ENABLED/ALLOW_PUBLISH automatically. Flip them manually.";
  await openIncident("high", reason, JSON.stringify({ runs }, null, 2));
  await notifyHuman({
    subject: "[PIPELINE] Disabled",
    message: `${reason}. Pending: ${pending ?? "unknown"}. ${flagNote}`,
    links: runs.map((run) => run.url),
  });
}

function findLastReviewSuccess(runs: RunInfo[]) {
  return runs.find((run) => run.mode === "review" && run.conclusion === "success");
}

async function main() {
  const [queue, health] = await Promise.all([fetchQueueSafe(), getPipelineHealth(5)]);
  const runs = health.runs;

  const wfFlag = (await getActionsVariable("WF_ENABLED")) ?? process.env.WF_ENABLED ?? "false";
  const allowFlag = (await getActionsVariable("ALLOW_PUBLISH")) ?? process.env.ALLOW_PUBLISH ?? "human_disabled";
  const wfEnabled = coerceBoolFlag(wfFlag);
  const allowPublish = allowFlag as "human_enabled" | "human_disabled";

  if (unstable(runs)) {
    await disablePipeline("Pipeline unstable: >=2 failures detected", runs, queue?.totalPending ?? null);
    return;
  }

  if (!queue || queue.totalPending === 0) {
    console.log("Supervisor: no pending items or queue unavailable");
    return;
  }

  if (!wfEnabled) {
    await dispatchWorkflow("review", `WF disabled; running safe review for ${queue.totalPending} pending items`);
    await notifyHuman({
      subject: "[PIPELINE] Review only",
      message: `WF_ENABLED=false but ${queue.totalPending} pending items exist. Triggered review draft run.`,
      links: queue.sampleUrls,
    });
    return;
  }

  if (allowPublish !== "human_enabled") {
    await dispatchWorkflow("review", `Publish locked by ALLOW_PUBLISH; review ${queue.totalPending} pending items`);
    await notifyHuman({
      subject: "[PIPELINE] Publish locked",
      message: `ALLOW_PUBLISH=${allowPublish}. Ran review to keep queue moving. Consider enabling publish when ready.`,
      links: queue.sampleUrls,
    });
    return;
  }

  const lastReview = findLastReviewSuccess(runs);
  if (!lastReview) {
    await dispatchWorkflow("review", `Need recent successful review before publish (${queue.totalPending} pending)`);
    await notifyHuman({
      subject: "[PIPELINE] Need fresh review",
      message: "No successful review run found in recent history, so dispatched review instead of publish.",
      links: runs.map((run) => run.url),
    });
    return;
  }

  await dispatchWorkflow("publish", `${queue.totalPending} pending; last review healthy (${lastReview.url})`);
  await notifyHuman({
    subject: "[PIPELINE] Publish dispatched",
    message: `Triggered publish for ${queue.totalPending} pending items. Last review run: ${lastReview.url}.`,
    links: queue.sampleUrls,
  });
}

try {
  await main();
} catch (error) {
  console.error("Supervisor tick failed", error);
  process.exitCode = 1;
}
