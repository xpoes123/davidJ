#!/usr/bin/env bash
set -euo pipefail

# Directory where the site is served from
DEPLOY_DIR=/var/www/davidj

echo "==> Deploying to $DEPLOY_DIR"

# Move into the deployment directory
cd "$DEPLOY_DIR"

# Pull the latest commit refs from the remote without modifying the working tree
git fetch origin main

# Hard-reset to match remote exactly — discards any local drift
git reset --hard origin/main

# Validate the Nginx configuration before reloading to catch syntax errors early
sudo nginx -t

# Reload Nginx to pick up any config changes (zero-downtime; workers drain gracefully)
sudo systemctl reload nginx

echo "==> Deploy complete at $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
