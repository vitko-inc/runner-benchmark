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

## 2026-10-08: harness refreshes an expired API token at once (harness)

In session 1 the harness's short-lived GitHub App token sometimes expired a few minutes before its
scheduled refresh; status polls then failed with HTTP 401 for about 5–7 minutes roughly every
100 minutes (no dispatch failed). Polls are retried, so no run was lost; rounds only took a few
minutes longer to notice finished runs. From session 2 the token is refreshed every 10 minutes and
immediately after any 401. Nothing that is measured changes: times come from GitHub's job records.

## 2026-10-08: a Vitko Runners control-plane rollout between sessions 1 and 2 (rolled back)

Between session 1 (ended 2026-10-08 04:43Z) and session 2 (starts 2026-10-09 00:00Z), a Vitko
Runners production deploy ran outside the benchmark's change freeze. A new control-plane and broker
image served a 10% slice from 09:55Z and all traffic from 10:05Z, and was rolled back automatically
at 10:25Z (a latency check failed). Earlier the same morning (05:44–06:48Z) three attempts of the same
rollout rolled back while still at a 10% slice. No benchmark job ran during any of these windows,
the benchmark host was not changed, and the revisions serving every Vitko Runners job in sessions 2
and 3 are the same as in session 1 (checked 2026-10-08 10:38Z). Listed for completeness; no
measured run is affected.
