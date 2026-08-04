# Breakdown: criwin-media-download

Started: 2026-08-03
Theme: The end-to-end media download path, grown along the existing `bot/` structure.

Supersedes tickets 1 and 2 of `criwin-discord-bot.md`, which shipped as KAN-1 and KAN-3 under
the `discord-bot-bootstrap.md` plan. This breakdown covers all remaining work.

## Stages
- [x] 1. Frame the scope
- [x] 2. Group into a theme
- [x] 3. Decompose into tickets
- [x] 4. Flesh out each ticket
- [x] 5. PR summaries

## Artifacts

### Stage 1: Frame the scope

#### Problem statement

I have no way to save images or videos from the platforms I use. Media posted to Instagram,
YouTube, Reddit, and TikTok can be viewed but not downloaded, and there is no path from a link
someone shares in Discord to a file I actually hold.

#### Goal

A Discord bot that accepts a URL from Instagram, YouTube, Reddit, or TikTok and privately
returns the media behind it to the requesting user, as a Discord attachment when it fits and as
a time-limited download link when it does not.

#### In scope

**The download feature**
- A slash command that accepts a URL from Instagram, YouTube, Reddit, or TikTok.
- Video and image posts, including multi-image posts (Instagram carousels, Reddit galleries).
- Delivery via ephemeral response, visible only to the requester.
- Media larger than 50 MB is rejected. Below that, the bot attaches the file directly when it
  fits within the guild's Discord attachment limit, read at runtime from the guild's boost tier,
  and otherwise stores it in MinIO and returns a presigned URL.
- One download in flight per user. A second request is refused until the first completes.

**Storage and data**
- MinIO for media objects. Objects are deleted after 24 hours, and presigned URLs expire at
  24 hours so the two clocks match.
- PostgreSQL as the datastore, accessed through an ORM with managed migrations.

**Platform**
- Multi-guild support. One deployment serves many Discord servers.
- Separate development and production bot applications. Development registers commands per
  guild for instant updates. Production registers globally and accepts Discord's propagation
  delay of up to an hour.
- Cookie files for extractor authentication, stored globally rather than per guild.

**Delivery and quality**
- Docker containers for every component, with all required images available.
- pytest coverage over the implemented features to guard against regressions.
- A Makefile for common commands.
- A README explaining the bot's purpose.
- Python 3.12.

#### Out of scope

- **The soundboard feature in its entirety.** Deferred to a later sprint. This includes voice
  channel playback, the sound panel, per-sound volume, bot clones, and the admin screens for
  creating, updating, and deleting sounds.
- **Batch and playlist downloads.** One URL, one job.
- **Transcoding or compressing media** to fit under an attachment limit. Oversized media is
  rejected or linked, never re-encoded.
- **Audio-only extraction.** Possible later.
- **Download history and re-download.** Objects expire and are gone.
- **An IAM-style role model.** The guild-scoped regular admin role is deferred. The schema should
  not preclude adding it, but nothing is built for it now.
- **Per-guild cookie files.**
- **The admin portal.** *(Amended at Stage 2. It was listed in scope at Stage 1, limited to cookie
  file upload and gated to a single super admin.)* Deferred to its own breakdown. Cookie rotation
  is served by a `make load-cookies` target run on the host, so the portal was the only admitted
  item whose removal did not break the goal, while it would have added a web framework, an
  authentication surface, an externally reachable port, and a second container image.

#### Constraints

**Production host.** Debian, 2 GB RAM, 2 vCores. SSD holds bot data, HDD holds media.
PostgreSQL, MinIO, the bot, and the admin portal are all co-resident on that 2 GB, alongside
FFmpeg during a download. FFmpeg merging a long video is the memory and CPU spike in that set,
and there are only two cores.

**Python 3.12.**

**PostgreSQL accessed through SQLAlchemy, with Alembic for migrations.** Confirmed during Stage 1
as still fixed rather than an open choice. No schema change lands outside a migration.

**Discord's attachment limit is not a constant.** It varies by guild boost tier, roughly 10 MB
unboosted, and must be read per guild at runtime rather than configured.

**Discord's interaction acknowledgement window is three seconds.** No download completes in that
time, so every download command must defer immediately and respond as a follow up.

**Extractor fragility.** yt-dlp breaks when the target platforms change their sites, and cookies
expire. Cookie rotation is ongoing maintenance, not a one-time setup, which is why cookie upload
is the one admin portal feature in scope.

**Terms of service.** Automated downloading from these platforms is against their terms. This is
accepted as a known risk for a personal deployment.

**Starting condition.** A running bot already exists: a flat `bot/` package with `discord.Client`
and a hand-built `CommandTree`, a class-attribute `Config` read from `os.getenv` and validated at
import, `requirements.txt`, a single-stage Dockerfile, a one-service `docker-compose.yml`, and a
Makefile with `dev`, `prod`, and `logs`. There is no test runner, no database, no object storage,
and no linter.

#### Answers given during Stage 1

1. **Scope size.** This breakdown is all remaining work, not a slice.
2. **ORM.** SQLAlchemy and Alembic remain fixed.
3. **Structure.** The scope must revolve around the bot structure.

#### Carried into Stage 2 unresolved

- **What "revolve around the bot structure" means.** Either the existing `bot/` layout is a
  constraint that new work conforms to, or the structure is itself a subject this scope may
  reshape. Stage 2's theme statement has to settle it, because it decides whether the
  decomposition opens with a restructuring ticket.
- **Whether the problem is personal or shared.** The problem statement is first person while
  multi-guild support is in scope.
- **Whether images follow the same size logic as video**, or always attach. The previous
  breakdown carried this as an open assumption and this framing does not settle it.
- **Three in-scope items already shipped:** the development and production sync split, the bot's
  Docker container, and Python 3.12. Recorded as inherited context rather than new work.
- **"Docker containers for every component, with all required images available"** has no stated
  pass condition.

### Stage 2: Group into a theme

#### Theme

**The end-to-end media download path, grown along the existing `bot/` structure.** Everything
required to take a URL from a slash command to a file in the requester's hands, added at the seams
the shipped bot already has, rather than in a shape imported from a plan that was never built.

