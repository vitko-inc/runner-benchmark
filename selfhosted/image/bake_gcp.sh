#!/usr/bin/env bash
# Scripted GCE image bake (no SSH, no inbound access needed):
#   1. create a builder VM from the Ubuntu 24.04 image with install-runner-base.sh as startup-script
#   2. the script powers the VM off on success
#   3. create an image from the builder's boot disk, delete the builder
#
# Required env: GCP_PROJECT SUBNET (name of a subnetwork in GCP_ZONE's region)
# Optional env: GCP_ZONE MACHINE_TYPE IMAGE_NAME IMAGE_FAMILY OWNER_LABEL RESOURCES_FILE
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
: "${GCP_PROJECT:?}" "${SUBNET:?}"
GCP_ZONE="${GCP_ZONE:-us-east4-a}"
MACHINE_TYPE="${MACHINE_TYPE:-n4d-standard-2}"
IMAGE_FAMILY="${IMAGE_FAMILY:-ci-runner-ubuntu2404}"
IMAGE_NAME="${IMAGE_NAME:-${IMAGE_FAMILY}-$(date -u +%Y%m%d%H%M)}"
OWNER_LABEL="${OWNER_LABEL:-runner-benchmark}"
RESOURCES_FILE="${RESOURCES_FILE:-/dev/null}"
builder="image-builder-$(date -u +%H%M%S)"
gc() { gcloud --project "$GCP_PROJECT" --quiet "$@"; }
record() { echo "$(date -u +%FT%TZ) gcp $1 $2 ${3:-}" >>"$RESOURCES_FILE"; }

script="$(mktemp)"
trap 'rm -f "$script"' EXIT
{
  echo '#!/bin/bash'
  echo 'set -euxo pipefail'
  echo '[ -f /etc/ci-runner-image ] && exit 0'
  echo 'cat >/root/install-runner-base.sh <<'"'"'__INSTALL__'"'"''
  cat "$here/install-runner-base.sh"
  echo '__INSTALL__'
  echo 'bash /root/install-runner-base.sh'
  echo 'rm -f /root/install-runner-base.sh'
  echo 'cloud-init clean --logs || true'
  echo 'sync; systemctl poweroff'
} >"$script"

disk_type=hyperdisk-balanced
case "$MACHINE_TYPE" in n1-*|n2-*|n2d-*|e2-*) disk_type=pd-balanced ;; esac

gc compute instances create "$builder" --zone "$GCP_ZONE" \
  --machine-type "$MACHINE_TYPE" --subnet "$SUBNET" \
  --image-family ubuntu-2404-lts-amd64 --image-project ubuntu-os-cloud \
  --boot-disk-size 20GB --boot-disk-type "$disk_type" \
  --no-service-account --no-scopes \
  --labels "rb-owner=${OWNER_LABEL},rb-role=image-builder" \
  --metadata block-project-ssh-keys=true \
  --metadata-from-file startup-script="$script" >/dev/null
record instance "$builder" "zone=$GCP_ZONE image-builder"
echo "builder VM: $builder (waiting for it to power off; ~5-10 min)"

deadline=$(( $(date +%s) + 1800 ))
while :; do
  status="$(gc compute instances describe "$builder" --zone "$GCP_ZONE" --format='value(status)')"
  [ "$status" = "TERMINATED" ] && break
  if [ "$(date +%s)" -gt "$deadline" ]; then
    echo "builder did not power off in 30 min; serial tail:" >&2
    gc compute instances get-serial-port-output "$builder" --zone "$GCP_ZONE" 2>/dev/null | tail -40 >&2 || true
    exit 1
  fi
  sleep 15
done

gc compute images create "$IMAGE_NAME" --family "$IMAGE_FAMILY" \
  --source-disk "$builder" --source-disk-zone "$GCP_ZONE" \
  --labels "rb-owner=${OWNER_LABEL}" >/dev/null
record image "projects/${GCP_PROJECT}/global/images/${IMAGE_NAME}" "family=$IMAGE_FAMILY"
gc compute instances delete "$builder" --zone "$GCP_ZONE" >/dev/null
echo "deleted builder $builder"
echo "IMAGE=projects/${GCP_PROJECT}/global/images/${IMAGE_NAME}"
