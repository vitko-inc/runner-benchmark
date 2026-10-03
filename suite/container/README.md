# container

- **Project:** mastodon/mastodon at `v4.7.2` (`3987b9fd624010eeeaeb7cad96606b05aa813f6a`), licence AGPL-3.0. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/build-container-image.yml`, job build-image (linux/amd64).
- **Benchmark workflow:** [`.github/workflows/wl-container.yml`](../../.github/workflows/wl-container.yml).

## Portability edits (identical for every provider)

- No registry login or push.
- Built with upstream's PR-build layer cache (`type=gha`). Each run first appends a comment to `config/application.rb`, as a pull request would change the app: dependency layers can come from the cache, and everything after `COPY . /opt/mastodon/` rebuilds. Providers' own Docker layer caches (where documented) are used the same way.