#### Justification

Every remaining in-scope item exists because a URL must become a file the requester holds, and each
one attaches to a named seam in the current code (`Config`, the `setup_commands` registry, the
Compose topology) instead of replacing what those seams already do. With the portal deferred, every
admitted item fails the download path outright if removed, so there is no admitted exception left to
argue around.

#### The theme as a Stage 3 test

**Admitted.** The database and its migrations. Guild registration. URL parsing, extraction, and size
resolution. Cookie storage and the `make load-cookies` target that populates it. The media fetch, the
attachment branch, and the MinIO branch. The per-user lock. Object expiry. Typed errors and their
user-facing messages. A pytest harness and dev dependencies. Multi-service Compose. The README and
deployment notes.

**Rejected.** Everything on the out-of-scope list, plus:

- The admin portal, deferred to its own breakdown.
- Converting `discord.Client` to `commands.Bot` for its own sake.
- Replacing the `os.getenv` `Config` with `pydantic-settings` for its own sake.
- Adopting `uv`, `pyproject.toml`, or a `src/criwin/` layout. These appear throughout
  `criwin-discord-bot.md` and were never built, which makes that document's file lists reference
  material rather than instructions.
- Metrics, Grafana, Redis, structured logging with correlation IDs, and a CI pipeline.

#### The structure ruling

The existing structure is the constraint, not the subject. Nothing already merged gets restructured.
New work lands as new packages under `bot/` (`bot/db/`, `bot/media/`, `bot/storage/`, and so on), and
`Config` and `setup_commands` are extended in place. With the portal deferred there is no second
top-level application, so the repository stays one application with one image.

The one carve-out: `docker-compose.yml` grows from one service to three (bot, PostgreSQL, MinIO), and
`requirements.txt` splits runtime pins from development pins.

Known cost of this ruling: `Config` validates at import time, so importing anything under `bot`
requires the environment to be populated. That is a conftest fixture rather than a refactor.

#### Carried into Stage 3

**Cookies may no longer belong in PostgreSQL.** The previous plan put cookie contents in a database
row because the portal ran in a separate container and a row was the only storage both processes
could reach. With no portal, a bind-mounted cookie directory on the SSD, read straight by yt-dlp as
`cookiefile`, removes a model, a migration, the materialize-to-temp-file step, the permission
handling, and the cleanup-on-exception path.

### Stage 3: Decompose into tickets

Strictly linear. Every ticket depends only on the one before it.

`1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11 -> 12 -> 13`

| # | Title | Type | Goal | Files |
| --- | --- | --- | --- | --- |
| 1 | Test harness and development dependencies | Feature | `make test` runs pytest against the existing bot and reports a passing test rather than zero collected. | 6 |
| 2 | URL validation and media metadata extraction | Feature | `/download <url>` reports what media sits behind a supported link without fetching it. | 10 |
| 3 | Post size resolution and the 50 MB gate | Feature | The true total size of a post is resolved before any bytes are fetched, and posts over 50 MB or of unknown size are refused. | 6 |
| 4 | Cookie files and extractor authentication | Feature | yt-dlp authenticates with operator-supplied cookies, so all four platforms extract rather than three. | 10 |
| 5 | Media fetch and Discord attachment delivery | Feature | Media within the guild's attachment limit is downloaded and delivered ephemerally as a file. | 10 |
| 6 | MinIO storage and presigned URL delivery | Feature | Media too large to attach is uploaded to MinIO and returned as a 24 hour presigned link. | 9 |
| 7 | Database plumbing and Alembic migrations | Feature | PostgreSQL runs in Compose and the bot holds a working async session factory with migrations under Alembic control. | 11 |
| 8 | Guild registration | Feature | The bot records every guild it is in, which is multi-guild support made real and the first consumer of the database. | 5 |
| 9 | Per-user download concurrency lock | Feature | A user with a download in flight is refused a second one until the first finishes. | 6 |
| 10 | Stored object expiry | Feature | Objects are deleted 24 hours after upload so the link and the object die together. | 6 |
| 11 | User-facing failure handling | Feature | Every way a download can fail produces a distinct ephemeral message instead of a traceback or silence. | 7 |
| 12 | End-to-end regression coverage | Feature | The delivered path is covered well enough that a change breaking it fails the suite. | 8 |
| 13 | README and deployment documentation | Feature | A clean Debian host can be brought to a working bot using only the documentation. | 4 |

File counts for tickets 3 through 6 were revised upward during Stage 4, when the per-file lists
were written out. The original estimates were 5, 9, 8, and 8.

#### Decisions embedded in this ordering

- **The test harness is ticket 1, not ticket 12.** There is no pytest in the repository at all, and
  every later ticket carries its own tests. Ticket 1 also owns a real problem rather than a config
  file: `Config` validates at import time, so importing anything under `bot` inside a test fails on
  a machine with no `.env`.
- **The whole download path lands before any database work.** Tickets 1 through 6 deliver the
  Stage 1 goal in full. Nothing in that path needs PostgreSQL, because cookies moved to a bind
  mount. Building the database earlier would carry five tickets of unused infrastructure before the
  first consumer appeared, which is the speculative infrastructure the theme rejects.
- **The database arrives at ticket 7, immediately before the two things that need it:** the
  concurrency lock at 9 and object expiry at 10. Guild registration at 8 sits between them as the
  first consumer, which keeps ticket 7 from being plumbing that nothing exercises.
- **Tickets 7 and 8 are split**, where the previous plan kept database plumbing and guild
  registration together. Combined against the current structure they come to fifteen files.
- **Sizing is split out as ticket 3.** Extraction answers what is behind a URL. Sizing answers how
  big it is and whether it is refused.
- **The concurrency lock lands at ticket 9, after the fetch**, so it guards a real multi-second
  download and can be demonstrated rather than argued about.
- **Failure handling is its own ticket at 11**, after every failure surface exists, so the messages
  are designed as one coherent set.
- **Ticket 5 owns two decisions** without an obvious home: the temp file lifecycle, and what happens
  to a carousel of more than ten images, since Discord caps attachments per message at ten.

#### The cookie storage decision, settled here

