#!/usr/bin/env python3
"""Save warm-start checkpoints for a provider that offers them, the way a customer's setup is
saved: every workload runs once, from the repository's default branch, with the checkpoint step
on. Measured runs are later dispatched from another branch.

Usage:
  GITHUB_TOKEN=... python3 harness/capture.py --plan plans/<name>.json --targets <targets.json> \
      --provider <id> --out results/<set>/capture.jsonl

The provider's target entry names the run repository and the labels:
  "capture": {"ref": "main", "labels": {"plain": "<label>", "split": "<label>"}}
"plain" captures every workload with split off; "split" captures the splittable workloads with
split on. Like every benchmark workflow, these runs are started by workflow_dispatch only.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import run  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--provider", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    plan, targets = run.load(a.plan), run.load(a.targets)
    t = targets[a.provider]
    cap = t["capture"]
    sent = []
    for variant, label in cap["labels"].items():
        split = variant == "split"
        for wid, w in plan["workloads"].items():
            if wid in plan.get("bursts", []) or (split and not w.get("splittable")):
                continue
            target = {"repo": t["repo"], "runs_on": label, "ref": cap.get("ref", "main"),
                      "inputs": {"checkpoint": "true"}}
            tag = f"capture-{wid}-{variant}"
            d = run.dispatch(target, w, tag, split, a.dry_run)
            if not a.dry_run and d["run_id"] is None:
                d["run_id"] = run.find_run(t["repo"], w["workflow"], tag, d["since"])
            rec = {"event": "capture", "provider": a.provider, "workload": wid, "variant": variant,
                   "tag": tag, "repo": t["repo"], "run_id": d["run_id"], "dispatched_at": d["dispatched_at"]}
            run.record(a.out, rec)
            sent.append(rec)
            print(f"[{run.now()}] capture {wid} {variant} -> {d['run_id']}", flush=True)
    if a.dry_run:
        return
    left = run.wait_all(sent, plan.get("run_timeout_s", 7200))
    bad = []
    for r in sent:
        res = run.gh.get(f"/repos/{r['repo']}/actions/runs/{r['run_id']}")
        print(f"{r['workload']:12} {r['variant']:6} {res.get('conclusion')}")
        if res.get("conclusion") != "success":
            bad.append(r["tag"])
    if left or bad:
        raise SystemExit(f"capture incomplete: timed out {sorted(left)}, failed {bad}")


if __name__ == "__main__":
    main()
