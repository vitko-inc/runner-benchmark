# burst

- **Project:** psf/black at `26.5.1` (`87928e6d6761a4a6d22250e1fee5601b3998086e`), licence MIT. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/test.yml`, job test (3.13, ubuntu-latest).
- **Benchmark workflow:** [`.github/workflows/wl-black.yml`](../../.github/workflows/wl-black.yml).

## Portability edits (identical for every provider)

- One matrix cell (Python 3.13, Linux); Coveralls upload runs only in upstream's repository.
- Dispatched 20 times at once: the measured time is from the first job created to the last job finished.
