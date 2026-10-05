#!/usr/bin/env python3
"""Turn raw job records into per-run, per-cell and suite-level results.

Usage:
  python3 analysis/aggregate.py --raw results/<set>/raw/jobs.jsonl.gz --providers providers/ \
      --prices prices/<date>.json --out results/<set>/ [--reference gh2] [--index-providers a,b,...]
      [--extra-cost results/<set>/raw/selfhosted-cost.csv] [--split-copies results/<set>/raw/split-copies.jsonl]
      [--boot 10000]

Definitions (METHOD.md):
  queue  = job started_at - created_at
  run    = job completed_at - started_at
  wall   = last job completed - first job created, per workflow run; for a burst, across all
           runs of the burst (makespan)
  burst dispatch spread = first to last dispatch request (harness clock, burst_dispatch.csv),
           and first to last job created (GitHub's clock)
  cost   = per job, list price x billed time under the provider's billing rule, summed per run
  cell   = (workload, provider): p50/p95 wall and queue, mean cost, success rate
  index  = geometric mean over workloads of (cell p50 wall / reference p50 wall), and the same for
           mean cost; 95% CIs by a block bootstrap over (session, round) blocks
"""
import argparse
import csv
import datetime as dt
import gzip
import json
import math
import os
import random
from collections import defaultdict


