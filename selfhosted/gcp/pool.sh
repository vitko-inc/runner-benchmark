#!/usr/bin/env bash
# Scale the persistent GCE runner pool and keep an uptime log.
#
#   pool.sh up <N>     mint a fresh registration token locally and apply pool_size=N
#   pool.sh down       apply pool_size=0 (runners are deregistered, VMs deleted)
#   pool.sh destroy    destroy everything (network included)
#   pool.sh status     list VMs and repository runners
#
# Env: TFVARS (var file with project/github_repo/image), TF_STATE (local state path),
#      POOL_LOG (CSV: utc_time,event,pool_size,vm_name,zone,created_or_deleted_at)
# GCP auth: uses `gcloud auth print-access-token` for the Terraform provider.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
: "${TFVARS:?}" "${TF_STATE:?}"
POOL_LOG="${POOL_LOG:-./pool-log.csv}"
export TF_DATA_DIR="${TF_DATA_DIR:-$(dirname "$TF_STATE")/gcp.terraform}"
export GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)"
repo="$(sed -n 's/^ *github_repo *= *"\(.*\)".*/\1/p' "$TFVARS")"
tf() { terraform -chdir="$here" "$@"; }
[ -d "$TF_DATA_DIR" ] || tf init -input=false -backend-config=path="$TF_STATE" >/dev/null
[ -f "$POOL_LOG" ] || echo "utc_time,event,pool_size,vm_name,zone,vm_time" >"$POOL_LOG"

snapshot() {  # log every VM currently in state with its creation time
  local event="$1" size="$2"
  tf output -json runners 2>/dev/null | jq -r '.[] | [.name, (.zone|split("/")|last)] | @tsv' |
    while IFS=$'\t' read -r name zone; do
      created="$(gcloud compute instances describe "$name" --zone "$zone" --format='value(creationTimestamp)' 2>/dev/null || true)"
      echo "$(date -u +%FT%TZ),$event,$size,$name,$zone,$created" >>"$POOL_LOG"
    done
  echo "$(date -u +%FT%TZ),$event,$size,,," >>"$POOL_LOG"
}

case "${1:-}" in
  up)
    n="${2:?pool size}"
    token="$(gh api -X POST "repos/${repo}/actions/runners/registration-token" --jq .token)"
    TF_VAR_registration_token="$token" tf apply -auto-approve -input=false -var-file="$TFVARS" -var "pool_size=$n"
    snapshot up "$n"
    ;;
  down)
    snapshot down-begin 0
    tf apply -auto-approve -input=false -var-file="$TFVARS" -var pool_size=0
    echo "$(date -u +%FT%TZ),down-complete,0,,," >>"$POOL_LOG"
    ;;
  destroy)
    snapshot destroy-begin 0
    tf destroy -auto-approve -input=false -var-file="$TFVARS"
    echo "$(date -u +%FT%TZ),destroy-complete,0,,," >>"$POOL_LOG"
    ;;
  status)
    tf output -json runners | jq -r '.[] | "\(.name) \(.zone|split("/")|last)"'
    gh api "repos/${repo}/actions/runners?per_page=100" --jq '.runners[] | "\(.name) \(.status) busy=\(.busy)"'
    ;;
  *) sed -n '2,12p' "$0"; exit 2 ;;
esac
