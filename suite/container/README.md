# container

- **Project:** mastodon/mastodon at `v4.7.2` (`3987b9fd624010eeeaeb7cad96606b05aa813f6a`), licence AGPL-3.0. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/build-container-image.yml`, job build-image (linux/amd64).
- **Benchmark workflow:** [`.github/workflows/wl-container.yml`](../../.github/workflows/wl-container.yml).

## Portability edits (identical for every provider)

- No registry login or push.
- Run with the reusable workflow's `cache: false`: the same commit every run would otherwise hit every layer.
