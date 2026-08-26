# rrr — research context

Roblox R6 combat-game project; external research is under way on three open problems, detailed in [`research-context/OPEN_PROBLEMS.md`](research-context/OPEN_PROBLEMS.md).

## If you are an AI assistant asked to read this project's state

**Start at [`progress/LATEST.md`](progress/LATEST.md)**
(raw: <https://raw.githubusercontent.com/broussemilan-beep/rrr/main/progress/LATEST.md>)

It is a small pointer file carrying the current commit SHA, the UTC time it was
written, and **immutable commit-pinned URLs** for the progress log and the
screenshots. Fetch the pointer, then fetch the pinned URL it gives you.

**Do not read `.../main/progress/PROGRESS_LOG.md` and assume it is current.**
Two caches sit in front of a branch-ref URL, both measured on 2026-08-26:

| layer | behaviour | measured |
| --- | --- | --- |
| `raw.githubusercontent.com` (Fastly) | `cache-control: max-age=300` on branch refs, **not purged on push** | content still stale 242 s after the push; edge flipped at ~275 s |
| the fetching agent's own cache (e.g. Claude `WebFetch`) | ~15 min per URL, **ignores the response `max-age`** | at 16:12:24Z `curl` returned V2 while `WebFetch` returned V1 for the identical URL |

Cache-busting query strings do **not** help — the query string is not part of the
CDN cache key, the same cached object is returned. A `Cache-Control: no-cache`
request header is ignored too. Only a **different URL** defeats a per-URL client
cache, which is why every publish mints a commit-pinned one.

**Staleness self-check:** if `generated_utc` in `progress/LATEST.md` is far behind
the current time, you were served a cached copy of the pointer itself. Say so
rather than reporting its contents as current, and ask the operator to re-run the
sync and paste the fresh immutable URL.

## Contents

- [`progress/LATEST.md`](progress/LATEST.md) — pointer to the current immutable URLs. **Read this first.**
- [`progress/PROGRESS_LOG.md`](progress/PROGRESS_LOG.md) — newest entry first, one per significant work turn, with the measurements. Opens with a self-contained one-page summary, so it can be read cold.
- [`progress/screenshots/`](progress/screenshots/) — renders, newest first, indexed in [`INDEX.md`](progress/screenshots/INDEX.md). Filenames are dated `YYYY-MM-DD_<slug>.<ext>`.
- [`research-context/ARCHITECTURE.md`](research-context/ARCHITECTURE.md) — summary of the current animation architecture.
- [`research-context/OPEN_PROBLEMS.md`](research-context/OPEN_PROBLEMS.md) — the three problems, with what has been tried and where it stalls.
- [`research-context/reference-code/`](research-context/reference-code/) — two source files, extracted for reference.

This repository is a **context pack**, not the game. It carries no game source, no assets, and no credentials. Publishing is done by `scripts/sync_progress_log.sh` in the private repo, which refuses to stage anything but the progress log, its pointer, the screenshot index, and dated image files validated by magic bytes.
