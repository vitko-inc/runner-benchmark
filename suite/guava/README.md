# guava

- **Project:** google/guava at `v33.7.2` (`666338cc49d5686c07e3e4d17f0aa1cec25a2be6`), licence Apache-2.0. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/ci.yml`, job "pom.xml on JDK 25 on ubuntu-latest" (Maven install, then verify).
- **Benchmark workflow:** [`.github/workflows/wl-guava.yml`](../../.github/workflows/wl-guava.yml).

## Portability edits (identical for every provider)

- One matrix cell (pom.xml, JDK 25, Linux). No other changes.

## Why it replaced okhttp

okhttp (Gradle) was the first Java/Kotlin workload. In the pilot it failed the flakiness criterion
(one HTTP/2 test failed in 3 of 6 GitHub-hosted runs) and its IPv6-loopback tests fail on plain cloud
VMs, so it was replaced by the alternate before any result set.
