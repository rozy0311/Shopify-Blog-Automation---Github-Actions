# AMP CLI

Command-line interface for Shopify Blog Automation.

## Installation

Quick install via script:

```bash
curl -fsSL https://ampcode.com/install.sh | bash
```

Or install manually:

```bash
git clone https://github.com/rozy0311/Shopify-Blog-Automation---Github-Actions.git
cd Shopify-Blog-Automation---Github-Actions
npm install --workspaces
npm run --workspace apps/amp build
npm link apps/amp
```

## Usage

```bash
# Check status
amp status

# Setup and install dependencies
amp setup

# Build all components
amp build

# Build specific workspace
amp build --workspace executor

# Run executor in review mode (dry-run)
amp run

# Run executor in publish mode
amp run --mode publish

# Run supervisor
amp supervise

# Show environment variable help
amp help-env

# Show help
amp --help
```

## Commands

- `amp setup` - Install dependencies for all workspace apps
- `amp build` - Build all workspace apps (or specific with `--workspace`)
- `amp run` - Run the executor (`--mode review` or `--mode publish`)
- `amp supervise` - Run the supervisor
- `amp status` - Check the status of all components
- `amp help-env` - Display required environment variables

## Environment Setup

Each app needs its own `.env` file. Copy `.env.sample` in each directory:

```bash
cp apps/executor/.env.sample apps/executor/.env
cp apps/supervisor/.env.sample apps/supervisor/.env
```

Then edit the `.env` files with your credentials and configuration.

For required environment variables, run:

```bash
amp help-env
```
