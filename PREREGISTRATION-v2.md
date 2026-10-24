# Pre-registration: result set v2

This file fixes the plan, the analysis, the stop rules and the spending cap for result set v2
**before** its first measured session. The commit tagged `prereg-v2` fixes it, including the plan's
random seed. Anything changed after that tag is listed in the result set's `deviations.md`.
[PREREGISTRATION.md](PREREGISTRATION.md) still governs v1 and is unchanged. Everything in it that
this file does not change (suite, metrics, cost rules, CIs, exclusions and voids) applies to v2.

## What v2 adds

v1 left out providers that could not be measured or were not yet set up. v2 measures one of them
and keeps the reference:

- **GitHub-hosted 2 vCPU** (`gh2`), the reference, re-measured in v2.
- **Namespace, 2 vCPU / 8 GB** (`namespace2`), Linux x64, through a runner profile with that shape.
- **Depot** (`depot2`) is in the plan only if its start check passes before the tag (the
  `depot-ubuntu-24.04` label starts a job on the repository's workflow). If it does not, v2
  reports "Not measured in v2" with the reason and the evidence, and no Depot cells are published.

v2 is not a re-run of v1: its numbers are reported as their own result set, and v1 numbers are
not re-indexed against v2's reference.

## Plan

- **Suite:** the same 12 workloads at the same pinned commits and portability edits as v1
  ([plans/v2.json](plans/v2.json) differs from [plans/v1.json](plans/v1.json) only in `set`,
  `seed`, `providers` and `burst_groups`).
- **Configurations.** Each provider runs the configuration a customer would use, in its own
  repository copy so no provider's cache serves another:
  - GitHub-hosted 2 vCPU: the provider's default with only `runs-on` changed.
  - Namespace: the runner profile `namespace-profile-rb-2x8` (Linux x64, 2 vCPU / 8 GB RAM), only
    `runs-on` changed. **No Namespace accelerator is configured:** `actions/cache` is served by
    GitHub's cache service, and Namespace Cache Volumes (`nscloud-cache-action`) are not used. This
    is a limitation published with the results: Namespace documents Cache Volumes as the option with
    local, no-transfer cache hits.
- **Sessions:** 3 sessions on 3 different days within 7 days (weekday US working hours, weekday
  night UTC, weekend). Each: 2 warm-up rounds (discarded), then 10 measured rounds.
- **Rounds and burst:** as v1. Every workload is dispatched to every provider within seconds, in
  seeded random order, in parallel lanes. The burst (20 runs of the black job) runs after the
  lanes, one provider at a time.
- **Measured runs** are dispatched from a non-default branch.

## Prices (fixed)

[prices/2026-10-24.json](prices/2026-10-24.json), list prices read on 2026-10-24:

- GitHub-hosted 2 vCPU: $0.006 per minute, job rounded up to the minute.
- Namespace Linux 2 vCPU / 8 GB: $0.006 per minute at the pay-as-you-go rate (4 unit minutes per
  minute); seconds are billed as whole minutes. The plan-prepaid rate ($0.004 per minute) is not
  used, because it depends on a plan the test does not buy.
- Depot (only if included): $0.006 per minute, per second.

## Analysis (fixed)

As v1: reference GitHub-hosted 2 vCPU; usable cell at least 90% successful runs; failures counted,
never replaced; block bootstrap over sessions then rounds, 10,000 replicates, percentile 95%;
pairwise ratios with CIs; leave-one-workload-out; per-session indices; burst dispatch spread.
With two measured providers the index is the Namespace-to-GitHub-hosted ratio over all 12
workloads, and per-workload results are published for every cell.

## Stop rules and spending cap (fixed)

- **Cap:** total benchmark spending for v2 is capped at $150. Estimated spend is $72 to $98. If a
  running total reaches $120, the remaining sessions are stopped and the owner is told before
  anything further is dispatched.
- **Start rule:** if a provider cannot start jobs in the warm-up rounds of session 1 (a job queued
  with no runner for 15 minutes), that provider is dropped from v2 and reported as "Not measured in
  v2" with the evidence. The other provider's session continues.
- **No substitutions:** a provider is not swapped for another after the tag.

## Exclusions and voids (fixed)

As v1: harness-side incidents are re-dispatched and listed; provider-side failures are never
voided; a workload that fails on every provider in a round because of an upstream change is voided
for that round for every provider and listed.

## Conflict of interest

Vitko Inc. maintains this benchmark and sells Vitko Runners. v2 does not measure Vitko Runners.
