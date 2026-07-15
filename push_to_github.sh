#!/usr/bin/env bash
# One-shot: create the GitHub repo and push this monorepo.
# Requires the GitHub CLI (https://cli.github.com). Run from inside this folder.
set -euo pipefail

REPO="ai-engineering-projects"
VISIBILITY="private"   # change to "public" if you prefer

# 1. Make sure you're authenticated (opens a browser the first time)
gh auth status >/dev/null 2>&1 || gh auth login

# 2. Init git if needed
if [ ! -d .git ]; then
  git init
  git branch -M main
fi

git add .
git commit -m "Initial commit: 15-project AI engineering monorepo + P1 Support Knowledge Copilot scaffold" || true

# 3. Create the repo under your account and push
gh repo create "$REPO" --"$VISIBILITY" --source=. --remote=origin --push

echo "Done → https://github.com/$(gh api user -q .login)/$REPO"