def ts(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def geomean(xs):
    return math.exp(sum(math.log(x) for x in xs) / len(xs))


def load_providers(path):
    out = {}
    for fn in sorted(os.listdir(path)):
        if fn.endswith(".json"):
            p = json.load(open(os.path.join(path, fn)))
            out[p["id"]] = p
    return out


def job_cost(provider, prices, workload, job, extra, copies):
    """Return (usd, billed_seconds) for one job, or (None, None) if it can't be priced."""
    ref = provider.get("price_ref_by_workload", {}).get(workload, provider["price_ref"])
    pr = prices["providers"].get(ref)
    if pr is None:
        return None, None
    run_s = ts(job["completed_at"]) - ts(job["started_at"])
    rule = pr["billing"]
    if rule == "external":  # priced per job by a collector (EC2 instance seconds, RunsOn, ...)
        e = extra.get(str(job["id"]))
        if e is None:
            return None, None
        return e["usd"], e["billed_seconds"]
    mult = provider.get("price_multiplier", {}).get(workload, 1)
    rate = pr["usd_per_min"] * mult
    if rule == "job-rounded-up-to-minute":
        billed = math.ceil(max(run_s, 1) / 60) * 60
    elif rule == "per-second":
        billed = run_s
    elif rule == "per-second-min-60":
        billed = max(run_s, 60)
    elif rule == "pool-occupancy":
        # Always-on pool: the job's share of the pool's cost at the stated utilization U.
        billed = run_s / pr["utilization"]
    elif rule == "external":
        e = extra.get(str(job["id"]))
        if e is None:
            return None, None
        return e["usd"], e["billed_seconds"]
    else:
        raise ValueError(rule)
    if provider.get("split_billing") and copies is not None:
        split = [s for s in job["steps"] if "(split)" in (s.get("name") or "") and s.get("completed_at")]
        cps = copies.get(job.get("runner_name") or "")
        if split and cps:
            # Every split step of the job (vite has four): the job is billed for its own time
            # outside those steps plus the run time of every copy that ran them.
            st = sum(ts(x["completed_at"]) - ts(x["started_at"]) for x in split)
            billed = run_s - st + sum(cps)
    return billed / 60 * rate, billed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--providers", required=True)
    ap.add_argument("--prices", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reference", default="gh2")
    ap.add_argument("--index-providers", default="")
    ap.add_argument("--extra-cost")
    ap.add_argument("--split-copies")
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--phase", default="measure")
    ap.add_argument("--index-workloads", choices=["all", "common"], default="all")
    ap.add_argument("--min-success", type=float, default=0.9)
    a = ap.parse_args()

    providers = load_providers(a.providers)
    prices = json.load(open(a.prices))
    extra = {}
    if a.extra_cost and os.path.exists(a.extra_cost):
        for r in csv.DictReader(open(a.extra_cost)):
            extra[r["job_id"]] = {"usd": float(r["usd"]), "billed_seconds": float(r["billed_seconds"])}
    copies = None
    if a.split_copies and os.path.exists(a.split_copies):
        copies = defaultdict(list)
        for line in open(a.split_copies):
            c = json.loads(line)
            copies[c["parent_runner"]].append((c["finished_ms"] - c["started_ms"]) / 1000)

    rows = [json.loads(l) for l in gzip.open(a.raw, "rt") if l.strip()]
    rows = [r for r in rows if r.get("phase") == a.phase]

    # ---- per run (bursts grouped into one unit per provider and round)
    units = defaultdict(list)
    for r in rows:
        key = (r["workload"], r["provider"], r["session"], r["round"])
        if r.get("kind") == "burst":
            units[key].append(r)
        else:
            units[key + (r["copy"],)].append(r)

    run_rows = []
    for key, rs in sorted(units.items(), key=lambda kv: str(kv[0])):
        wl, prov = key[0], key[1]
        p = providers.get(prov)
        jobs = [j for r in rs for j in r["jobs"]]
        ok = all(r["run"]["conclusion"] == "success" for r in rs) and jobs and all(
            j.get("started_at") and j.get("completed_at") for j in jobs)
        row = {"workload": wl, "provider": prov, "session": key[2], "round": key[3], "runs": len(rs),
               "jobs": len(jobs), "ok": bool(ok), "wall_s": None, "queue_max_s": None, "queue_p50_s": None,
               "cost_usd": None, "billed_s": None,
               "run_ids": " ".join(str(r["run_id"]) for r in rs)}
        if ok:
            first = min(ts(j["created_at"]) for j in jobs)
            last = max(ts(j["completed_at"]) for j in jobs)
            qs = [ts(j["started_at"]) - ts(j["created_at"]) for j in jobs]
            row.update(wall_s=last - first, queue_max_s=max(qs), queue_p50_s=pct(qs, 0.5))
            if p:
                cs = [job_cost(p, prices, wl, j, extra, copies) for j in jobs]
                if all(c[0] is not None for c in cs):
                    row["cost_usd"] = sum(c[0] for c in cs)
                    row["billed_s"] = sum(c[1] for c in cs)
        run_rows.append(row)

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "runs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(run_rows[0].keys()))
        w.writeheader()
        w.writerows(run_rows)

    # ---- burst dispatch spread, per provider and round (METHOD.md: burst dispatch spread)
    spread_rows = []
    for key, rs in sorted(units.items(), key=lambda kv: str(kv[0])):
        if not rs or rs[0].get("kind") != "burst":
            continue
        ms = [r["dispatched_at_ms"] for r in rs if r.get("dispatched_at_ms")]
        created = [ts(j["created_at"]) for r in rs for j in r["jobs"] if j.get("created_at")]
        spread_rows.append({
            "workload": key[0], "provider": key[1], "session": key[2], "round": key[3], "runs": len(rs),
            "dispatch_spread_s": round((max(ms) - min(ms)) / 1000, 3) if len(ms) == len(rs) else None,
            "created_spread_s": (max(created) - min(created)) if created else None})
    if spread_rows:
        with open(os.path.join(a.out, "burst_dispatch.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(spread_rows[0].keys()))
            w.writeheader()
            w.writerows(spread_rows)

    # ---- per cell
    cells = defaultdict(list)
    for r in run_rows:
        cells[(r["workload"], r["provider"])].append(r)

    def cell_stats(rs):
        okr = [r for r in rs if r["ok"]]
        walls = [r["wall_s"] for r in okr]
        costs = [r["cost_usd"] for r in okr if r["cost_usd"] is not None]
        qs = [r["queue_p50_s"] for r in okr]
        return {"n": len(rs), "ok": len(okr), "success_rate": len(okr) / len(rs) if rs else None,
                "p50_wall_s": pct(walls, 0.5), "p95_wall_s": pct(walls, 0.95),
                "mean_wall_s": sum(walls) / len(walls) if walls else None, "max_wall_s": max(walls) if walls else None,
                "p50_queue_s": pct(qs, 0.5), "p95_queue_s": pct([r["queue_max_s"] for r in okr], 0.95),
                "mean_cost_usd": sum(costs) / len(costs) if costs else None, "p50_cost_usd": pct(costs, 0.5)}

    summary = []
    for (wl, prov), rs in sorted(cells.items()):
        summary.append(dict(workload=wl, provider=prov, **cell_stats(rs)))
    with open(os.path.join(a.out, "summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    # ---- indices
    workloads = sorted({wl for wl, _ in cells})
    idx_provs = [x for x in a.index_providers.split(",") if x] or sorted({p for _, p in cells})
    ref = a.reference

    def usable(wl, prov):
        if (wl, prov) not in cells:
            return False
        st = cell_stats(cells[(wl, prov)])
        return st["ok"] > 0 and st["success_rate"] >= a.min_success and st["mean_cost_usd"] is not None

    excluded = {}
    if a.index_workloads == "all":
        idx_provs = [p for p in idx_provs if all(usable(wl, p) for wl in workloads)]
    else:
        # "common": the workloads every index provider (and the reference) completed; the result
        # lists the excluded workloads and why, so a partial index is never mistaken for a full one.
        for wl in workloads:
            missing = [p for p in set(idx_provs) | {ref} if not usable(wl, p)]
            if missing:
                excluded[wl] = sorted(missing)
        workloads = [wl for wl in workloads if wl not in excluded]
    if ref not in idx_provs or not workloads:
        idx_provs = []

    blocks = sorted({(r["session"], r["round"]) for r in run_rows})
    by_block = defaultdict(list)
    for r in run_rows:
        if r["ok"]:
            by_block[(r["session"], r["round"])].append(r)

    def indices(block_list, wls):
        agg = defaultdict(lambda: {"w": [], "c": []})
        for b in block_list:
            for r in by_block[b]:
                agg[(r["workload"], r["provider"])]["w"].append(r["wall_s"])
                if r["cost_usd"] is not None:
                    agg[(r["workload"], r["provider"])]["c"].append(r["cost_usd"])
        out = {}
        for p in idx_provs:
            tr, cr = [], []
            for wl in wls:
                a1, a0 = agg.get((wl, p)), agg.get((wl, ref))
                if not a1 or not a0 or not a1["w"] or not a0["w"] or not a1["c"] or not a0["c"]:
                    return None
                tr.append(pct(a1["w"], 0.5) / pct(a0["w"], 0.5))
                cr.append((sum(a1["c"]) / len(a1["c"])) / (sum(a0["c"]) / len(a0["c"])))
            out[p] = (geomean(tr), geomean(cr))
        return out

    result = {"schema": "runner-benchmark/v2", "reference": ref, "workloads": workloads,
              "excluded_from_index": excluded,
              "index_providers": idx_provs, "blocks": len(blocks), "cells": summary}
    if idx_provs:
        point = indices(blocks, workloads)
        sessions = sorted({b[0] for b in blocks})
        rng = random.Random(20261001)
        reps = []
        for _ in range(a.boot):
            bl = []
            for s in (rng.choice(sessions) for _ in sessions):
                rs_ = [b for b in blocks if b[0] == s]
                bl.extend(rng.choice(rs_) for _ in rs_)
            v = indices(bl, workloads)
            if v:
                reps.append(v)

        def ci(vals):
            return [pct(vals, 0.025), pct(vals, 0.975)]

        result["indices"] = {p: {"time": point[p][0], "cost": point[p][1],
                                 "time_ci95": ci([v[p][0] for v in reps]),
                                 "cost_ci95": ci([v[p][1] for v in reps])} for p in idx_provs}
        pair = {}
        for p in idx_provs:
            for q in idx_provs:
                if p != q:
                    pair[f"{p}/{q}"] = {"time": point[p][0] / point[q][0], "cost": point[p][1] / point[q][1],
                                        "time_ci95": ci([v[p][0] / v[q][0] for v in reps]),
                                        "cost_ci95": ci([v[p][1] / v[q][1] for v in reps])}
        result["pairwise"] = pair
        loo = {}
        for wl in workloads:
            v = indices(blocks, [w for w in workloads if w != wl])
            loo[wl] = {p: {"time": v[p][0], "cost": v[p][1]} for p in idx_provs} if v else None
        result["leave_one_out"] = loo
        result["per_session"] = {s: indices([b for b in blocks if b[0] == s], workloads)
                                 for s in sorted({b[0] for b in blocks})}
    with open(os.path.join(a.out, "results.json"), "w") as f:
        json.dump(result, f, indent=1, sort_keys=True)
    print(json.dumps(result.get("indices", {}), indent=1))


if __name__ == "__main__":
    main()