Cookies go in a bind-mounted directory on the SSD, not in PostgreSQL. The database row existed to
let a separate portal container write cookies, and that container is deferred. `make load-cookies`
becomes a copy into the mounted directory. If the portal returns, it needs either a shared volume or
a migration of cookies into the database at that point.

#### Accepted costs of the linear order

- **Objects uploaded between tickets 6 and 10 are untracked and never expire.** Ticket 10 either
  reconciles against the bucket on first run, or the operator wipes the bucket once.
- **A user can issue concurrent downloads from ticket 5 until ticket 9.**
- **Ticket 11 is the widest ticket in the chain**, because it maps failures from extraction, sizing,
  cookies, fetch, storage, and the lock into one message set.

### Stage 4: Ticket detail

Produced as a set rather than one at a time, at the author's request.

Estimate correction: writing the per-file lists moved four counts. Ticket 3 went from 5 to 6,
ticket 4 from 9 to 10, ticket 5 from 8 to 10, ticket 6 from 8 to 9. The additions are almost
entirely `.env.example`, `.gitignore`, and `Makefile` edits that were not counted at Stage 3.

---

#### Ticket 1: Test harness and development dependencies

**Goal.** `make test` runs pytest against the existing bot and reports a passing test rather than
zero collected.

**Concepts.** pytest imports a `conftest.py` before any test module in its directory tree, which is
the only hook available for work that must happen before your package is imported. `pytest-asyncio`
with `asyncio_mode = auto` lets every later `async def` test run without a per-test decorator.

| File | Purpose |
| --- | --- |
| `requirements-dev.txt` | `pytest` and `pytest-asyncio`, separate from `requirements.txt` so the production image does not carry a test runner. |
| `pytest.ini` | A standalone ini file rather than a `pyproject.toml` block, per the structure ruling. Sets `asyncio_mode = auto`, `testpaths = tests`, and `pythonpath = .`. |
| `tests/conftest.py` | Sets `DISCORD_TOKEN`, `ENVIRONMENT`, and `DEV_GUILD_ID` at module scope, before any test imports `bot.config`. |
| `tests/test_config.py` | Asserts `Config` loads the fixture environment and that an invalid `ENVIRONMENT` raises. |
| `Makefile` (edit) | `install-dev` and `test`. `.PHONY` must list `test`, which collides with the `tests/` directory otherwise. |
| `.gitignore` (edit) | `.pytest_cache/`. |

**Mechanic worth knowing.** `bot/config.py` validates in the class body, which runs at import time
and raises if `DISCORD_TOKEN` is unset. Setting the environment inside a fixture is too late: the
test module has already been imported during collection. The environment must be populated at the
top level of `conftest.py`, outside any fixture. The alternative, moving validation into a function,
is a change to shipped code that the structure ruling rejects.

**Done when.** `make test` on a clean checkout with no `.env` reports at least one passing test and
zero collection errors.

---

#### Ticket 2: URL validation and media metadata extraction

**Goal.** `/download <url>` reports what media sits behind a supported link without fetching it.

**Concepts.** `YoutubeDL.extract_info(url, download=False)` returns metadata without fetching:
`title`, `extractor`, `formats`, `filesize` or `filesize_approx`, and an `entries` list for a
multi-item post. A carousel and a single video differ only in whether `entries` is present, which is
what lets one normalization function cover both.

| File | Purpose |
| --- | --- |
| `requirements.txt` (edit) | Pins `yt-dlp`. Expect to bump it often. |
| `bot/media/platforms.py` | The four-platform allowlist, rejecting unsupported hosts before any network call. Handles `youtu.be`, `m.youtube.com`, `vm.tiktok.com`, `old.reddit.com`, and `www` prefixes. |
| `bot/media/types.py` | `MediaItem` and `MediaPost`. The boundary that keeps yt-dlp's raw dictionary out of commands, storage, and delivery. |
| `bot/media/extractor.py` | The yt-dlp wrapper. Runs extraction in a worker thread and normalizes single and `entries` cases into one `MediaPost`. |
| `bot/commands/download/__init__.py` | `setup_download(tree)`, mirroring `bot/commands/ping/__init__.py`. |
| `bot/commands/download/download.py` | `handle_download(interaction, url)`. Defers ephemerally first, validates the host, extracts, reports. |
| `bot/commands/setup.py` (edit) | One line registering the command. This file is the registry seam the structure ruling preserves. |
| `Dockerfile` (edit) | Installs FFmpeg, which `python:3.12-slim` lacks and yt-dlp needs to merge separate video and audio streams. |
| `tests/test_platforms.py` | Every host variant, plus rejection of unsupported hosts and non-URLs. |
| `tests/test_extractor.py` | Normalization of a single video and a carousel, against recorded metadata rather than live calls. |

**Mechanics worth knowing.** yt-dlp is synchronous. Calling `extract_info` inside a coroutine stalls
the event loop, which stops the bot answering anything and eventually causes gateway heartbeat
timeouts and a disconnect. Every call goes through `asyncio.to_thread`, and the same applies to the
fetch in ticket 5. Separately, `interaction.response.defer(ephemeral=True)` must be the first
statement in the handler, before host validation, because the acknowledgement window is three
seconds and an early raise leaves the user with Discord's generic failure text.

**Done when.** YouTube, Reddit, and TikTok links report accurate title and item count, an unsupported
host is refused without a network call, and `/ping` still answers during an extraction. Instagram is
expected to fail here and is fixed in ticket 4.

---

#### Ticket 3: Post size resolution and the 50 MB gate

**Goal.** The true total size of a post is resolved before any bytes are fetched, and posts over
50 MB or of unknown size are refused.

**Concepts.** `HEAD` returns headers without a body, so `Content-Length` gives a size for one round
trip. Servers rejecting `HEAD` usually honour `Range: bytes=0-0`, whose `Content-Range` header ends
with the total size.

