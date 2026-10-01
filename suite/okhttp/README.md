# okhttp

- **Project:** square/okhttp (served as lysine-dev/okhttp) at `parent-5.5.0` (`a94bdf152084d11acecd44dcd09ffef203f4f0aa`), licence Apache-2.0. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/build.yml`, job jvm (21).
- **Benchmark workflow:** [`.github/workflows/wl-okhttp.yml`](../../.github/workflows/wl-okhttp.yml).

## Portability edits (identical for every provider)

- One JDK (21).
- `--no-build-cache`: with the same commit every run, Gradle's build cache would restore test results instead of running tests. Dependency caching (setup-gradle) is kept.
- Report-publishing steps run only in upstream's repository and are omitted.
