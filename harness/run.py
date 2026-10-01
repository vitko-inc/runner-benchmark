#!/usr/bin/env python3
"""Dispatch benchmark rounds and record every dispatched run.

Usage:
  GITHUB_TOKEN=... python3 harness/run.py --plan plans/<name>.json --targets <targets.json> \
      --out results/<set>/dispatch.jsonl [--session s1] [--dry-run]

The plan says which workloads and providers run, how many warm-up and measured rounds, and
which workloads run in which lane. The targets file (kept outside this repository) maps each
provider id to the repository where its runs happen and the runs-on label to use.

Within a round, every lane runs in parallel. A lane takes its workloads one at a time: it
dispatches the workload to every provider within a few seconds, in random order, and waits
until all of those runs have finished. Burst workloads run after the lanes, as their own step:
every provider gets N copies at once.
"""
import argparse
import datetime as dt
import json
import os
import random
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(__file__))
import gh  # noqa: E402

LOCK = threading.Lock()
POLL_S = 10


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path):
    with open(path) as f:
        return json.load(f)


def record(out, rec):
    with LOCK:
        with open(out, "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")


def find_run(repo, workflow, tag, since, timeout=300):
    """Find the run whose run-name is the tag (dispatch returns no id on older API versions)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        runs = gh.get(f"/repos/{repo}/actions/workflows/{workflow}/runs?event=workflow_dispatch"
                      f"&created=>={since}&per_page=100")["workflow_runs"]
        for r in runs:
            if r.get("display_title") == tag or r.get("name") == tag:
                return r["id"]
        time.sleep(3)
    return None


def dispatch(target, workload, tag, split, dry):
    repo = target["repo"]
    label = target.get("runs_on_by_workload", {}).get(workload["id"], target["runs_on"])
    inputs = {"runs_on": label, "tag": tag}
    if workload.get("splittable") or split:
        inputs["split"] = "true" if split else "false"
    if dry:
        return {"run_id": None, "dispatched_at": now()}
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    at = now()
    resp = gh.post(f"/repos/{repo}/actions/workflows/{workload['workflow']}/dispatches",
                   {"ref": target.get("ref", "main"), "inputs": inputs, "return_run_details": True})
    run_id = (resp or {}).get("workflow_run_id")
    return {"run_id": run_id, "dispatched_at": at, "since": since}


def wait_all(items, timeout_s):
    """items: list of dicts with repo, run_id. Blocks until every run is completed or times out."""
    deadline = time.time() + timeout_s
    pending = {(i["repo"], i["run_id"]) for i in items if i.get("run_id")}
    while pending and time.time() < deadline:
        for repo, rid in list(pending):
            try:
                r = gh.get(f"/repos/{repo}/actions/runs/{rid}")
            except Exception as e:  # transient; retry on the next poll
                print(f"[{now()}] poll error {repo} {rid}: {e}", file=sys.stderr)
                continue
            if r.get("status") == "completed":
                pending.discard((repo, rid))
        if pending:
            time.sleep(POLL_S)
    return pending


def run_group(plan, targets, workload, providers, meta, out, dry, copies=1):
    """Dispatch one workload to all providers (copies each), then wait for all."""
    jobs = [(p, c) for p in providers for c in range(copies)]
    random.shuffle(jobs)
    sent = []
    for p, c in jobs:
        t = targets[p]
        split = bool(t.get("split"))
        tag = "rb/{set}/{session}/{round}/{wl}/{p}/{c}".format(wl=workload["id"], p=p, c=c, **meta)
        d = dispatch(t, workload, tag, split, dry)
        if not dry and d["run_id"] is None:
            d["run_id"] = find_run(t["repo"], workload["workflow"], tag, d["since"])
        rec = dict(meta, workload=workload["id"], provider=p, copy=c, tag=tag, repo=t["repo"],
                   workflow=workload["workflow"], run_id=d["run_id"], dispatched_at=d["dispatched_at"],
                   kind="burst" if copies > 1 else "single")
        record(out, rec)
        sent.append(rec)
    if dry:
        return
    left = wait_all(sent, plan.get("run_timeout_s", 7200))
    if left:
        print(f"[{now()}] TIMEOUT {workload['id']} {sorted(left)}", file=sys.stderr)
        record(out, dict(meta, workload=workload["id"], event="timeout", runs=sorted(map(list, left))))


def lane_worker(plan, targets, wls, providers_for, meta, out, dry):
    for wid in wls:
        w = plan["workloads"][wid]
        print(f"[{now()}] {meta['phase']} r{meta['round']} {wid}", flush=True)
        run_group(plan, targets, w, providers_for(wid), meta, out, dry)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--session", default="s1")
    ap.add_argument("--start-round", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    plan, targets = load(a.plan), load(a.targets)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    rng_seed = plan.get("seed")
    if rng_seed is not None:
        random.seed(f"{rng_seed}/{a.session}")

    def providers_for(wid):
        only = plan["workloads"][wid].get("providers")
        ps = [p for p in plan["providers"] if (only is None or p in only)]
        return [p for p in ps if p in targets and wid not in targets[p].get("skip", [])
                and ("only" not in targets[p] or wid in targets[p]["only"])]

    total = plan["warmup_rounds"] + plan["measured_rounds"]
    for rnd in range(a.start_round, total + 1):
        phase = "warmup" if rnd <= plan["warmup_rounds"] else "measure"
        meta = {"set": plan["set"], "session": a.session, "round": rnd, "phase": phase}
        record(a.out, dict(meta, event="round_start", at=now()))
        threads = []
        for lane in plan["lanes"]:
            wls = list(lane)
            th = threading.Thread(target=lane_worker,
                                  args=(plan, targets, wls, providers_for, meta, a.out, a.dry_run))
            th.start()
            threads.append(th)
        for th in threads:
            th.join()
        for wid in plan.get("bursts", []):
            w = plan["workloads"][wid]
            print(f"[{now()}] {phase} r{rnd} burst {wid} x{w['copies']}", flush=True)
            # Optional "burst_groups": provider groups that burst one after another, e.g. when two
            # providers share one account-wide concurrency limit.
            groups = plan.get("burst_groups") or [providers_for(wid)]
            for g in groups:
                ps = [p for p in g if p in providers_for(wid)]
                if ps:
                    run_group(plan, targets, w, ps, meta, a.out, a.dry_run, copies=w["copies"])
        record(a.out, dict(meta, event="round_end", at=now()))


if __name__ == "__main__":
    main()
