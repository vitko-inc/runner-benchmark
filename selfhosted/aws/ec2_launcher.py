#!/usr/bin/env python3
"""Ephemeral EC2 runner launcher (one fresh VM per queued job).

A deliberately small stand-in for a webhook-driven autoscaler, for benchmarking:

  every POLL seconds:
    list the repository's queued / in-progress workflow runs   (conditional GETs)
    for each queued job whose labels include LABEL and that we have not handled:
      mint a single-use JIT runner config  (POST .../actions/runners/generate-jitconfig)
      launch one instance from the launch template with the JIT config in user-data
  the instance runs `run.sh --jitconfig ...` and powers off when the runner exits;
  the launch template sets InstanceInitiatedShutdownBehavior=terminate.

  every 5 s: record state transitions of launched instances (for cost_ec2.py)
  every 60 s: safety sweep - terminate own instances older than MAX_AGE minutes, and
              reap runners still idle IDLE minutes after launch (their job was cancelled or
              taken by another runner): delete the registration, terminate the instance.
              "own" = carries the owner tag AND its ID is listed in RESOURCES_FILE.
  Only one launcher may run per state dir (file lock); SIGTERM/SIGINT stop it cleanly.

Only the JIT config (single-use, scoped to one runner) is sent to the VM. The
GitHub token used to mint it is read from the local `gh` login (or GITHUB_TOKEN)
and never leaves this machine.

Dependencies: Python 3.9+ stdlib, the `aws` CLI (default credentials) and `gh`.
"""

import argparse
import datetime as dt
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

API = "https://api.github.com"


def now_iso():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def log(msg):
    print(f"{now_iso()} {msg}", flush=True)


# --------------------------------------------------------------------------- GitHub


class GitHub:
    def __init__(self, repo, token):
        self.repo = repo
        self._token = token
        self._etag = {}
        self._cache = {}
        self.rate_remaining = None
        self.rate_reset = 0

    def _req(self, method, path, body=None, conditional=False):
        url = path if path.startswith("http") else API + path
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if conditional and url in self._etag:
            req.add_header("If-None-Match", self._etag[url])
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                self._note_rate(resp.headers)
                payload = resp.read()
                parsed = json.loads(payload) if payload else None
                if conditional and resp.headers.get("ETag"):
                    self._etag[url] = resp.headers["ETag"]
                    self._cache[url] = parsed
                return resp.status, parsed
        except urllib.error.HTTPError as e:
            self._note_rate(e.headers)
            if e.code == 304 and conditional:
                return 304, self._cache[url]
            detail = e.read().decode(errors="replace")[:300]
            raise RuntimeError(f"GitHub {method} {path} -> {e.code}: {detail}") from None

    def _note_rate(self, headers):
        if headers and headers.get("X-RateLimit-Remaining") is not None:
            self.rate_remaining = int(headers["X-RateLimit-Remaining"])
            self.rate_reset = int(headers.get("X-RateLimit-Reset", "0"))

    def get(self, path, conditional=True):
        return self._req("GET", path, conditional=conditional)[1]

    def queued_jobs(self, label):
        """Queued jobs (in queued or in-progress runs) whose labels include `label`."""
        out = []
        for status in ("queued", "in_progress"):
            runs = self.get(f"/repos/{self.repo}/actions/runs?status={status}&per_page=100")
            for run in runs.get("workflow_runs", []):
                jobs = self.get(f"/repos/{self.repo}/actions/runs/{run['id']}/jobs?filter=latest&per_page=100")
                for job in jobs.get("jobs", []):
                    if job.get("status") == "queued" and label in (job.get("labels") or []):
                        out.append(job)
        return out

    def jit_config(self, name, label, runner_group_id):
        body = {"name": name, "runner_group_id": runner_group_id, "labels": [label], "work_folder": "_work"}
        _, resp = self._req("POST", f"/repos/{self.repo}/actions/runners/generate-jitconfig", body)
        return resp["runner"]["id"], resp["encoded_jit_config"]

    def runners(self):
        out, page = [], 1
        while True:
            resp = self.get(f"/repos/{self.repo}/actions/runners?per_page=100&page={page}", conditional=False)
            out += resp.get("runners", [])
            if len(resp.get("runners", [])) < 100:
                return out
            page += 1

    def delete_runner(self, runner_id):
        try:
            self._req("DELETE", f"/repos/{self.repo}/actions/runners/{runner_id}")
        except RuntimeError as e:
            log(f"warn: could not delete runner {runner_id}: {e}")


