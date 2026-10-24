# Deviations from the v2 pre-registration

Everything here changed after the `prereg-v2` tag. Dated entries, newest last.

## 2026-10-24: reference arm dropped

Reference arm dropped by decision on 2026-10-24 before session 1 completed. v2 Namespace results are
compared against v1's GitHub-hosted results from October 7-11.

- The GitHub-hosted 2 vCPU arm (`gh2`) dispatched only the 10 workloads of session 1, warm-up round 1
  (the harness was stopped at about 20:19Z). Those runs finished on their own and are kept in the raw
  records; they are not analysed and not part of any published index.
- The remaining rounds run from [plans/v2-namespace.json](../../plans/v2-namespace.json): the same
  seed, suite and rounds as `plans/v2.json`, with `namespace2` as the only provider.
- Because v2 and v1 were measured on different days, the Namespace-to-GitHub comparison is a
  cross-set comparison and is published as such.

## 2026-10-24: session 1, warm-up round 1 incomplete

Round 1 of session 1 dispatched 10 of the 12 workloads (`cli` and the burst were not dispatched),
for Namespace and GitHub-hosted alike, because the harness was stopped when the reference arm was
dropped. The first-run metric for session 1 therefore has no `cli` or burst value. Round 2 started
at 20:20Z while a few round-1 Namespace runs may still have been finishing.

## 2026-10-24: Depot

Not measured in v2: Depot runners were assigned but did not start jobs for our account during the
test window (checks on 2026-10-01 and 2026-10-24).
