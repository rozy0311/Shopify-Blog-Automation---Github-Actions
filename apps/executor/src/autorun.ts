import "./tracing.js";
import "dotenv/config";
import cron from "node-cron";
import { wait } from "./batch.js";

const CRON = "5 7,13,20 * * *";
const TZ = "America/Chicago";

async function triggerRun() {
  await import("./index.js");
}

console.log(`[autorun] Scheduling at ${CRON} ${TZ}. MODE=${process.env.MODE || resolveDefaultMode()}`);

cron.schedule(
  CRON,
  async () => {
    const stamp = new Date().toISOString();
    console.log(`[autorun] tick ${stamp} MODE=${process.env.MODE || resolveDefaultMode()}`);
    await triggerRun();
  },
  { timezone: TZ },
);

await triggerRun();
while (true) {
  // eslint-disable-next-line no-await-in-loop
  await wait(60_000);
}

function resolveDefaultMode() {
  return process.env.WF_ENABLED === "true" ? "publish" : "review";
}
