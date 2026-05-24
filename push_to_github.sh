#!/usr/bin/env bash
set -euo pipefail

REPO_URL="git@github.com:Geralt903/IOT104_coursedesign.git"
BRANCH="main"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_DIR"

echo "Project directory: $PROJECT_DIR"
echo "Target repository: $REPO_URL"

if ! command -v git >/dev/null 2>&1; then
  echo "Error: git is not installed or not in PATH." >&2
  exit 1
fi

if [ ! -d ".git" ]; then
  echo "Initializing git repository..."
  git init
fi

git branch -M "$BRANCH"

if git remote get-url origin >/dev/null 2>&1; then
  CURRENT_REMOTE="$(git remote get-url origin)"
  if [ "$CURRENT_REMOTE" != "$REPO_URL" ]; then
    echo "Updating origin remote:"
    echo "  old: $CURRENT_REMOTE"
    echo "  new: $REPO_URL"
    git remote set-url origin "$REPO_URL"
  fi
else
  echo "Adding origin remote..."
  git remote add origin "$REPO_URL"
fi

echo "Staging project files..."
git add .

if git diff --cached --quiet; then
  echo "No new changes to commit."
else
  COMMIT_MESSAGE="Upload IOT104 course design project"
  echo "Creating commit: $COMMIT_MESSAGE"
  git commit -m "$COMMIT_MESSAGE"
fi

echo "Pushing to GitHub..."
git push -u origin "$BRANCH"

echo "Done."
