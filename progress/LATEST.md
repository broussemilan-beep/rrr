# LATEST — where to actually read this project's state

generated_utc: 2026-09-03T17:45:51Z
content_commit: 7eaa70738dcc4982e16ee9422e2c7101bfeb5117

## Read these (immutable — always fresh on first read)

- progress log     : https://raw.githubusercontent.com/broussemilan-beep/rrr/7eaa70738dcc4982e16ee9422e2c7101bfeb5117/progress/PROGRESS_LOG.md
- screenshot index : https://raw.githubusercontent.com/broussemilan-beep/rrr/7eaa70738dcc4982e16ee9422e2c7101bfeb5117/progress/screenshots/INDEX.md
- screenshot base  : https://raw.githubusercontent.com/broussemilan-beep/rrr/7eaa70738dcc4982e16ee9422e2c7101bfeb5117/progress/screenshots/<filename>

## Why these URLs and not `.../main/...`

A `main` URL passes through two caches, both measured on 2026-08-26:
`raw.githubusercontent.com` serves branch refs with `cache-control: max-age=300`
and GitHub does not purge on push (content was still stale 242 s after a push);
and a fetching agent such as Claude's WebFetch caches ~15 min per URL while
ignoring that `max-age` entirely. Cache-busting query strings do not work — the
query string is not part of the CDN cache key.

The URLs above are pinned to an immutable commit SHA, so they are a URL no
client has fetched before, and neither cache can hold a previous version of them.

## Staleness check

If `generated_utc` above is far behind the current time, THIS pointer was served
from a cache. Ask the operator to re-run `scripts/sync_progress_log.sh` and paste
the immutable URL it prints.
