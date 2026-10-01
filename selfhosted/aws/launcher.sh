#!/usr/bin/env bash
# Start/stop ec2_launcher.py in the background.
#   launcher.sh start | stop | status | sweep
# Env: RB_REPO RB_LAUNCH_TEMPLATE_ID RB_STATE_DIR RB_RESOURCES_FILE (see ec2_launcher.py --help)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
: "${RB_STATE_DIR:?}"
mkdir -p "$RB_STATE_DIR"
pidf="$RB_STATE_DIR/launcher.pid"
running() { [ -f "$pidf" ] && kill -0 "$(cat "$pidf")" 2>/dev/null; }
case "${1:-}" in
  start)
    running && { echo "already running (pid $(cat "$pidf"))"; exit 0; }
    nohup python3 -u "$here/ec2_launcher.py" >>"$RB_STATE_DIR/launcher.log" 2>&1 &
    echo $! >"$pidf"; echo "started pid $!; log: $RB_STATE_DIR/launcher.log" ;;
  stop)
    if running; then
      pid="$(cat "$pidf")"; kill -TERM "$pid"; echo "stopping pid $pid"
      for _ in $(seq 1 60); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
      kill -0 "$pid" 2>/dev/null && { echo "still running after 60 s; sending KILL"; kill -KILL "$pid"; }
    else echo "not running"; fi
    rm -f "$pidf" ;;
  status) running && echo "running pid $(cat "$pidf")" || echo "not running" ;;
  sweep) python3 "$here/ec2_launcher.py" --sweep-only ;;
  *) sed -n '2,4p' "$0"; exit 2 ;;
esac