def github_token():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    return subprocess.run(["gh", "auth", "token"], check=True, capture_output=True, text=True).stdout.strip()


# --------------------------------------------------------------------------- AWS


def aws(*args):
    res = subprocess.run(["aws", *args, "--output", "json"], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"aws {' '.join(args[:2])}: {res.stderr.strip()[:500]}")
    return json.loads(res.stdout) if res.stdout.strip() else None


USER_DATA = """#!/bin/bash
# Ephemeral runner: run exactly one job, then power off (instance terminates).
# Timing lines also go to the serial console (visible via `aws ec2 get-console-output`).
exec >>/var/log/ci-runner.log 2>&1
say() {{ echo "ci-runner: $* uptime=$(cut -d' ' -f1 /proc/uptime)s" | tee /dev/console; }}
say "user-data start"
systemd-analyze 2>/dev/null | head -1 | tee /dev/console
cd /opt/actions-runner
timeout --kill-after=60s {max_minutes}m sudo -u runner -H ./run.sh --jitconfig '{jit}'
say "runner exited rc=$?"
sync
systemctl poweroff
"""


# --------------------------------------------------------------------------- state


class Store:
    """Small JSON/JSONL files in a local state directory."""

    def __init__(self, state_dir, resources_file):
        os.makedirs(state_dir, exist_ok=True)
        self.handled_path = os.path.join(state_dir, "handled_jobs.json")
        self.launches_path = os.path.join(state_dir, "launches.jsonl")
        self.events_path = os.path.join(state_dir, "instance_events.jsonl")
        self.resources_file = resources_file
        self.lock = threading.Lock()
        self.handled = set()
        if os.path.exists(self.handled_path):
            with open(self.handled_path) as f:
                self.handled = set(json.load(f))

    def save_handled(self):
        with self.lock:
            tmp = self.handled_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(sorted(self.handled), f)
            os.replace(tmp, self.handled_path)

    def append(self, path, rec):
        with self.lock, open(path, "a") as f:
            f.write(json.dumps(rec) + "\n")

    def record_resource(self, instance_id, note):
        with self.lock, open(self.resources_file, "a") as f:
            f.write(f"{now_iso()} aws instance {instance_id} {note}\n")

    def own_instance_ids(self):
        if not os.path.exists(self.resources_file):
            return set()
        with open(self.resources_file) as f:
            return set(re.findall(r"\b(i-[0-9a-f]{8,17})\b", f.read()))


# --------------------------------------------------------------------------- launcher


