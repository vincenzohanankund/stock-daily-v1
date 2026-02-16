#!/usr/bin/env bash
set -euo pipefail

BASE_BRANCH="${1:-main}"
UPSTREAM_REF="${2:-main}"
TS="$(date +%Y%m%d-%H%M%S)"
SYNC_BRANCH="codex/sync-upstream-${TS}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: run this script inside a git repository."
  exit 1
fi

if ! git remote get-url upstream >/dev/null 2>&1; then
  echo "Error: remote 'upstream' is missing."
  echo "Run: git remote add upstream <upstream-repo-url>"
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "Error: remote 'origin' is missing."
  echo "Run: git remote add origin <your-private-repo-url>"
  exit 1
fi

echo "[1/6] Fetch remotes"
git fetch origin --prune
git fetch upstream --prune

echo "[2/6] Checkout base branch: ${BASE_BRANCH}"
git checkout "${BASE_BRANCH}"

echo "[3/6] Fast-forward base branch from origin/${BASE_BRANCH}"
git pull --ff-only origin "${BASE_BRANCH}"

echo "[4/6] Create sync branch: ${SYNC_BRANCH}"
git checkout -b "${SYNC_BRANCH}"

echo "[5/6] Merge upstream/${UPSTREAM_REF}"
git merge "upstream/${UPSTREAM_REF}" --no-edit

echo "[6/6] Push sync branch"
git push -u origin "${SYNC_BRANCH}"

echo
echo "Done. Open a PR from ${SYNC_BRANCH} into ${BASE_BRANCH}."
