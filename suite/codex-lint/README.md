# codex-lint

- **Project:** openai/codex at `rust-v0.159.3` (`01fc69f4026735edfdf6789820549727a4867b11`), licence Apache-2.0. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/rust-ci-full.yml`, job lint_build (ubuntu-24.04, x86_64-unknown-linux-gnu, dev).
- **Benchmark workflow:** [`.github/workflows/wl-codex-lint.yml`](../../.github/workflows/wl-codex-lint.yml).

## Portability edits (identical for every provider)

- Upstream runs this on its own larger runner group; here it runs on the provider under test.
- Two extra apt packages (libglib2.0-dev, libdbus-1-dev) that upstream's runner image has.
- `codex-voice-host` is excluded (needs GStreamer 1.28+, absent from stock Ubuntu 24.04).
- No `-D warnings`, so the job ends green; the compile work is the same.
- Needs more than 8 GB of memory without swap (GitHub's runner has 4 GB of swap). Providers without swap run it at their next memory size, priced there.
