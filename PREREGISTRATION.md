# Pre-registration: result set v1 (draft)

This file fixes the plan, the analysis and the exclusion rules for result set v1 **before** its
first measured session. When it is final, the commit is tagged `prereg-v1`; anything changed
after that tag is listed in the result set's `deviations.md`.

## Plan

- **Suite:** the 12 workloads in [suite/](suite/), at the pinned commits, with the portability
  edits listed per workload ([plans/v1.json](plans/v1.json)).
- **Providers:** [plans/v1.json](plans/v1.json) and [providers/](providers/). Each provider runs
  in its own repository copy, so no provider's cache serves another.
- **Configurations.** Every provider runs the configuration its customers would use:
  - GitHub-hosted 2 vCPU and 4 vCPU, Blacksmith, Depot, Ubicloud and RunsOn: the provider's
    defaults, with only `runs-on` changed.
  - Self-hosted EC2 (one VM per job) and GCE (always-on pool): stock runner, on-demand prices.
  - **Vitko Runners, two arms, both reported:**
    - `vitko`: only `runs-on` changed.
    - `vitko-opt`: Vitko's recommended configuration: warm starts (the checkpoint step after the
      setup steps, saved from a push to the default branch) and split tests on workloads with a
      splittable test step. Network-dependent tests run in a separate unsplit step of the same
      job, so the job runs the same tests as every other arm.
  - **Providers' documented accelerators**, configured as their docs describe, wherever they apply
    to these workloads (the workflow input `accel`):
    - Blacksmith: Docker layer cache (`useblacksmith/setup-docker-builder` and
      `useblacksmith/build-push-action`) on the container workload; its cache for `actions/cache`
      is automatic.
    - RunsOn: Magic Cache (`extras=s3-cache` in the label and `runs-on/action` before the cache steps).
    - Ubicloud: transparent cache (on by default). Depot: Depot Cache for `actions/cache` (automatic).
    - GitHub-hosted, self-hosted: GitHub's cache service.
  - **Build-output persistence across runs** (for example a sticky disk holding a build directory)
    is not used by any provider: the suite builds the same commit every run, so a persisted build
    directory would replay the previous run instead of measuring a change. The container workload
    instead simulates a pull-request change in each run, so layer caches are measured realistically.
- **Sessions:** 3 sessions on 3 different days within 7 days: weekday US working hours, weekday
  night (UTC), weekend. Each: 2 warm-up rounds (discarded), then 10 measured rounds.
- **Rounds:** every workload is dispatched to every provider within seconds, in random order
  (seeded), in parallel lanes; the burst (20 runs of the black job at once) runs after the lanes.
  Providers that share one account-wide concurrency limit burst one after another.
- **Measured runs** are dispatched from a non-default branch. Warm-start captures happen only from
  pushes to the default branch, before session 1 and after any change to the suite.

## Analysis (fixed)

- Metrics, cost rules and the index as in [METHOD.md](METHOD.md) v1.0.
- **Reference:** GitHub-hosted 2 vCPU.
- **Indices** over all 12 workloads; a provider without a usable cell for every workload gets
  per-workload results only, and the reason is listed.
- **Usable cell:** at least 90% successful runs. Failures are counted, never replaced.
- **CIs:** block bootstrap over sessions, then rounds, 10,000 replicates, percentile 95%.
- **Also published:** pairwise ratios with CIs, leave-one-workload-out, per-session indices, and
  the self-hosted pool at U = 25% / 50% / 75%.

## Exclusions and voids (fixed)

- A run voided by an infrastructure incident **on the harness side** (driver crash, API outage)
  is re-dispatched in a replacement round and listed. Provider-side failures are never voided.
- A workload that fails on every provider in a round because of an upstream change (network test,
  registry outage) is voided for that round for every provider, and listed.

## Conflict of interest

Vitko Inc. maintains this benchmark and sells Vitko Runners.
