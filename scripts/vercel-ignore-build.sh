#!/bin/sh
# Exit 0 when this commit only changes data, so Vercel skips the build.
# Exit 1 when application code changed, so the build runs.
# A missing previous commit builds, which is the safe direction.
set -eu
prev="${VERCEL_GIT_PREVIOUS_SHA:-}"
curr="${VERCEL_GIT_COMMIT_SHA:-HEAD}"
if [ -z "$prev" ]; then
  exit 1
fi
if ! git cat-file -e "${prev}^{commit}" 2>/dev/null; then
  git fetch --depth=50 origin "$prev" >/dev/null 2>&1 || exit 1
fi
names=$(git diff --name-only "$prev" "$curr")
if [ -z "$names" ]; then
  exit 0
fi
printf '%s\n' "$names" | grep -qvE '^(web-app/data/|data/)' && exit 1
exit 0
