#!/bin/bash
# Runs on every boot. First boot: register a persistent runner and install it as a
# systemd service. Later boots: the service starts on its own.
set -euo pipefail
md() { curl -fsS -H 'Metadata-Flavor: Google' "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1"; }
cd /opt/actions-runner
if [ ! -f .runner ]; then
  repo="$(md rb-repo)"
  labels="$(md rb-labels)"
  token="$(md rb-registration-token)"
  sudo -u runner ./config.sh --unattended \
    --url "https://github.com/${repo}" --token "${token}" \
    --name "$(hostname -s)" --labels "${labels}" --replace --disableupdate
  ./svc.sh install runner
fi
./svc.sh start || true
