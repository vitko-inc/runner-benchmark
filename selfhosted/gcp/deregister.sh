#!/usr/bin/env bash
# Removes a repository runner registration by name using the local `gh` login.
# Usage: deregister.sh <owner/repo> <runner-name>
set -euo pipefail
repo="$1"; name="$2"
id="$(gh api "repos/${repo}/actions/runners?per_page=100" --paginate \
  --jq ".runners[] | select(.name == \"${name}\") | .id" | head -1)"
if [ -z "$id" ]; then
  echo "deregister: runner ${name} not registered in ${repo}"; exit 0
fi
for attempt in 1 2 3 4 5 6; do
  if gh api -X DELETE "repos/${repo}/actions/runners/${id}" >/dev/null 2>&1; then
    echo "deregister: removed ${name} (${id})"; exit 0
  fi
  echo "deregister: ${name} busy or API error, retry ${attempt}"; sleep 10
done
echo "deregister: FAILED to remove ${name} (${id})" >&2
exit 1
