# Result set v1: deviations from the pre-registration

Changes after the `prereg-v1` tag, dated, with the reason. Losses (failed or replaced runs) are listed
in `losses.md`.

## 2026-10-07: replacement rounds for cells lost to GitHub API incidents (harness)

During session 1, GitHub's API returned HTTP 500 to workflow dispatches in two windows that match
GitHub-reported incidents (githubstatus.com, 2026-10-07 15:14Z and 17:17Z, "Incident with Git
Operations, ... Actions"). The harness at the tag retried a failed dispatch once, then dropped the
whole workload for that round. As a result, measured round 3 lost 8 workloads for every provider,
and measured round 4 lost the burst for 4 providers; no run was created for any lost cell.

The pre-registration already says that a run voided by a harness-side incident, such as an API
outage, "is re-dispatched in a replacement round and listed". The harness gained the mechanism to
do that, without changing what is measured:

- a failed dispatch is retried with back-off for up to 15 minutes, checking by the run's tag before
  every retry so a run is never dispatched twice;
- a failure loses only that provider's cell, not the whole workload;
- `--replace` re-dispatches, after the session's last round, every measured cell that never ran,
  under its original round number; a burst cut short is run again whole, and only the replacement
  counts.

Applied from session 1's replacement round onward (sessions 2 and 3 run with it from the start).