| File | Purpose |
| --- | --- |
| `requirements.txt` (edit) | Pins `httpx`. |
| `bot/media/sizing.py` | The ladder: `filesize`, `filesize_approx`, `HEAD`, ranged `GET`, summed across every entry. Applies the cap and the refuse-when-unknown rule. |
| `bot/config.py` (edit) | `MAX_POST_BYTES`, default 50 MB, parsed to `int`. |
| `.env.example` (edit) | Documents `MAX_POST_BYTES`. |
| `bot/commands/download/download.py` (edit) | Calls the resolver and reports size and the accept or refuse decision. |
| `tests/test_sizing.py` | Each rung, the summed carousel, refusal above the cap, refusal when size is unknown. |

**Policy this ticket owns.** The cap is per post, not per file, so twelve 5 MB images are refused at
60 MB. Segmented HLS or DASH formats with no single `Content-Length` are refused rather than
attempted. Ticket 5 trusts this answer and does not re-check.

**Least confident.** `filesize` is absent more often than expected and `filesize_approx` is exactly
what its name says. If the approximation runs under the true size near the boundary, a post passes
the gate and downloads larger than 50 MB. Whether an approximate size is trusted at all, or only
comfortably under the cap, is a real decision without a confident recommendation.

**Done when.** An oversized post is refused before any fetch, a carousel reports the sum rather than
the first item, and a segmented format is refused.

---

#### Ticket 4: Cookie files and extractor authentication

**Goal.** yt-dlp authenticates with operator-supplied cookies, so all four platforms extract rather
than three.

**Concepts.** yt-dlp reads cookies from a Netscape-format text file passed as `cookiefile`, exported
from a logged-in browser session. Cookies expire, so replacement is routine maintenance, which is
why `make load-cookies` exists.

| File | Purpose |
| --- | --- |
| `bot/config.py` (edit) | `COOKIE_DIR`, defaulting to a path on the SSD. |
| `bot/media/cookies.py` | Resolves `<COOKIE_DIR>/<platform>.txt` or returns `None`. Deliberately trivial, which is the payoff of the bind mount decision. |
| `bot/media/extractor.py` (edit) | Passes `cookiefile` when a cookie exists, omits the key entirely when it does not. |
| `docker-compose.yml` (edit) | Mounts the host cookie directory read-only. Nothing in the bot should write a cookie file. |
| `Makefile` (edit) | `load-cookies`, copying a named file into place under the right platform name with `0600`. |
| `.env.example` (edit) | Documents `COOKIE_DIR`. |
| `.gitignore` (edit) | Excludes the cookie directory. A committed cookie file is a committed session. |
| `.dockerignore` (edit) | Same directory, so a cookie cannot be baked into an image layer. |
| `tests/test_cookies.py` | Resolution when present, `None` when absent, no exception when the directory is missing. |
| `tests/test_extractor.py` (edit) | `cookiefile` present when a cookie exists, absent when it does not. |

**Why the bind mount.** Against the database approach it replaces, it removes a model, a migration,
a materialize-to-temp-file step, permission handling on that temp file, and a cleanup path that has
to run even when extraction raises.

**Done when.** An Instagram post that failed in ticket 2 extracts after `make load-cookies`, and
removing the file makes it fail again without an unhandled exception.

---

#### Ticket 5: Media fetch and Discord attachment delivery

**Goal.** Media within the guild's attachment limit is downloaded and delivered ephemerally as a
file.

**Concepts.** `discord.Guild.filesize_limit` returns the upload ceiling in bytes directly, so there
is no need to derive it from the boost tier as the Stage 1 scope assumed. Files go out as
`discord.File` objects through `interaction.followup.send(files=[...], ephemeral=True)`, since the
interaction was deferred in ticket 2.

| File | Purpose |
| --- | --- |
| `bot/media/downloader.py` | Fetches with yt-dlp into a per-invocation temp directory through `asyncio.to_thread`, and guarantees removal on success and failure. |
| `bot/config.py` (edit) | `MEDIA_TMP_DIR`, on the HDD per the Stage 1 disk split. |
| `bot/delivery/limits.py` | Reads `guild.filesize_limit` and returns the attach-or-store decision. Ticket 6 replaces the store stub. |
| `bot/delivery/attachment.py` | Builds `discord.File` objects and sends them, splitting into groups of ten. |
| `bot/commands/download/download.py` (edit) | Wires extraction to sizing to fetch to delivery. |
| `docker-compose.yml` (edit) | Mounts the HDD media path into the bot container. |
| `.env.example` (edit) | Documents `MEDIA_TMP_DIR`. |
| `tests/test_downloader.py` | Fetch and temp directory removal, including on raise. |
| `tests/test_limits.py` | The attach-or-store decision across limits, including the DM case. |
| `tests/test_attachment.py` | Splitting a twelve item carousel into two messages, and the single file case. |

**Mechanics worth knowing.** Discord allows at most ten attachments per message, so a twelve image
carousel cannot go out in one follow-up, which is why `bot/delivery/attachment.py` is a module rather
than three lines in the command. Separately, `interaction.guild` is `None` in a direct message and
reading `.filesize_limit` off it raises `AttributeError`. Since the response is ephemeral, a user may
well try it in a DM. The fallback is Discord's base limit rather than a crash.

**Temp file policy this ticket owns.** One directory per invocation, named by interaction ID, removed
in a `finally`. A leaked directory per failed download fills the HDD quietly, and ticket 10's sweep
covers MinIO objects rather than these.

**Sizing.** Ten files, at the ceiling. The seam, if needed, is `bot/delivery/` and its two tests
moving into a separate ticket from the downloader.

**Done when.** A small TikTok video and a three image Reddit gallery arrive as ephemeral attachments,
a twelve image gallery arrives across two messages, the temp directory is empty afterward including
after a failure, and a DM invocation does not raise.

---

#### Ticket 6: MinIO storage and presigned URL delivery

**Goal.** Media too large to attach is uploaded to MinIO and returned as a 24 hour presigned link.

**Concepts.** MinIO is an S3-compatible object store. A presigned URL carries a signature and an
expiry in its query string, so anyone holding it can fetch the object without credentials until it
expires.

