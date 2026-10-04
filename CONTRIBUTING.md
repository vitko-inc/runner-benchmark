# Contributing

## Corrections

Open an issue with the result set, the cell and what is wrong (configuration, price, billing
rule, a portability edit). Maintainers answer within 5 business days. An accepted correction to a
published result set is recorded in that set's `errata.md` with the recomputed files; raw job
records never change.

## Submitting runs

Open a pull request adding `submissions/<date>-<provider>/` with:
- the `collect.py` output from runs in a public repository (so the run ids can be checked on GitHub);
- the provider definition (`providers/<id>.json`) and the price source;
- the plan you used.

CI validates the files and recomputes the summaries from the raw records. Submitted runs are
shown as "submitted, not reproduced" until the next official round reproduces them, and are never
mixed into official indices.

## Adding a provider

Add `providers/<id>.json` with the `runs-on` label, size, public price URL and billing rule, the
plan a new customer would use, setup steps a reader can follow, and a link showing that the
provider's terms allow publishing benchmark results. Include a submitted run as above. The
provider joins official rounds from the next one.

## Providers' right of reply

After a result set is published, any measured provider can report an error in its results,
configuration or price in an issue on this repository or by email to benchmark@vitko.inc. We
review every report and publish corrections in the result set, each listed with its date in the
result set's changelog.

## Wording

State facts and method: provider names and labels, numbers with units and dates. No marketing
language.
