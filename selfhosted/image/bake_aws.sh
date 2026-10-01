#!/usr/bin/env bash
# Scripted AMI bake (no SSH, no inbound access needed):
#   1. launch a builder VM from the Canonical Ubuntu 24.04 AMI with install-runner-base.sh as user-data
#   2. the script powers the VM off on success (shutdown behavior = stop)
#   3. create an AMI from the stopped VM, wait until available, terminate the builder
#
# Required env: SUBNET_ID SECURITY_GROUP_ID
# Optional env: AWS_REGION INSTANCE_TYPE IMAGE_NAME OWNER_TAG RESOURCES_FILE (append created IDs)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
: "${SUBNET_ID:?}" "${SECURITY_GROUP_ID:?}"
AWS_REGION="${AWS_REGION:-us-east-1}"
INSTANCE_TYPE="${INSTANCE_TYPE:-m8a.large}"
IMAGE_NAME="${IMAGE_NAME:-ci-runner-ubuntu2404-$(date -u +%Y%m%d%H%M)}"
OWNER_TAG="${OWNER_TAG:-runner-benchmark}"
RESOURCES_FILE="${RESOURCES_FILE:-/dev/null}"
export AWS_DEFAULT_REGION="$AWS_REGION"

record() { echo "$(date -u +%FT%TZ) aws $1 $2 ${3:-}" >>"$RESOURCES_FILE"; }

base_ami="$(aws ssm get-parameter \
  --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id \
  --query Parameter.Value --output text)"
echo "base AMI: $base_ami"

userdata="$(mktemp)"
trap 'rm -f "$userdata"' EXIT
{
  echo '#!/bin/bash'
  echo 'set -euxo pipefail'
  echo 'cat >/root/install-runner-base.sh <<'"'"'__INSTALL__'"'"''
  cat "$here/install-runner-base.sh"
  echo '__INSTALL__'
  echo 'bash /root/install-runner-base.sh'
  echo 'rm -f /root/install-runner-base.sh'
  echo 'cloud-init clean --logs'
  echo 'sync; systemctl poweroff'
} >"$userdata"

iid="$(aws ec2 run-instances \
  --image-id "$base_ami" --instance-type "$INSTANCE_TYPE" \
  --subnet-id "$SUBNET_ID" --security-group-ids "$SECURITY_GROUP_ID" \
  --associate-public-ip-address \
  --instance-initiated-shutdown-behavior stop \
  --metadata-options HttpTokens=required,HttpEndpoint=enabled \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=20,VolumeType=gp3,DeleteOnTermination=true,Encrypted=true}' \
  --user-data "file://$userdata" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=rb-owner,Value=$OWNER_TAG},{Key=Name,Value=image-builder},{Key=rb-role,Value=image-builder}]" \
                       "ResourceType=volume,Tags=[{Key=rb-owner,Value=$OWNER_TAG}]" \
  --query 'Instances[0].InstanceId' --output text)"
record instance "$iid" "image-builder"
echo "builder instance: $iid (waiting for it to power off; ~5-10 min)"

deadline=$(( $(date +%s) + 1800 ))
while :; do
  state="$(aws ec2 describe-instances --instance-ids "$iid" --query 'Reservations[0].Instances[0].State.Name' --output text)"
  [ "$state" = "stopped" ] && break
  if [ "$(date +%s)" -gt "$deadline" ]; then
    echo "builder did not power off in 30 min; console tail:" >&2
    aws ec2 get-console-output --instance-id "$iid" --latest --output text | tail -40 >&2 || true
    exit 1
  fi
  sleep 15
done

ami="$(aws ec2 create-image --instance-id "$iid" --name "$IMAGE_NAME" \
  --description "Ubuntu 24.04 + docker + actions/runner" \
  --tag-specifications "ResourceType=image,Tags=[{Key=rb-owner,Value=$OWNER_TAG}]" "ResourceType=snapshot,Tags=[{Key=rb-owner,Value=$OWNER_TAG}]" \
  --query ImageId --output text)"
record ami "$ami" "$IMAGE_NAME"
echo "AMI: $ami (waiting for available)"
aws ec2 wait image-available --image-ids "$ami"
snap="$(aws ec2 describe-images --image-ids "$ami" --query 'Images[0].BlockDeviceMappings[0].Ebs.SnapshotId' --output text)"
record snapshot "$snap" "backs $ami"
aws ec2 terminate-instances --instance-ids "$iid" >/dev/null
echo "terminated builder $iid"
echo "AMI_ID=$ami"
