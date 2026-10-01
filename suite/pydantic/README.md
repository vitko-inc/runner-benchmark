# pydantic

- **Project:** pydantic/pydantic at `v2.13.5` (`001dea020e0809844e5b17666432c9135a976f46`), licence MIT. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/ci.yml`, job Test ubuntu-latest / 3.13.
- **Benchmark workflow:** [`.github/workflows/wl-pydantic.yml`](../../.github/workflows/wl-pydantic.yml).

## Portability edits (identical for every provider)

- One matrix cell (Linux, Python 3.13).
- The coverage artifact upload is omitted (it feeds a separate combine job).
- `ulimit -s 16384` before the tests: GitHub's runner image sets a 16 MiB stack limit, stock Ubuntu 8 MiB, where a recursion test overflows.