| File | Purpose |
| --- | --- |
| `requirements.txt` (edit) | Pins `minio`. |
| `bot/config.py` (edit) | Internal endpoint, public endpoint, access key, secret key, bucket, TLS flag. Two endpoints deliberately. |
| `bot/storage/client.py` | Bucket creation if absent, upload, and presign. Every call through `asyncio.to_thread`, because the MinIO client is synchronous like yt-dlp. |
| `bot/delivery/link.py` | Formats the follow-up message: the link, what it points at, and when it expires. |
| `bot/delivery/limits.py` (edit) | Replaces the ticket 5 stub so the store branch is real. |
| `bot/commands/download/download.py` (edit) | Takes the store branch when media exceeds the guild limit. |
| `docker-compose.yml` (edit) | MinIO service with its data volume on the HDD. |
| `.env.example` (edit) | Documents all six settings. |
| `tests/test_storage.py` | Upload, presign, and that the URL carries the public endpoint rather than the internal one. |

**Mechanic worth knowing, and the one defect here that passes its own tests.** A presigned URL embeds
the hostname it was signed against. Signed against the Compose service name it produces
`http://minio:9000/...`, which resolves only inside the Docker network and is a dead link for every
user, while every test passes. Changing the host after signing invalidates the signature, so this
cannot be patched by string replacement. The hostname assertion in `tests/test_storage.py` is the
guard.

**Note.** Between this ticket and ticket 10, links expire at 24 hours while the objects behind them
live indefinitely.

**Done when.** An oversized file returns a link that opens from a browser outside the Docker host.

---

#### Ticket 7: Database plumbing and Alembic migrations

**Goal.** PostgreSQL runs in Compose and the bot holds a working async session factory with
migrations under Alembic control.

**Concepts.** SQLAlchemy 2.0 async needs an async driver, so the URL scheme is
`postgresql+asyncpg://`. Alembic autogenerates by diffing `DeclarativeBase.metadata` against the live
database, which is why `migrations/env.py` must import the models and read the URL from the
environment.

| File | Purpose |
| --- | --- |
| `requirements.txt` (edit) | Pins `sqlalchemy[asyncio]`, `asyncpg`, `alembic`. |
| `bot/config.py` (edit) | `DATABASE_URL`, required in every environment. |
| `bot/db/base.py` | The `DeclarativeBase` whose metadata Alembic diffs against, inherited by every model in tickets 8, 9, and 10. |
| `bot/db/session.py` | Async engine, `async_sessionmaker`, and a session context manager. Pool size matters: the host has 2 GB with PostgreSQL co-resident, so the default pool is larger than this deployment wants. |
| `alembic.ini` | Configuration with `sqlalchemy.url` left blank, so no credential lands in a committed file. |
| `migrations/env.py` | Points Alembic at the metadata and the runtime URL. Always requires hand editing after `alembic init`, doubly so for async. |
| `migrations/script.py.mako` | Generated template, committed unmodified. |
| `docker-compose.yml` (edit) | PostgreSQL service, volume on the SSD, plus a healthcheck. |
| `.env.example` (edit) | Documents `DATABASE_URL` and the PostgreSQL credentials Compose needs. |
| `Makefile` (edit) | `migrate` and `revision`, run inside the container so tooling matches the deployed environment. |
| `tests/test_session.py` | The factory opens a session and executes a trivial statement. |

**Mechanics worth knowing.** Alembic's generated `env.py` is synchronous. Against an async engine it
must build an `AsyncEngine` and run migrations inside `connection.run_sync(...)`. Skipping this fails
confusingly at `alembic upgrade` rather than at import. Separately, plain `depends_on` waits only for
the container to start, not for PostgreSQL to accept connections, so the bot loses the race on a cold
boot without a healthcheck condition.

**Sizing.** Eleven files, knowingly over. Three are Alembic scaffold. The seam, if needed, is between
the scaffold and the engine plus session factory.

**Done when.** `make migrate` runs against a fresh database and reports no pending migrations, and a
cold `docker compose up` brings the bot up without a connection error.

---

#### Ticket 8: Guild registration

**Goal.** The bot records every guild it is in, which is multi-guild support made real and the first
consumer of the database.

**Concepts.** PostgreSQL's `INSERT ... ON CONFLICT DO UPDATE` upserts in one statement, exposed as
`sqlalchemy.dialects.postgresql.insert(...).on_conflict_do_update(...)`. It is dialect-specific and
not available on the generic `insert`.

| File | Purpose |
| --- | --- |
| `bot/models/guild.py` | The `guild` table: Discord guild ID as primary key, name, joined timestamp. |
| `migrations/versions/0001_create_guild.py` | First migration, autogenerated then reviewed. |
| `bot/services/guilds.py` | The upsert, kept out of the client so it is testable without a gateway. |
| `bot/client.py` (edit) | Upserts from `on_ready` for every guild in `self.guilds`, and from `on_guild_join`. |
| `tests/test_guild_registration.py` | A join writes one row, a repeated `on_ready` does not duplicate, a rename updates. |

**Mechanics worth knowing.** `on_ready` is not once per process: discord.py fires it again after
every reconnection, so registration must be idempotent, which is what makes the upsert the right
shape rather than select-then-insert. Select-then-insert also races against a simultaneous
`on_guild_join`. Discord IDs exceed 32 bits, so the column is `BigInteger`; a plain `Integer` accepts
a small test value and overflows on a real one.

**Done when.** A fresh server join writes exactly one row, repeated restarts add no rows and raise
nothing, and a renamed guild updates the stored name.

---

#### Ticket 9: Per-user download concurrency lock

**Goal.** A user with a download in flight is refused a second one until the first finishes.

**Concepts.** A partial unique index applies only to rows matching a condition
(`CREATE UNIQUE INDEX ... WHERE status = 'active'`). It permits many completed jobs per user and at
most one active job per user, which is exactly the rule here.

| File | Purpose |
| --- | --- |
| `bot/models/download_job.py` | Job rows: user ID, status, started timestamp. |
| `migrations/versions/0002_create_download_job.py` | Schema plus the partial index via `op.create_index(..., unique=True, postgresql_where=...)`. |
| `bot/services/job_lock.py` | Acquire, release, and reclaim jobs left active by a crash. |
| `bot/commands/download/download.py` (edit) | Acquires before the fetch, releases in a `finally`. |
| `tests/test_job_lock.py` | Acquire, contention, release, stale reclamation. |
| `tests/test_download_concurrency.py` | A second command during an in-flight download is refused. |

