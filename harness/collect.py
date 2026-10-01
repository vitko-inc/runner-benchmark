#!/usr/bin/env python3
"""Fetch GitHub's record of every dispatched run: the run, its jobs and steps, and the
rb-probe line from each job's log (CPU model, vCPUs, memory, swap, kernel).

Usage: GITHUB_TOKEN=... python3 harness/collect.py --dispatch results/<set>/dispatch.jsonl \
           --out results/<set>/raw/jobs.jsonl.gz
"""
import argparse
import gzip
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import gh  # noqa: E402

PROBE = re.compile(r'rb-probe cpu="([^"]*)" nproc=(\d+) mem_kib=(\d+) swap_kib=(\d+) kernel=(\S+)')
JOB_FIELDS = ("id", "name", "status", "conclusion", "created_at", "started_at", "completed_at",
              "labels", "runner_name", "runner_group_name", "run_attempt")


def probe(repo, job_id):
    try:
        text = gh.get(f"/repos/{repo}/actions/jobs/{job_id}/logs", raw=True).decode("utf-8", "replace")
    except Exception:
        return None
    for line in text.splitlines():
        if "rb-probe cpu=" in line and "echo" not in line:
            m = PROBE.search(line)
            if m:
                return {"cpu": m.group(1), "nproc": int(m.group(2)), "mem_kib": int(m.group(3)),
                        "swap_kib": int(m.group(4)), "kernel": m.group(5)}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dispatch", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-logs", action="store_true")
    a = ap.parse_args()
    recs = [json.loads(l) for l in open(a.dispatch) if l.strip()]
    recs = [r for r in recs if r.get("tag") and r.get("run_id")]
    done = set()
    if os.path.exists(a.out):
        with gzip.open(a.out, "rt") as f:
            done = {json.loads(l)["tag"] for l in f}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with gzip.open(a.out, "at") as out:
        for i, r in enumerate(recs):
            if r["tag"] in done:
                continue
            run = gh.get(f"/repos/{r['repo']}/actions/runs/{r['run_id']}")
            if run.get("status") != "completed":
                print(f"skip (not completed): {r['tag']}", file=sys.stderr)
                continue
            jobs = gh.paginate(f"/repos/{r['repo']}/actions/runs/{r['run_id']}/jobs?filter=all", "jobs")
            jl = []
            for j in jobs:
                d = {k: j.get(k) for k in JOB_FIELDS}
                d["steps"] = [{k: s.get(k) for k in ("number", "name", "conclusion", "started_at", "completed_at")}
                              for s in j.get("steps") or []]
                d["probe"] = None if a.no_logs else probe(r["repo"], j["id"])
                jl.append(d)
            row = dict(r, run={k: run.get(k) for k in ("id", "status", "conclusion", "created_at",
                                                       "run_started_at", "updated_at", "run_attempt")},
                       jobs=jl)
            out.write(json.dumps(row, sort_keys=True) + "\n")
            if i % 25 == 0:
                print(f"{i + 1}/{len(recs)}", file=sys.stderr)


if __name__ == "__main__":
    main()
