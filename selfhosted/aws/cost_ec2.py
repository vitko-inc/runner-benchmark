#!/usr/bin/env python3
"""Per-job cost of the ephemeral EC2 baseline.

Inputs (written by ec2_launcher.py into its state dir):
  launches.jsonl         one record per launched instance (trigger job, runner name, instance id)
  instance_events.jsonl  state transitions observed by the launcher's 5 s monitor

Billed interval per instance = LaunchTime -> termination time, floored at 60 s
(EC2 Linux per-second billing with a 60 s minimum).

  LaunchTime       : EC2 describe-instances `LaunchTime` (captured by the monitor/launch record).
  termination time : in order of preference
     1. the timestamp inside describe-instances `StateTransitionReason`, e.g.
        "User initiated (2026-10-01 06:12:33 GMT)". EC2 includes it when terminate-instances
        is called (sweeper/reaper/operator), but NOT for a guest-initiated power-off, where the
        reason is just "User initiated". Read live while the instance is still visible
        (~1 h after termination), else from the monitor's copy.        -> end_source=transition_reason
     2. first time the monitor observed state shutting-down/terminated   -> end_source=monitor
        (the normal case: power-off after the job; at most one monitor interval, 5 s, late)
  CloudTrail is NOT used: a guest-initiated shutdown produces no TerminateInstances API event.

Cost = billed_s x on-demand $/h / 3600
     + root gp3 GB x $/GB-month prorated per second (1 month = 730 h)
     + public IPv4 $/h prorated per second (reported separately; also in total_usd)

The job a runner actually executed can differ from the job that triggered its launch
(JIT runners take any queued job with the label). With --resolve-jobs the script asks
the GitHub API which job ran on each runner name and keys rows by that job id.
"""

import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys

PRICE_PER_HOUR = {"m8a.large": 0.12172, "r8a.large": 0.15976}  # us-east-1 on-demand Linux, 2026-10-01
GP3_PER_GB_MONTH = 0.08
IPV4_PER_HOUR = 0.005
HOURS_PER_MONTH = 730.0

REASON_TS = re.compile(r"\((\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) GMT\)")


def parse_ts(s):
    if not s:
        return None
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def reason_ts(reason):
    m = REASON_TS.search(reason or "")
    if not m:
        return None
    return dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def live_describe(ids):
    """Best-effort describe of instances still visible in the EC2 API."""
    out = {}
    ids = list(ids)
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        res = subprocess.run(
            ["aws", "ec2", "describe-instances", "--filters", f"Name=instance-id,Values={','.join(chunk)}",
             "--output", "json"], capture_output=True, text=True)
        if res.returncode != 0:
            continue
        for r in json.loads(res.stdout)["Reservations"]:
            for inst in r["Instances"]:
                out[inst["InstanceId"]] = inst
    return out


def resolve_jobs(repo, launches):
    """runner_name -> job record, via the jobs of every run referenced by the launches."""
    by_runner = {}
    run_ids = sorted({str(rec["run_id"]) for rec in launches})
    names = {rec["runner_name"] for rec in launches}
    for run_id in run_ids:
        res = subprocess.run(["gh", "api", "--paginate", f"repos/{repo}/actions/runs/{run_id}/jobs?filter=all&per_page=100",
                              "--jq", ".jobs[] | tojson"], capture_output=True, text=True)
        for line in res.stdout.splitlines():
            job = json.loads(line)
            if job.get("runner_name") in names:
                by_runner[job["runner_name"]] = job
    return by_runner


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--state-dir", default=os.environ.get("RB_STATE_DIR", "./launcher-state"))
    p.add_argument("--repo", default=os.environ.get("RB_REPO"))
    p.add_argument("--resolve-jobs", action="store_true", help="look up the job that actually ran on each runner")
    p.add_argument("--root-gb", type=float, default=75)
    p.add_argument("--out", default="-")
    a = p.parse_args()

    launches = read_jsonl(os.path.join(a.state_dir, "launches.jsonl"))
    events = read_jsonl(os.path.join(a.state_dir, "instance_events.jsonl"))
    live = live_describe(rec["instance_id"] for rec in launches)
    jobs = resolve_jobs(a.repo, launches) if (a.resolve_jobs and a.repo) else {}

    ev_by_iid = {}
    for e in events:
        ev_by_iid.setdefault(e["instance_id"], []).append(e)

    cols = ["job_id", "trigger_job_id", "run_id", "runner_name", "instance_id", "instance_type",
            "launch_time", "end_time", "end_source", "billed_s", "compute_usd", "ebs_usd", "ipv4_usd",
            "total_usd", "job_started_at", "job_completed_at", "job_conclusion"]
    out = sys.stdout if a.out == "-" else open(a.out, "w", newline="")
    w = csv.DictWriter(out, fieldnames=cols)
    w.writeheader()
    for rec in launches:
        iid = rec["instance_id"]
        evs = ev_by_iid.get(iid, [])
        inst = live.get(iid, {})
        launch = parse_ts(inst.get("LaunchTime") or next((e["launch_time"] for e in evs if e.get("launch_time")), None)
                          or rec.get("launch_time"))
        end, src = None, ""
        if inst.get("State", {}).get("Name") in ("shutting-down", "terminated", "stopped"):
            end = reason_ts(inst.get("StateTransitionReason"))
            src = "transition_reason" if end else ""
        if not end:
            for e in evs:
                if e["state"] in ("shutting-down", "terminated", "stopped"):
                    end = reason_ts(e.get("state_transition_reason"))
                    src = "transition_reason" if end else ""
                    if not end:
                        end, src = parse_ts(e["observed_at"]), "monitor"
                    break
        itype = rec.get("instance_type") or inst.get("InstanceType") or "m8a.large"
        row = {"trigger_job_id": rec["job_id"], "run_id": rec["run_id"], "runner_name": rec["runner_name"],
               "instance_id": iid, "instance_type": itype,
               "launch_time": launch.isoformat() if launch else "", "end_time": end.isoformat() if end else "",
               "end_source": src or "still-running"}
        job = jobs.get(rec["runner_name"])
        if a.resolve_jobs:
            row["job_id"] = job["id"] if job else ""  # empty = runner never got a job (overhead)
        else:
            row["job_id"] = rec["job_id"]
        if job:
            row.update(job_started_at=job.get("started_at"), job_completed_at=job.get("completed_at"),
                       job_conclusion=job.get("conclusion"))
        elif a.resolve_jobs:
            row["job_conclusion"] = "no-job"
        if launch and end:
            billed = max(60.0, (end - launch).total_seconds())
            compute = billed * PRICE_PER_HOUR[itype] / 3600
            ebs = a.root_gb * GP3_PER_GB_MONTH * billed / (HOURS_PER_MONTH * 3600)
            ipv4 = IPV4_PER_HOUR * billed / 3600
            row.update(billed_s=round(billed, 1), compute_usd=f"{compute:.6f}", ebs_usd=f"{ebs:.6f}",
                       ipv4_usd=f"{ipv4:.6f}", total_usd=f"{compute + ebs + ipv4:.6f}")
        w.writerow(row)
    if out is not sys.stdout:
        out.close()


if __name__ == "__main__":
    main()