**Why the database and not a Python set.** An in-memory lock is less code but does not survive a
restart, so a crash mid-download leaves nothing to release and the user stays blocked. The partial
index also makes the constraint the database's job, so two commands racing on one user cannot both
acquire regardless of how the Python is written.

**The parameter that matters.** Too short a stale reclamation timeout reclaims a legitimately slow
download underneath itself, producing two concurrent fetches for one user, which is the exact thing
this ticket prevents. Set it well above the longest plausible download.

**Done when.** Two rapid `/download` commands produce one download and one refusal, and killing the
bot mid-download does not leave that user permanently blocked.

---

#### Ticket 10: Stored object expiry

**Goal.** Objects are deleted 24 hours after upload so the link and the object die together.

**Concepts.** `discord.ext.tasks.loop` runs a coroutine on an interval tied to the bot lifecycle. It
works with a plain `discord.Client` and does not require `commands.Bot`, so it fits the current
structure without change.

| File | Purpose |
| --- | --- |
| `bot/models/stored_object.py` | Object key, created timestamp, expiry timestamp. |
| `migrations/versions/0003_create_stored_object.py` | Schema, indexed on expiry since the sweep queries by it. |
| `bot/tasks/cleanup.py` | The sweep: select expired rows, remove each object, delete the row. |
| `bot/storage/client.py` (edit) | Adds object removal. |
| `bot/client.py` (edit) | Starts the loop in `setup_hook` and cancels it on close. |
| `tests/test_cleanup.py` | Expired removed, unexpired kept, and a MinIO failure does not kill the loop. |

**Why a task and not a lifecycle rule.** S3 and MinIO lifecycle expiration is day granular and
measured from a day boundary, so it cannot express 24 hours from a specific upload. Running the sweep
in the bot process also avoids adding a scheduler container to a 2 GB host.

**Mechanic worth knowing.** An unhandled exception inside a `tasks.loop` stops the loop permanently
and quietly. A brief MinIO outage during one sweep would stop expiry forever, and the HDD fills over
the following weeks with no visible error. The sweep body needs its own exception handling plus a
`@loop.error` backstop.

**The gap from ticket 6, now due.** Objects uploaded between tickets 6 and 10 have no row and will
never be swept. Either reconcile the bucket against the table on first run, or empty the bucket once
at deploy. Emptying is recommended: the objects are disposable by design, and reconciliation code
that runs exactly once is code you will never trust again.

**Done when.** An object written with a backdated expiry is gone after one sweep along with its row,
and a sweep against an unreachable MinIO logs an error and runs again next interval.

---

#### Ticket 11: User-facing failure handling

**Goal.** Every way a download can fail produces a distinct ephemeral message instead of a traceback
or silence.

| File | Purpose |
| --- | --- |
| `bot/errors.py` | Typed exceptions: unsupported platform, extraction failed, authentication required, size unknown, too large, download in progress, storage unavailable. |
| `bot/media/extractor.py` (edit) | Maps yt-dlp `DownloadError` text onto typed errors, separating a private or deleted post from an expired cookie from a genuine extractor break. |
| `bot/media/sizing.py` (edit) | Raises typed errors instead of returning sentinels. |
| `bot/commands/download/download.py` (edit) | One handler mapping each typed error to its message. |
| `bot/client.py` (edit) | `tree.on_error`, so anything unmapped still produces a response. |
| `tests/test_errors.py` | Real yt-dlp error strings map to the right typed error. |
| `tests/test_error_messages.py` | Every typed error produces a distinct message, and no two collide. |

**Why this matters more than it looks.** Stage 1 accepts extractor breakage as ongoing maintenance,
which makes these messages the primary diagnostic surface. "Too large" versus "size could not be
determined" are the same refusal to a user and completely different signals to the operator: without
the distinction there is no way to tell whether ticket 3's refuse-on-unknown policy is rejecting far
more than expected. "Authentication required" versus "extraction failed" is the difference between
running `make load-cookies` and reading a yt-dlp changelog.

**Mechanic worth knowing.** After a defer, `interaction.response.send_message` raises. Every error
path must use `interaction.followup.send`, and `tree.on_error` cannot assume either state, so it
branches on `interaction.response.is_done()`. Getting this wrong makes the error handler itself
raise, which produces the exact generic failure text this ticket exists to prevent.

**Fragility to accept.** Error text mapping is string matching against yt-dlp messages and will drift
when wording changes. The fallback for an unrecognized message must be the generic extraction
failure, so drift degrades message quality rather than breaking the command.

**Done when.** A private Instagram post, an expired cookie, an unsupported host, an oversized post,
an unmeasurable post, and a second concurrent download each produce a different message, and an
injected unmapped exception still produces a response.

---

#### Ticket 12: End-to-end regression coverage

**Goal.** The delivered path is covered well enough that a change breaking it fails the suite.

| File | Purpose |
| --- | --- |
| `tests/fakes/discord.py` | Fake interaction, guild, and follow-up, recording what was sent, so command tests need no gateway. |
| `tests/fakes/ytdlp.py` | Recorded metadata for each platform, including a carousel and a segmented format. |
| `tests/fakes/storage.py` | In-memory object store standing in for MinIO. |
| `tests/test_end_to_end.py` | Command to extraction to size gate to fetch to delivery, for both the attach and link branches. |
| `tests/conftest.py` (edit) | Registers the fakes as fixtures. |
| `requirements-dev.txt` (edit) | Adds `pytest-cov`. |
| `pytest.ini` (edit) | Coverage configuration and a failure threshold. |
| `Makefile` (edit) | `coverage` target. |

**Note on ordering.** Stage 1 asked for pytest coverage over implemented features. Each ticket
carries its own tests instead, and this one fills gaps and adds the end-to-end path. Retrofitting all
coverage across eleven merged tickets produces worse tests, and the concurrency lock in particular is
far easier to verify with a test than by hand in Discord.

