# Method (v1.0, draft)

## Workloads

Selection criteria for a workload:
1. A well-known open-source project.
2. The project's own CI job at a pinned release commit, not a job written for the benchmark.
3. Self-contained: no secrets and no paid services, package registries only.
4. At most one flaky failure in ten runs on GitHub-hosted 2 vCPU.
5. Fits 2 vCPU / 8 GB.
6. Upstream doesn't depend on any runner provider's service; if it does, that part is disabled for everyone.
7. A licence that allows running and patching it. Projects are fetched at run time, never vendored.

The suite mixes short and long jobs, CPU-, cache- and network-bound work, a container build, a
long splittable test suite and a burst of concurrent runs.

**Portability edits** are listed per workload in `suite/<id>/README.md` and marked `PORTABILITY`
in the workflow. They are identical for every provider. Toolchains always come from `setup-*`
actions, never from the runner image.

**Source-keyed caches.** The benchmark builds the same commit every run. Caches keyed by source
content (Turbo/Next build caches, Gradle's build cache, Go's test-result cache, Docker layer
caches of the image being built) would replay the previous run's results and turn the job into
a no-op, which no real change would see. They are disabled. Dependency caches (package stores,
toolchains, compiler caches of dependencies) are kept, as in everyday CI.

## Runs

- **Rounds.** A round dispatches each workload to every provider within a few seconds, in
  random order, and waits until all have finished. Workloads run in parallel lanes. The burst
  runs after the lanes, one provider at a time in random order: each provider's 20 copies are
  dispatched at once, in parallel, and the next provider starts when they have all finished.
- **Warm-up.** The first 2 rounds of a session are discarded; they warm caches as everyday CI is warm.
- **Sessions.** An official result set has 3 sessions on 3 different days (weekday working hours
  in the US, weekday night, weekend), with 10 measured rounds each: 30 runs per cell.
- **Isolation.** Each provider runs in its own repository copy, so no provider's cache serves another.
- **Pre-registration.** The suite, plan, analysis code and claim-relevant rules are tagged
  before the first measured session; changes afterwards are listed in the result set's `deviations.md`.

## Metrics

All times come from GitHub's jobs API (whole seconds), the same clock for every provider.

- **Queue:** job `started_at` − `created_at`.
- **Run:** job `completed_at` − `started_at`.
- **Wall:** first job created to last job completed, per workflow run. For the burst, across all 20 runs.
- **Burst dispatch spread:** per provider and round, the time between the first and the last of
  the 20 dispatch requests (harness clock) and between the first and last job created (GitHub's
  clock). Published in `burst_dispatch.csv`, so it can be checked that every provider's burst
  started equally tight.
- **Per cell:** p50 and p95 (linear interpolation), mean and max wall; p50 queue; mean cost; success rate.
- **Hardware** each job saw is recorded by the first step of every job, the same way for every provider: CPU vendor family (for example "AMD EPYC"), clock in GHz, vCPUs, memory and swap. Exact CPU models are not recorded.

## Cost

Per job, at the provider's public list price on the date (`prices/<date>.json`), for the size
used, with the provider's own billing rule, summed over the run's jobs:

- **Rounded up to a whole minute per job** where the provider bills that way.
- **Per second** where the provider bills per second.
- **Self-hosted, one VM per job:** billed instance seconds from launch to termination (60 s
  minimum), including boot, plus the root volume.
- **Self-hosted, always-on pool:** the job's run time ÷ U at the VM's per-second price, with
  U = 50% (results at 25% and 75% are shown alongside). Time is measured; cost at U is modelled.
- **Split tests (Vitko Runners, Track B):** only the parts are billed while a split step runs:
  job run time − the split step's duration + each part's duration.
- Queue time isn't billed by hosted providers. Free minutes, plan fees, discounts, and cache and
  artifact storage are excluded from per-run cost and listed separately.
- If a workload needs the next size up on a provider, it runs and is priced there, and the cell is flagged.
- **Memory and swap.** Managed providers run their own documented images and sizes, unchanged.
  The self-hosted baselines (EC2, GCE) are ours to configure, so they get the same swap as the
  Vitko Runners guest: zram (compressed, in RAM), zstd, min(RAM, 8 GiB), priority 100,
  `vm.swappiness = 100`, `vm.page-cluster = 0`. This is applied identically to every
  self-hosted arm, so all of them, and Vitko, run every workload at 2 vCPU / 8 GiB. The
  `codex-lint` job records the pages swapped out during the job and the swap in use at its end,
  for every provider.
- Not included for self-hosted: people's time, NAT gateways, image upkeep, monitoring.

## Reliability

A run failing for infrastructure reasons counts as a failure and is never silently replaced. A
cell needs at least 90% successful runs to enter the indices.

## Indices

For each workload, a provider's p50 wall and mean cost are divided by the reference provider's
(GitHub-hosted 2 vCPU). The **time index** and **cost index** are the geometric means of those
ratios across the workloads, with equal weight per workload. 95% confidence intervals come from a
block bootstrap (10,000 replicates) that resamples sessions, then rounds within a session, keeping
all runs dispatched together in one round together. Also published: pairwise ratios with CIs,
leave-one-workload-out indices and per-session indices.

## Tracks

- **Track A:** only `runs-on` changes. This is the comparison the indices use.
- **Track B:** each provider's documented options for the same workloads (for example split
  tests, a Docker layer cache). Shown separately, never mixed into Track A.
