#!/usr/bin/env bash
# Provisions an Ubuntu 24.04 machine into a self-hosted GitHub Actions runner base image.
# Used by both bake scripts (AWS and GCP). Runs as root on a fresh Ubuntu 24.04 VM.
#
# Result:
#   - build tooling: git curl unzip jq zstd build-essential python3 (+venv/pip)
#   - Docker Engine + buildx plugin (from Docker's apt repo)
#   - user "runner" with passwordless sudo, member of the docker group
#   - actions/runner pre-extracted in /opt/actions-runner (dependencies installed)
#   - apt background timers disabled so jobs never wait on the dpkg lock
set -euxo pipefail

RUNNER_VERSION="${RUNNER_VERSION:-2.337.0}"
RUNNER_SHA256="${RUNNER_SHA256:-70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613}"
RUNNER_USER="${RUNNER_USER:-runner}"
RUNNER_DIR="${RUNNER_DIR:-/opt/actions-runner}"
export DEBIAN_FRONTEND=noninteractive

# 1. Stop background apt activity (it would otherwise race `apt-get install` inside jobs).
systemctl stop apt-daily.timer apt-daily-upgrade.timer unattended-upgrades.service || true
systemctl disable apt-daily.timer apt-daily-upgrade.timer unattended-upgrades.service || true
systemctl mask apt-daily.service apt-daily-upgrade.service || true
cat >/etc/apt/apt.conf.d/99-ci-no-periodic <<'EOF'
APT::Periodic::Enable "0";
APT::Periodic::Update-Package-Lists "0";
APT::Periodic::Unattended-Upgrade "0";
EOF
for _ in $(seq 1 120); do
  fuser /var/lib/dpkg/lock-frontend /var/lib/apt/lists/lock >/dev/null 2>&1 || break
  sleep 2
done

# 2. Base packages.
apt-get update
apt-get -y -o Dpkg::Options::=--force-confold upgrade
apt-get install -y --no-install-recommends \
  git curl wget unzip zip jq zstd xz-utils tar ca-certificates gnupg lsb-release \
  build-essential pkg-config libssl-dev python3 python3-venv python3-pip python3-dev \
  sudo acl rsync file openssh-client

# 3. Docker Engine + buildx from Docker's repository.
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  >/etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker containerd

# 4. Runner user: passwordless sudo, docker group.
id "$RUNNER_USER" >/dev/null 2>&1 || useradd -m -s /bin/bash "$RUNNER_USER"
usermod -aG docker "$RUNNER_USER"
echo "$RUNNER_USER ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/90-ci-runner
chmod 0440 /etc/sudoers.d/90-ci-runner
visudo -cf /etc/sudoers.d/90-ci-runner

# 5. actions/runner, pre-extracted.
mkdir -p "$RUNNER_DIR"
curl -fsSL -o /tmp/runner.tar.gz \
  "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
echo "${RUNNER_SHA256}  /tmp/runner.tar.gz" | sha256sum -c -
tar -xzf /tmp/runner.tar.gz -C "$RUNNER_DIR"
rm -f /tmp/runner.tar.gz
"$RUNNER_DIR/bin/installdependencies.sh"
chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"

# 6. Image metadata + cleanup.
cat >/etc/ci-runner-image <<EOF
runner_version=${RUNNER_VERSION}
built_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
apt-get clean
rm -rf /tmp/* /var/tmp/*   # apt lists are kept so jobs can `apt-get install` without an update first
docker version
docker buildx version
sudo -u "$RUNNER_USER" sudo -n true
echo "ci-runner-base: OK"