**The risk here.** A fake that accepts what the real API rejects gives false confidence, which is
worse than no test. The fake follow-up should enforce the ten attachment cap, and the fake
interaction should raise if `response.send_message` is called after a defer. Permissive fakes let
ticket 5's splitting logic and ticket 11's followup discipline pass while being wrong in production.

**Done when.** `make coverage` passes its threshold, and deliberately breaking the size gate or the
attachment split fails the suite.

---

#### Ticket 13: README and deployment documentation

**Goal.** A clean Debian host can be brought to a working bot using only the documentation.

| File | Purpose |
| --- | --- |
| `README.md` | Replaces the bootstrap content: what the bot does, the four platforms, the size and expiry rules, and local setup including `make test`. |
| `docs/deployment.md` | The Debian host: the SSD and HDD volume split, Compose bring-up order, migrations on deploy, loading cookies, and the up-to-an-hour propagation of production global command sync. |
| `docs/configuration.md` | Every environment variable across the thirteen tickets, its default, and which component reads it. |
| `Makefile` (edit) | A production bring-up target matching the deployment document exactly, so document and tooling cannot drift. |

**One correction this ticket must carry.** The current `README.md` states that `make dev` runs in the
foreground, while the `Makefile` passes `-d` and runs detached. That line is wrong today and stays
wrong until fixed here.

**Done when.** A clean Debian host reaches a working bot using only these documents, with no step
remembered from outside them.

---

#### Least confident across the set

- **Ticket 3's treatment of `filesize_approx`** near the 50 MB boundary, without real values to
  reason from.
- **Ticket 5 at ten files**, carrying the temp file lifecycle, the guild limit read, the DM edge
  case, and the ten attachment split.
- **Ticket 11's error text mapping**, since a private Instagram post and an expired cookie may not be
  reliably distinguishable. If they are not, that ticket collapses two messages into one and says so
  rather than guessing.

### Stage 5: PR summaries

Each body is deliberately short. The reasoning lives in the Stage 4 ticket, which every PR
references rather than repeats.

---

**1. Test harness and development dependencies**

Adds `pytest` and `pytest-asyncio` in a separate `requirements-dev.txt`, a standalone `pytest.ini`
with `asyncio_mode = auto` and `pythonpath = .`, a `conftest.py` that populates the environment, one
real test over `Config`, and `make install-dev` and `make test`.

No `pyproject.toml`, no `src/` layout, no `uv`. This project uses `requirements.txt` and a flat
`bot/` package, and this PR stays inside that.

Look hardest at: why the environment is set at the top level of `conftest.py` rather than in a
fixture. `bot/config.py` validates in the class body at import time, so a fixture runs too late and
collection fails before any test does.

Verified by: `make test` on a clean checkout with no `.env`, reporting at least one passing test and
zero collection errors.

---

**2. URL validation and media metadata extraction**

Adds `/download <url>`. Rejects unsupported hosts against a four-platform allowlist before any
network call, extracts metadata with yt-dlp without fetching media, and normalizes single posts and
carousels into one `MediaPost` shape. Adds FFmpeg to the image.

Look hardest at: the `asyncio.to_thread` boundary and the placement of the defer. yt-dlp is
synchronous, so calling it inline stalls the event loop until the gateway heartbeat times out and the
bot disconnects. The defer must be the handler's first statement, because the acknowledgement window
is three seconds and anything that raises before it leaves the user with Discord's generic failure
text. Both bugs look identical from the outside.

Verified by: accurate title and item count for YouTube, Reddit, and TikTok links, an unsupported host
refused without a network call, and `/ping` still answering during an extraction. Instagram is
expected to fail and is fixed in PR 4.

---

**3. Post size resolution and the 50 MB gate**

Resolves the true total size of a post before any bytes are fetched: yt-dlp fields first, then an
HTTP `HEAD`, then a ranged `GET` where `HEAD` is rejected, summed across every item. Posts over 50 MB
are refused, and so are posts whose size cannot be determined.

The cap is per post, not per file: a gallery of twelve 5 MB images is refused at 60 MB.

Look hardest at: how `filesize_approx` is treated near the boundary. It is present far more often
than `filesize`, and if it runs under the true size, a post passes the gate and then downloads larger
than the cap. Also worth checking that the refuse-on-unknown path actually triggers for a segmented
format rather than falling through.

Verified by: an oversized post refused before any fetch, a carousel reporting the sum rather than the
first item, and a segmented format refused.

---

**4. Cookie files and extractor authentication**

Reads a Netscape-format cookie file per platform from a bind-mounted directory on the SSD and passes
it to yt-dlp as `cookiefile`. Adds `make load-cookies`.

Cookies are files rather than database rows because the admin portal was deferred at Stage 2. That
decision removed a model, a migration, a materialize-to-temp-file step, permission handling, and a
cleanup-on-exception path from this PR.

Look hardest at: the `.gitignore` and `.dockerignore` entries. A cookie file is a live session for
your account on that platform, and both lines need to land before the first real cookie file does.
Also confirm the Compose mount is read-only.

Verified by: an Instagram post that failed in PR 2 extracting after `make load-cookies`, and failing
again without an unhandled exception once the file is removed.

---

**5. Media fetch and Discord attachment delivery**

Downloads accepted posts into a per-invocation temp directory on the HDD and delivers them as
ephemeral attachments when they fit `guild.filesize_limit`. Carousels beyond Discord's ten attachment
cap are split across follow-ups.

Look hardest at three things: temp directory removal on the error path as well as the happy path,
since a leak per failed download fills the HDD quietly; the ten attachment split, which only bites on
larger carousels and is easy to miss in manual testing; and `interaction.guild` being `None` in a
direct message, where reading `.filesize_limit` raises `AttributeError`. The response is ephemeral,
so someone will try it in a DM.

Ten files, at the size ceiling. The seam if it needs splitting is `bot/delivery/` separating from the
downloader.

Verified by: a small TikTok video and a three image gallery arriving as attachments, a twelve image
gallery arriving across two messages, an empty temp directory after both success and failure, and a
DM invocation that does not raise.

---

**6. MinIO storage and presigned URL delivery**

Uploads media exceeding the guild attachment limit to MinIO and returns a 24 hour presigned URL. Adds
the MinIO service with its data volume on the HDD.