class Launcher:
    def __init__(self, args, gh, store):
        self.a = args
        self.gh = gh
        self.store = store
        self.pool = ThreadPoolExecutor(max_workers=args.max_parallel_launches)
        self.attempts = {}
        self.inflight = set()
        self.last_state = {}

    def launch(self, job):
        job_id = job["id"]
        name = f"{self.a.label}-{job_id}-{uuid.uuid4().hex[:6]}"
        runner_id = None
        try:
            runner_id, jit = self.gh.jit_config(name, self.a.label, self.a.runner_group_id)
            with tempfile.NamedTemporaryFile("w", delete=False, prefix="ud-") as f:
                os.chmod(f.name, 0o600)
                f.write(USER_DATA.format(jit=jit, max_minutes=self.a.max_job_minutes))
                ud_path = f.name
            try:
                tags = [
                    {"Key": "Name", "Value": name},
                    {"Key": self.a.owner_tag_key, "Value": self.a.owner_tag_value},
                    {"Key": "rb-job-id", "Value": str(job_id)},
                    {"Key": "rb-run-id", "Value": str(job["run_id"])},
                    {"Key": "rb-runner-name", "Value": name},
                ]
                spec = json.dumps([{"ResourceType": "instance", "Tags": tags}])
                out = aws(
                    "ec2", "run-instances",
                    "--launch-template", f"LaunchTemplateId={self.a.launch_template_id},Version=$Latest",
                    "--count", "1",
                    *(["--instance-type", self.a.instance_type] if self.a.instance_type else []),
                    "--user-data", f"file://{ud_path}",
                    "--tag-specifications", spec,
                )
            finally:
                os.unlink(ud_path)
            inst = out["Instances"][0]
            iid = inst["InstanceId"]
            self.store.record_resource(iid, f"rb-ec2-eph job={job_id}")
            rec = {
                "job_id": job_id, "run_id": job["run_id"], "job_created_at": job.get("created_at"),
                "runner_name": name, "runner_id": runner_id, "instance_id": iid,
                "instance_type": inst.get("InstanceType"), "launch_time": inst.get("LaunchTime"),
                "launched_at": now_iso(),
            }
            self.store.append(self.store.launches_path, rec)
            log(f"launched {iid} for job {job_id} (run {job['run_id']}) runner={name}")
        except Exception as e:  # noqa: BLE001 - keep the loop alive
            log(f"launch failed for job {job_id}: {e}")
            if runner_id:
                self.gh.delete_runner(runner_id)
            self.attempts[job_id] = self.attempts.get(job_id, 0) + 1
            if self.attempts[job_id] < self.a.max_attempts:
                with self.store.lock:
                    self.store.handled.discard(job_id)
                self.store.save_handled()
        finally:
            with self.store.lock:
                self.inflight.discard(job_id)

    def poll_jobs(self):
        for job in self.gh.queued_jobs(self.a.label):
            jid = job["id"]
            with self.store.lock:
                if jid in self.store.handled or jid in self.inflight:
                    continue
                self.store.handled.add(jid)
                self.inflight.add(jid)
            self.store.save_handled()
            log(f"queued job {jid} ({job.get('name')}) run {job['run_id']} -> launching")
            self.pool.submit(self.launch, job)

    def _own_instances(self, states=None):
        """Instances carrying the owner tag whose IDs are also in our resources file."""
        filters = [f"Name=tag:{self.a.owner_tag_key},Values={self.a.owner_tag_value}"]
        if states:
            filters.append(f"Name=instance-state-name,Values={','.join(states)}")
        res = aws("ec2", "describe-instances", "--filters", *filters)
        own = self.store.own_instance_ids()
        return [i for r in res["Reservations"] for i in r["Instances"] if i["InstanceId"] in own]

    def monitor(self):
        for i in self._own_instances():
            iid, state = i["InstanceId"], i["State"]["Name"]
            if self.last_state.get(iid) == state:
                continue
            self.last_state[iid] = state
            self.store.append(self.store.events_path, {
                "instance_id": iid, "state": state, "observed_at": now_iso(),
                "launch_time": i.get("LaunchTime"),
                "state_transition_reason": i.get("StateTransitionReason"),
                "state_reason": (i.get("StateReason") or {}).get("Message"),
            })

    def sweep(self):
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=self.a.max_age_minutes)
        old = []
        for i in self._own_instances(["pending", "running", "stopping", "stopped"]):
            launched = dt.datetime.fromisoformat(i["LaunchTime"].replace("Z", "+00:00"))
            if launched < cutoff:
                old.append(i["InstanceId"])
        if old:
            log(f"sweeper: terminating {len(old)} instance(s) older than {self.a.max_age_minutes} min: {old}")
            aws("ec2", "terminate-instances", "--instance-ids", *old)

    def reap_idle(self):
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=self.a.idle_minutes)
        launches = {}
        if os.path.exists(self.store.launches_path):
            with open(self.store.launches_path) as f:
                for line in f:
                    rec = json.loads(line)
                    launches[rec["runner_name"]] = rec
        own = self.store.own_instance_ids()
        for r in self.gh.runners():
            rec = launches.get(r["name"])
            if not rec or r.get("busy"):
                continue
            if dt.datetime.fromisoformat(rec["launched_at"].replace("Z", "+00:00")) > cutoff:
                continue
            log(f"reaper: runner {r['name']} idle {self.a.idle_minutes}+ min; removing it and {rec['instance_id']}")
            self.gh.delete_runner(r["id"])
            if rec["instance_id"] in own:
                try:
                    aws("ec2", "terminate-instances", "--instance-ids", rec["instance_id"])
                except RuntimeError as e:
                    log(f"reaper: terminate failed: {e}")

    def run(self):
        self.stopping = False

        def _stop(signum, _frame):
            log(f"signal {signum}: stopping after in-flight launches")
            self.stopping = True

        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)
        log(f"launcher up: repo={self.a.repo} label={self.a.label} lt={self.a.launch_template_id}")
        last_mon = last_sweep = 0.0
        while not self.stopping:
            t0 = time.time()
            try:
                self.poll_jobs()
            except Exception as e:  # noqa: BLE001
                log(f"poll error: {e}")
            if self.gh.rate_remaining is not None and self.gh.rate_remaining < 100:
                wait = max(5, self.gh.rate_reset - int(time.time()))
                log(f"GitHub rate limit low ({self.gh.rate_remaining}); sleeping {wait}s")
                time.sleep(wait)
            if t0 - last_mon >= 5:
                last_mon = t0
                try:
                    self.monitor()
                except Exception as e:  # noqa: BLE001
                    log(f"monitor error: {e}")
            if t0 - last_sweep >= 60:
                last_sweep = t0
                for step in (self.sweep, self.reap_idle):
                    try:
                        step()
                    except Exception as e:  # noqa: BLE001
                        log(f"{step.__name__} error: {e}")
            time.sleep(max(0.0, self.a.poll_seconds - (time.time() - t0)))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", default=os.environ.get("RB_REPO"), help="owner/name")
    p.add_argument("--label", default=os.environ.get("RB_LABEL", "rb-ec2-eph"))
    p.add_argument("--instance-type", default=os.environ.get("RB_INSTANCE_TYPE", ""),
                   help="override the launch template's instance type, e.g. r8a.large (2 vCPU / 16 GiB) for "
                        "the next memory size; run a second launcher with its own --label and --state-dir")
    p.add_argument("--launch-template-id", default=os.environ.get("RB_LAUNCH_TEMPLATE_ID"))
    p.add_argument("--runner-group-id", type=int, default=1)
    p.add_argument("--state-dir", default=os.environ.get("RB_STATE_DIR", "./launcher-state"))
    p.add_argument("--resources-file", default=os.environ.get("RB_RESOURCES_FILE", "./resources.txt"),
                   help="append-only list of created resource IDs; also the sweeper's allow-list")
    p.add_argument("--owner-tag", default="rb-owner=runner-benchmark", help="key=value tag on every instance")
    p.add_argument("--poll-seconds", type=float, default=2.0)
    p.add_argument("--max-job-minutes", type=int, default=80, help="hard runner timeout inside the VM")
    p.add_argument("--max-age-minutes", type=int, default=90, help="sweeper threshold")
    p.add_argument("--idle-minutes", type=int, default=10, help="reap runners idle this long after launch")
    p.add_argument("--max-parallel-launches", type=int, default=16)
    p.add_argument("--max-attempts", type=int, default=5)
    p.add_argument("--sweep-only", action="store_true", help="run one monitor+sweep pass and exit")
    a = p.parse_args()
    a.owner_tag_key, a.owner_tag_value = a.owner_tag.split("=", 1)
    if not a.repo or (not a.launch_template_id and not a.sweep_only):
        p.error("--repo and --launch-template-id are required")

    store = Store(a.state_dir, a.resources_file)
    gh = GitHub(a.repo, None if a.sweep_only else github_token())
    launcher = Launcher(a, gh, store)
    if a.sweep_only:
        launcher.monitor()
        launcher.sweep()
        return
    lock = open(os.path.join(a.state_dir, "launcher.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit(f"another launcher is already running with state dir {a.state_dir}")
    launcher.run()
    launcher.pool.shutdown(wait=True)
    log("launcher stopped")


if __name__ == "__main__":
    sys.exit(main())
