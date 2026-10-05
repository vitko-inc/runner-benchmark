# RunsOn cost collection

RunsOn runs in the customer's own AWS account, so its cost is the all-in AWS cost of its jobs
(METHOD.md, "Cost"). During a session:

1. `monitor.py` records every instance RunsOn starts: type, spot or on-demand, AZ, launch time,
   root volume, public address, and when it stops. Run it for the whole session.
2. The stack's VPC has a flow log to an S3 bucket in the account (format as in
   `../aws/main.tf`), so each instance's internet egress can be told apart from S3 traffic.
3. The stack's cache bucket has S3 request metrics turned on (filter `EntireBucket`).

After the session, `cost_runson.py` prices every job from those records, the bucket listing and
CloudWatch metrics, and writes the stack's fixed monthly cost for `analysis/aggregate.py
--fixed-costs`.
