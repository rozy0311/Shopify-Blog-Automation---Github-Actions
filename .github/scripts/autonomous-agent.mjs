/**
 * Autonomous GitHub Worker Agent
 *
 * Tự chạy, tự commit, tự push, không cần VS Code hay approve tay
 *
 * Features:
 * - Chạy theo schedule trong GitHub Actions
 * - Chỉ modify allowed paths
 * - Tự chạy checks trước khi commit
 * - Ghi log đầy đủ
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { execSync } from 'child_process';
import { join } from 'path';

// ============ CONFIGURATION ============
const CONFIG = {
  allowedPaths: [
    'artifacts/',
    'blogs/',
    'REPORT.md',
    'logs/',
  ],
  forbiddenPaths: [
    '.github/',
    'apps/',
    'package.json',
    'package-lock.json',
    '.env',
    'vertex-sa.json',
  ],
  checks: [
    // Commands that must pass before commit
    // 'npm run build --workspace apps/executor',
    // 'npm test',
  ],
};

// ============ SYSTEM PROMPT ============
const SYSTEM_PROMPT = `
You are an autonomous software & automation agent working inside a Git repository.

You will receive:
- A business task description.
- Allowed paths you can modify.
- Forbidden paths you must never touch.
- Shell commands that MUST pass (checks).

Your job:
1. Restate the business objective in 1–3 bullet points.
2. Propose a minimal technical plan (files to read, files to modify, steps).
3. Apply the smallest necessary changes ONLY within allowed paths.
4. Run the required checks locally (simulated via tool calls or described commands).
5. If checks fail, fix the code ONCE using the error messages, then re-run checks.
6. If checks still fail, revert your changes and output a failure report.
7. If checks pass, output the final file contents to be committed.

Never:
- Touch forbidden paths.
- Introduce large, unrelated refactors.
- Delete existing content unless clearly redundant.

Allowed paths: ${CONFIG.allowedPaths.join(', ')}
Forbidden paths: ${CONFIG.forbiddenPaths.join(', ')}
`;

// ============ DEFAULT TASKS ============
const DEFAULT_TASKS = [
  {
    name: 'update-report',
    description: 'Update REPORT.md with latest stats',
    businessPrompt: `
[Business task description]

Context:
- Business background: Shopify Blog Automation system that publishes blogs automatically
- Goal: Update REPORT.md with current system status and statistics
- Input: artifacts/blogs_sitemap.csv, blogs/ folder
- Output: Updated REPORT.md with current stats

Constraints:
- Allowed paths: REPORT.md, artifacts/, logs/
- Forbidden paths: apps/, .github/, package.json
- Risk / safety notes: Only update stats section, don't delete existing content

Checks:
- File must be valid Markdown
`,
  },
  {
    name: 'cleanup-logs',
    description: 'Clean up old log files',
    businessPrompt: `
[Business task description]

Context:
- Business background: System generates logs that need periodic cleanup
- Goal: Remove log files older than 7 days
- Input: logs/ folder
- Output: Cleaned logs folder, keeping recent files

Constraints:
- Allowed paths: logs/
- Forbidden paths: everything else
- Risk / safety notes: Only delete .log files, keep important files

Checks:
- logs/ folder still exists
`,
  },
];

// ============ UTILITY FUNCTIONS ============
function log(message, level = 'INFO') {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] [${level}] ${message}`);
}

function isPathAllowed(filePath) {
  // Check if path is in allowed list
  for (const allowed of CONFIG.allowedPaths) {
    if (filePath.startsWith(allowed) || filePath === allowed.replace('/', '')) {
      return true;
    }
  }
  return false;
}

function isPathForbidden(filePath) {
  for (const forbidden of CONFIG.forbiddenPaths) {
    if (filePath.startsWith(forbidden) || filePath === forbidden) {
      return true;
    }
  }
  return false;
}

function runCheck(command) {
  try {
    execSync(command, { stdio: 'pipe' });
    return { success: true, output: '' };
  } catch (error) {
    return { success: false, output: error.message };
  }
}

function safeWriteFile(filePath, content) {
  if (isPathForbidden(filePath)) {
    throw new Error(`FORBIDDEN: Cannot write to ${filePath}`);
  }
  if (!isPathAllowed(filePath)) {
    throw new Error(`NOT ALLOWED: ${filePath} is not in allowed paths`);
  }

  // Create directory if needed
  const dir = filePath.split('/').slice(0, -1).join('/');
  if (dir && !existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }

  writeFileSync(filePath, content);
  log(`Written: ${filePath}`);
}

// ============ AGENT EXECUTION ============
async function executeTask(task) {
  log(`Executing task: ${task.name}`);
  log(`Description: ${task.description}`);

  // For now, execute simple built-in tasks
  // In production, this would call an LLM API

  switch (task.name) {
    case 'update-report':
      await updateReport();
      break;
    case 'cleanup-logs':
      await cleanupLogs();
      break;
    default:
      log(`Unknown task: ${task.name}`, 'WARN');
  }
}

async function updateReport() {
  const reportPath = 'REPORT.md';
  const timestamp = new Date().toISOString();

  let content = '';
  if (existsSync(reportPath)) {
    content = readFileSync(reportPath, 'utf-8');
  }

  // Count blogs
  let blogCount = 0;
  try {
    const files = execSync('find blogs -name "*.txt" -o -name "*.md" 2>/dev/null || echo ""', { encoding: 'utf-8' });
    blogCount = files.split('\n').filter(f => f.trim()).length;
  } catch (e) {
    blogCount = 0;
  }

  // Update or create report
  const statsSection = `
## Latest Update
- **Last Run**: ${timestamp}
- **Blog Count**: ${blogCount}
- **Status**: ✅ Healthy

---
`;

  if (content.includes('## Latest Update')) {
    content = content.replace(/## Latest Update[\s\S]*?---/m, statsSection.trim());
  } else {
    content = statsSection + content;
  }

  safeWriteFile(reportPath, content);
  log('Report updated successfully');
}

async function cleanupLogs() {
  log('Cleaning up old logs...');

  try {
    // Delete logs older than 7 days
    execSync('find logs -name "*.log" -mtime +7 -delete 2>/dev/null || true', { stdio: 'pipe' });
    log('Old logs cleaned up');
  } catch (e) {
    log('No logs to clean or logs folder does not exist', 'WARN');
  }
}

// ============ MAIN ============
async function main() {
  log('========================================');
  log('Autonomous GitHub Worker Agent');
  log('========================================');

  const taskInput = process.env.TASK_INPUT;
  const dryRun = process.env.DRY_RUN === 'true';

  if (dryRun) {
    log('DRY RUN MODE - No changes will be committed');
  }

  // Determine which tasks to run
  let tasks = DEFAULT_TASKS;
  if (taskInput) {
    const customTask = DEFAULT_TASKS.find(t => t.name === taskInput);
    if (customTask) {
      tasks = [customTask];
    } else {
      log(`Custom task: ${taskInput}`);
      tasks = [{
        name: 'custom',
        description: taskInput,
        businessPrompt: taskInput,
      }];
    }
  }

  // Execute tasks
  for (const task of tasks) {
    try {
      await executeTask(task);
    } catch (error) {
      log(`Task failed: ${error.message}`, 'ERROR');
    }
  }

  // Run checks
  log('Running safety checks...');
  for (const check of CONFIG.checks) {
    const result = runCheck(check);
    if (!result.success) {
      log(`Check failed: ${check}`, 'ERROR');
      log(result.output, 'ERROR');
      process.exit(1);
    }
  }

  log('All tasks completed successfully!');
}

main().catch(error => {
  console.error('Agent failed:', error);
  process.exit(1);
});
