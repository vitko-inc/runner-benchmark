# Pre-registration: result set v1

This file fixes the plan, the analysis and the exclusion rules for result set v1 **before** its
first measured session. It is final: the commit tagged `prereg-v1` (2026-10-07) fixes it, including
the plan's random seed. Anything changed after that tag is listed in the result set's
`deviations.md`. The Vitko Runners service, the run repositories' workflows and the self-hosted
images stay as they are at the tag until the last session ends.

## Plan

- **Suite:** the 12 workloads in [suite/](suite/), at the pinned commits, with the portability
  edits listed per workload ([plans/v1.json](plans/v1.json)).
- **Providers:** [plans/v1.json](plans/v1.json) and [providers/](providers/). Each provider runs
  in its own repository copy, so no provider's cache serves another. Depot was excluded from v1:
  its runners never started a job during the test window.
- **Configurations.** Every provider runs the configuration its customers would use:
  - GitHub-hosted 2 vCPU and 4 vCPU, Blacksmith, Ubicloud and RunsOn: the provider's
    defaults, with only `runs-on` changed.
  - Self-hosted EC2 (one VM per job) and GCE (always-on pool): stock runner, on-demand prices, and
    the same swap as the Vitko Runners guest (zram, zstd, min(RAM, 8 GiB); METHOD.md "Memory and
    swap"), applied identically to every self-hosted arm, so every workload runs at 2 vCPU / 8 GiB.
    Managed providers (GitHub, Blacksmith, RunsOn, Ubicloud) run their own documented images and
    sizes, unchanged.
  - **Vitko Runners, two arms, both reported:**
    - `vitko`: only `runs-on` changed.
    - `vitko-opt`: Vitko's recommended configuration: warm starts (the checkpoint step after the
      setup steps, saved from a run on the default branch) and split tests (`vitko-inc/split-tests`)
      on the splittable test steps: the unit tests of vite, vue, flask, pydantic, cli and ts, and
      vite's three Playwright end-to-end steps (serve, bundled dev, build). Tests that need the
      outside network or state shared between test files run in a separate unsplit step of the
      same job, so the job runs the same tests as every other arm.
  - **Providers' documented accelerators**, configured as their docs describe, wherever they apply
    to these workloads (the workflow input `accel`):
    - Blacksmith: Docker layer cache (`useblacksmith/setup-docker-builder` and
      `useblacksmith/build-push-action`) on the container workload; its cache for `actions/cache`
      is automatic.
    - RunsOn: Magic Cache (`extras=s3-cache` in the label and `runs-on/action` before the cache steps).
    - Ubicloud: transparent cache (on by default).
    - GitHub-hosted, self-hosted: GitHub's cache service.
  - **Build-output persistence across runs** (for example a sticky disk holding a build directory)
    is not used by any provider: the suite builds the same commit every run, so a persisted build
    directory would replay the previous run instead of measuring a change. The container workload
    instead simulates a pull-request change in each run, so layer caches are measured realistically.
- **Sessions:** 3 sessions on 3 different days within 7 days: weekday US working hours, weekday
  night (UTC), weekend. Each: 2 warm-up rounds (discarded), then 10 measured rounds.
- **Rounds:** every workload is dispatched to every provider within seconds, in random order
  (seeded), in parallel lanes. The burst (20 runs of the black job) runs after the lanes, one
  provider at a time, in seeded random order: each provider's 20 runs are dispatched at once, in
  parallel, and the next provider starts after every run of the previous one has finished. So no
  two providers share a dispatch window, and providers that share one account-wide concurrency
  limit or one host never burst at the same moment. The spread between the first and last of
  each provider's 20 dispatches is recorded for every round and published with the results.
- **Measured runs** are dispatched from a non-default branch. Warm-start captures happen only from
  runs on the default branch (harness/capture.py), before session 1 and after any change to the
  suite.

## Analysis (fixed)

- Metrics, cost rules and the index as in [METHOD.md](METHOD.md) v1.0. Prices:
  [prices/2026-10-05.json](prices/2026-10-05.json).
- **Self-hosted options are priced all-in** (METHOD.md, "Cost"): RunsOn, EC2 and GCE pay
  everything their jobs use in the customer's cloud account, measured per job (instances, disks,
  public IPv4, accelerator storage and requests, NAT, internet egress), plus fixed monthly costs
  (control plane, launcher or controller hosts, licences) spread over 100,000 jobs per month, with
  10,000 and 1,000 jobs per month as sensitivity. Managed providers are priced at list price.
  This rule was adopted before the tag, after the pilot (below) showed the earlier rule left out
  public IPv4, accelerator storage, egress and fixed costs.
- **Pilot:** one round of the v1 plan on 2026-10-05, before the tag, to check the harness, the
  collectors and the cost rules. It is disclosed with the results and is not part of the result
  set. Changes it led to before the tag: all-in pricing for self-hosted options; RunsOn's
  `codex-lint` on its next memory size (2 vCPU / 16 GiB), applying METHOD.md's next-size rule after
  it ran out of memory at 8 GiB; harness and analysis fixes (runner-benchmark #11, #12). One
  Vitko Runners service change also landed before the tag: when a host is full, a pool with queued
  jobs now takes the capacity that another pool's idle standby runners were holding. In the pilot,
  the second Vitko arm's burst had waited for the first arm's idle standbys to expire.
- **Reference:** GitHub-hosted 2 vCPU.
- **Indices** over all 12 workloads; a provider without a usable cell for every workload gets
  per-workload results only, and the reason is listed.
- **Usable cell:** at least 90% successful runs. Failures are counted, never replaced.
- **CIs:** block bootstrap over sessions, then rounds, 10,000 replicates, percentile 95%.
- **Also published:** pairwise ratios with CIs, leave-one-workload-out, per-session indices, and
  the self-hosted pool at U = 25% / 50% / 75%.
- **Burst dispatch spread** per provider and round (`burst_dispatch.csv`, METHOD.md).
- **Reporting rules.** Results of `vitko-opt` are labelled as using Vitko Runners' own features
  (warm starts and split tests). A comparison between a 2 vCPU and a 4 vCPU configuration is
  reported as a difference in machine size, not in speed per vCPU.

## Exclusions and voids (fixed)

- A run voided by an infrastructure incident **on the harness side** (driver crash, API outage)
  is re-dispatched in a replacement round and listed. Provider-side failures are never voided.
- A workload that fails on every provider in a round because of an upstream change (network test,
  registry outage) is voided for that round for every provider, and listed.

## Conflict of interest

Vitko Inc. maintains this benchmark and sells Vitko Runners.
