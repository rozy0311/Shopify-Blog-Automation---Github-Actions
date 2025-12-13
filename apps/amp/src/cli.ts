#!/usr/bin/env node
import { Command } from 'commander';
import { execSync } from 'child_process';
import { existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const program = new Command();

program
  .name('amp')
  .description('AMP CLI for Shopify Blog Automation')
  .version('1.0.0');

program
  .command('setup')
  .description('Install dependencies for all workspace apps')
  .action(() => {
    console.log('📦 Installing dependencies...');
    try {
      const rootDir = join(__dirname, '../../../');
      execSync('npm install --workspaces', { 
        cwd: rootDir, 
        stdio: 'inherit' 
      });
      console.log('✅ Dependencies installed successfully');
    } catch (error) {
      console.error('❌ Failed to install dependencies');
      process.exit(1);
    }
  });

program
  .command('build')
  .description('Build all workspace apps')
  .option('-w, --workspace <name>', 'Build specific workspace (executor, supervisor, or amp)')
  .action((options) => {
    const rootDir = join(__dirname, '../../../');
    
    try {
      if (options.workspace) {
        console.log(`🔨 Building ${options.workspace}...`);
        execSync(`npm run --workspace apps/${options.workspace} build`, {
          cwd: rootDir,
          stdio: 'inherit'
        });
      } else {
        console.log('🔨 Building all workspaces...');
        execSync('npm run --workspace apps/executor build', { cwd: rootDir, stdio: 'inherit' });
        execSync('npm run --workspace apps/supervisor build', { cwd: rootDir, stdio: 'inherit' });
        console.log('✅ Build completed successfully');
      }
    } catch (error) {
      console.error('❌ Build failed');
      process.exit(1);
    }
  });

program
  .command('run')
  .description('Run the executor')
  .option('-m, --mode <mode>', 'Execution mode: review or publish', 'review')
  .action((options) => {
    const rootDir = join(__dirname, '../../../');
    const executorPath = join(rootDir, 'apps/executor');
    
    console.log(`🚀 Running executor in ${options.mode} mode...`);
    
    try {
      execSync(`MODE=${options.mode} node dist/index.js`, {
        cwd: executorPath,
        stdio: 'inherit',
        env: { ...process.env, MODE: options.mode }
      });
      console.log('✅ Execution completed');
    } catch (error) {
      console.error('❌ Execution failed');
      process.exit(1);
    }
  });

program
  .command('supervise')
  .description('Run the supervisor')
  .action(() => {
    const rootDir = join(__dirname, '../../../');
    const supervisorPath = join(rootDir, 'apps/supervisor');
    
    console.log('🔍 Running supervisor...');
    
    try {
      execSync('node dist/index.js', {
        cwd: supervisorPath,
        stdio: 'inherit'
      });
      console.log('✅ Supervision completed');
    } catch (error) {
      console.error('❌ Supervision failed');
      process.exit(1);
    }
  });

program
  .command('status')
  .description('Check the status of the automation')
  .action(() => {
    const rootDir = join(__dirname, '../../../');
    
    console.log('📊 Checking automation status...\n');
    
    const executorBuilt = existsSync(join(rootDir, 'apps/executor/dist'));
    const supervisorBuilt = existsSync(join(rootDir, 'apps/supervisor/dist'));
    const ampBuilt = existsSync(join(rootDir, 'apps/amp/dist'));
    
    console.log(`Executor:   ${executorBuilt ? '✅ Built' : '❌ Not built'}`);
    console.log(`Supervisor: ${supervisorBuilt ? '✅ Built' : '❌ Not built'}`);
    console.log(`AMP CLI:    ${ampBuilt ? '✅ Built' : '❌ Not built'}`);
    
    if (!executorBuilt || !supervisorBuilt) {
      console.log('\n💡 Run "amp build" to build all components');
    }
  });

program
  .command('help-env')
  .description('Show required environment variables')
  .action(() => {
    console.log(`
📝 Required Environment Variables:

Executor:
  SHEETS_ID           - Google Sheet ID
  SHEETS_RANGE        - Sheet range (e.g., Sheet1!A:B)
  CONFIG_RANGE        - Config range (e.g., CONFIG!A:B)
  SHOPIFY_SHOP        - Shopify shop subdomain
  BLOG_HANDLE         - Blog handle (default: agritourism)
  AUTHOR              - Article author (default: The Rike)
  OPENAI_MODEL        - OpenAI model (default: gpt-4o-mini)
  WF_ENABLED          - Enable workflow (false for dry-run)
  SHOPIFY_TOKEN       - Shopify Admin API token
  OPENAI_API_KEY      - OpenAI API key
  GOOGLE_SERVICE_ACCOUNT_JSON - Google service account JSON

Supervisor:
  GITHUB_TOKEN        - GitHub token for API access
  SLACK_WEBHOOK       - (Optional) Slack webhook URL

💡 Copy .env.sample files in each app directory and customize them.
`);
  });

program.parse();
