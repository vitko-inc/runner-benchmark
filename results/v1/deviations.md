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

## 2026-10-08: Vitko Runners control-plane update between sessions 1 and 2

Approved before it ran, as one attempt inside the gap between sessions. The Vitko Runners
control plane and broker moved to a newer image (observability changes only, no change to how jobs
are admitted or run on the benchmark host): a 10% slice from 10:47Z, all traffic from 11:00Z,
settled 11:30Z. The benchmark host's software, image and configuration did not change. Sessions 2
and 3 therefore run on a newer control-plane image than session 1; per-session results are
published, so any effect would show there. One smoke job per Vitko arm afterwards (11:33Z) ran
normally, including a warm start from the saved setup; those runs were deleted (they are not part of
the result set).

## 2026-10-09: GitHub runner-registration stalls during session 2; Vitko arms slowed (counted, not replaced)

Session 2 started at 00:00Z as planned, on the same harness commit as the earlier deviations entries.
GitHub's runner-listing API stalled twice with no incident published on its status page: about
23:25–23:31Z on 10-08 (before the session) and from 05:47Z to about 05:54Z on 10-09. During the second
stall, runner registrations on the Vitko Runners benchmark host took 53–58 s instead of about 3 s. The
host's client gives up after 30 s and retried under the same runner name; some retries were refused
(a per-host registration cap, 429) or collided with the earlier registration (409 name already
exists, 11 cases on 7 runners). The plain Vitko arm's warm pool then lost its standby runners and
rebuilt its parent image in about 2 minutes (05:57:50–05:59:48Z), an ordinary rebuild with no change
on our side (no push to the run repository; the cause of the rebuild is unconfirmed). The cap also
refused registrations throughout the session whenever bursts of 20 jobs arrived, as it does for any
user who exceeds it.

Effect on measured runs: no Vitko run was lost. Burst round 5 of the plain Vitko arm (dispatched
05:52Z) waited longer for a runner (median 128 s, maximum 528 s, against a typical 15–20 s), and burst
round 11 also had a long wait (median 104 s, maximum 431 s). The cause of burst round 11's wait
has not been established. Both are counted as measured, not voided and not replaced: the stall was
GitHub's, but the slowdown came from how the Vitko host handled it, and the pre-registration voids
only harness-side failures. A fix for the retry behaviour is planned after session 3 and is
not part of the measured configuration. The replacement round for session 2 found no cell without a
dispatched run (0 cells).

## 2026-10-10: session 3 starts late

Session 3 was planned for Saturday 2026-10-10 13:00Z. The benchmark operator's automation stopped
between sessions, so the session's preparation did not run on time; nothing about the benchmark
setup changed in the meantime. It starts at about 19:30Z on the same day, still within the
pre-registration's weekend session and inside seven days of session 2. Pre-checks were re-run
immediately beforehand: no run-repository changes, no non-benchmark runs, same Vitko Runners
revisions, same benchmark host configuration.

## 2026-10-10: the benchmark host's build predates later cleanup of restored saved setups (affects `vitko-opt`)

The Vitko Runners benchmark host runs the software build of 2026-10-05, frozen for all three
sessions. Production builds from 2026-10-06 onward do more cleanup when a saved setup is stored and
restored: package sources and keys, container state, created users, service units and certificate
stores no longer carry over from one job to the next. On the benchmark host's build those paths still
carry over. The saved-setup (`vitko-opt`) results were therefore measured without that cleanup, so
the gain from saved setups may be somewhat larger than current production behaviour would show.
Tool caches are not reset by either build.

From the run logs of sessions 1 and 2 (step names and durations only, no host access), the
saved-setup gain comes mostly from split tests (for example about 130–150 s of the 200–270 s
difference on `cli`, `ts` and `vite`), not from skipped setup. Setup steps that ran faster on
`vitko-opt` saved roughly 3–15 s per run. Only three workloads run steps that touch the affected
paths: `codex-lint` (system package install, about 3 s), `container` (container builder setup, about
2 s) and `vite` (browser install with system packages, about 7 s). The remaining setup savings are
language toolchains, package caches and dependency installs. The pre-registered results stand as
measured. A short supplementary measurement on a build with the cleanup is planned for after session
3 and will be reported separately, clearly marked as not part of the pre-registered results.
