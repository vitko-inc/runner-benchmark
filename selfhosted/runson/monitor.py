#!/usr/bin/env python3
"""Record the EC2 instances RunsOn starts in us-east-2 (every 5 s) so each job's
cost can be computed afterwards: type, lifecycle (spot/on-demand), AZ, launch time, root volume
size, and the first time the instance was seen shutting down or terminated.

Writes JSON lines to $RB_RUNSON_INSTANCES. Only instances tagged runs-on-stack-name=$RB_RUNSON_STACK are recorded.
"""
import json
import os
import subprocess
import time
import datetime as dt

OUT = os.environ.get("RB_RUNSON_INSTANCES", "runson_instances.jsonl")
REGION = os.environ.get("AWS_REGION", "us-east-2")
STACK = os.environ["RB_RUNSON_STACK"]
seen = {}


def aws(*a):
    r = subprocess.run(["aws", "--region", REGION, *a, "--output", "json"], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


while True:
    d = aws("ec2", "describe-instances")
    for res in (d or {}).get("Reservations", []):
        for i in res["Instances"]:
            tags = {t["Key"]: t["Value"] for t in i.get("Tags", [])}
            if tags.get("runs-on-stack-name") != STACK:
                continue
            iid = i["InstanceId"]
            st = i["State"]["Name"]
            rec = seen.get(iid)
            if rec is None:
                vols = [b["Ebs"]["VolumeId"] for b in i.get("BlockDeviceMappings", []) if "Ebs" in b]
                size = None
                if vols:
                    v = aws("ec2", "describe-volumes", "--volume-ids", *vols)
                    size = sum(x["Size"] for x in (v or {}).get("Volumes", [])) if v else None
                rec = {"instance_id": iid, "type": i["InstanceType"], "lifecycle": i.get("InstanceLifecycle", "on-demand"),
                       "az": i["Placement"]["AvailabilityZone"], "launch": i["LaunchTime"], "root_gb": size,
                       "tags": {k: v for k, v in tags.items() if k.lower().startswith(("runs-on", "name"))},
                       "public_ip": bool(i.get("PublicIpAddress")),
                       "first_seen": now(), "end": None, "reason": None}
                seen[iid] = rec
            if rec["root_gb"] is None:  # volumes attach a few seconds after launch
                vols = [b["Ebs"]["VolumeId"] for b in i.get("BlockDeviceMappings", []) if "Ebs" in b]
                if vols:
                    v = aws("ec2", "describe-volumes", "--volume-ids", *vols)
                    if v:
                        rec["root_gb"] = sum(x["Size"] for x in v.get("Volumes", []))
            if st in ("shutting-down", "terminated") and not rec["end"]:
                rec["end"] = now()
                rec["reason"] = i.get("StateTransitionReason")
                with open(OUT, "a") as f:
                    f.write(json.dumps(rec) + "\n")
            elif rec.get("reason") is None and i.get("StateTransitionReason"):
                rec["reason_live"] = i.get("StateTransitionReason")
    time.sleep(5)