Look hardest at: the endpoint configuration, which is the one defect in this breakdown that passes
its own tests. A presigned URL embeds the host it was signed against, so signing against the Compose
service name produces `http://minio:9000/...`, which resolves only inside the Docker network and is a
dead link for every user. Internal and public endpoints are configured separately for exactly this
reason, and the signature cannot be repaired by rewriting the host afterward.

Also note: links expire at 24 hours from this PR, but nothing deletes the objects until PR 10.

Verified by: an oversized file returning a link that opens from a browser on a machine outside the
Docker host.

---

**7. Database plumbing and Alembic migrations**

Adds PostgreSQL to Compose with its volume on the SSD, SQLAlchemy 2.0 async with `asyncpg`, a session
factory, and an Alembic setup pointed at the declarative metadata with the URL read from the
environment. Adds `make migrate` and `make revision`.

Eleven files, over the usual guideline, three of them Alembic scaffold.

Look hardest at: `migrations/env.py`. The generated file is synchronous, and against an async engine
it must run migrations inside `connection.run_sync(...)`, which fails confusingly at upgrade time
rather than at import if missed. Also check that `alembic.ini` carries no URL, and that the Compose
`depends_on` uses a healthcheck condition rather than plain container start, or the bot loses the
race on a cold boot.

Verified by: `make migrate` against a fresh database reporting no pending migrations, and a cold
`docker compose up` with no connection error.

---

**8. Guild registration**

Adds the `guild` table and upserts a row from `on_ready` and `on_guild_join`. This is the multi-guild
support from Stage 1 made real, and the first consumer of the database from PR 7.

Look hardest at: idempotence. `on_ready` fires again after every reconnection, not once per process,
so this has to be an upsert rather than a select-then-insert, which also races against a simultaneous
`on_guild_join`. Second, confirm the ID column is `BigInteger`: Discord IDs exceed 32 bits, and
`Integer` accepts a small test value and overflows on a real one.

Verified by: a fresh server join writing exactly one row, repeated restarts adding none, and a
renamed guild updating rather than inserting.

---

**9. Per-user download concurrency lock**

Adds a `download_job` table with a unique partial index over active jobs per user, acquired before
the fetch and released in a `finally`, with reclamation for jobs left active by a crash.

The lock is in the database rather than in process memory because an in-memory lock does not survive
a restart: a crash mid-download would leave nothing to release and block that user until the next
restart.

Look hardest at: the partial index, which is what makes two racing commands unable to both acquire
regardless of the Python, and the reclamation timeout. Too short and it reclaims a legitimately slow
download underneath itself, producing exactly the two concurrent fetches this PR exists to prevent.

Verified by: two rapid `/download` commands producing one download and one refusal, and a
mid-download kill not leaving that user blocked.

---

**10. Stored object expiry**

Tracks uploaded objects with an expiry timestamp and sweeps them from MinIO on a `discord.ext.tasks`
loop, so the object and its 24 hour link die together.

An S3 lifecycle rule cannot express this: expiration is day granular and measured from a day boundary
rather than from upload. Running the sweep in the bot process avoids adding a scheduler container to
a 2 GB host.

Look hardest at: loop resilience. An unhandled exception inside a `tasks.loop` stops it permanently
and quietly, so one brief MinIO outage would end expiry forever while the HDD fills over the
following weeks with no visible error. The sweep needs its own exception handling plus a
`@loop.error` backstop.

Note before deploying: objects uploaded between PR 6 and this one have no row and will never be
swept. Empty the bucket once rather than writing reconciliation code that runs exactly once.

Verified by: an object with a backdated expiry gone after one sweep along with its row, and a sweep
against an unreachable MinIO logging an error and running again on the next interval.

---

**11. User-facing failure handling**

Introduces a typed error hierarchy, maps yt-dlp's `DownloadError` text onto it, and gives each error
a distinct ephemeral message. Adds `tree.on_error` so an unmapped exception never leaves the user
with Discord's generic failure text.

Look hardest at: the distinction between "too large" and "size could not be determined." They are the
same refusal to a user and completely different signals to you, and collapsing them makes it
impossible to tell whether PR 3's refuse-on-unknown policy is rejecting far more than you think.
Second, every error path must use `followup.send` rather than `response.send_message`, since the
interaction was already deferred, and `on_error` has to branch on `interaction.response.is_done()`
because it cannot assume either state.

Accepted fragility: error text matching drifts when yt-dlp changes wording, so an unrecognized
message must fall back to the generic extraction failure rather than raising.

Verified by: a private Instagram post, an expired cookie, an unsupported host, an oversized post, an
unmeasurable post, and a second concurrent download each producing a different message, and an
injected unmapped exception still producing a response.

---

**12. End-to-end regression coverage**

Adds shared fakes for Discord, yt-dlp, and object storage, an end-to-end test covering the command
through extraction, the size gate, the fetch, and both delivery branches, plus coverage configuration
and `make coverage`.

Tests were written per PR rather than deferred wholesale to this one. This PR fills gaps and adds the
end-to-end path.

Look hardest at: whether the fakes are faithful. A fake that accepts what the real API rejects gives
false confidence, which is worse than no test. Specifically, the fake follow-up should enforce the
ten attachment cap and the fake interaction should raise if `response.send_message` is called after a
defer. If they do not, PR 5's splitting logic and PR 11's followup discipline both pass while being
wrong in production.

Verified by: `make coverage` passing its threshold, and a deliberate break of either the size gate or
the attachment split failing the suite.

---

**13. README and deployment documentation**

Replaces the bootstrap README with real content, and adds deployment and configuration documents
covering the Debian host, the SSD and HDD volume split, Compose bring-up order, migrations on deploy,
cookie loading, and the up-to-an-hour propagation of production global command sync. Adds a
production bring-up target matching the deployment document.

Also fixes a line that is wrong today: the README claims `make dev` runs in the foreground, while the
Makefile passes `-d`.

Look hardest at: whether the deployment document is actually sufficient. The test is a clean host,
not a familiar one, so read it as someone who has never seen this repository.

Verified by: bringing a clean Debian host to a working bot using only these documents.
