# Breakdown: criwin-discord-bot

Started: 2026-08-03
Theme: The foundational platform for the bot, bounded by a single end-to-end media download path.

## Stages
- [x] 1. Frame the scope
- [x] 2. Group into a theme
- [x] 3. Decompose into tickets
- [x] 4. Flesh out each ticket
- [x] 5. PR summaries

## Artifacts

### Stage 1: Frame the scope

#### Problem statement

I have no way to save images or videos from the platforms I use. Media posted to
Instagram, YouTube, Reddit, and TikTok can be viewed but not downloaded, and there is no
path from a link someone shares in Discord to a file I actually hold.

#### Goal

A Discord bot that accepts a URL from Instagram, YouTube, Reddit, or TikTok and privately
returns the media behind it to the requesting user, as a Discord attachment when it fits
and as a time-limited download link when it does not.

#### In scope

**The download feature**
- A slash command that accepts a URL from Instagram, YouTube, Reddit, or TikTok.
- Video and image posts, including multi-image posts (Instagram carousels, Reddit galleries).
- Delivery via ephemeral response, visible only to the requester.
- Media larger than 50 MB is rejected. Below that, the bot attaches the file directly when it
  fits within the guild's Discord attachment limit, read at runtime from the guild's boost
  tier, and otherwise stores it in MinIO and returns a presigned URL.
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

**Admin portal**
- Limited to cookie file upload and nothing else.
- Gated to a single super admin.

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
- **An IAM-style role model.** The guild-scoped regular admin role is deferred. The schema
  should not preclude adding it, but nothing is built for it now.
- **Per-guild cookie files.**

#### Constraints

**Production host.** Debian, 2 GB RAM, 2 vCores. SSD holds bot data, HDD holds media.
PostgreSQL, MinIO, the bot, and the admin portal are all co-resident on that 2 GB, alongside
FFmpeg during a download. FFmpeg merging a long video is the memory and CPU spike in that set,
and there are only two cores.

**Python 3.12.**

**PostgreSQL accessed through SQLAlchemy, with Alembic for migrations.** The ORM and migration
tooling are fixed rather than open choices. Alembic manages schema evolution, so no schema
change lands outside a migration.

**Discord's attachment limit is not a constant.** It varies by guild boost tier, roughly 10 MB
unboosted, and must be read per guild at runtime rather than configured.

**Discord's interaction acknowledgement window is three seconds.** No download completes in
that time, so every download command must defer immediately and respond as a follow up.

**Extractor fragility.** yt-dlp breaks when the target platforms change their sites, and
cookies expire. Cookie rotation is ongoing maintenance, not a one-time setup, which is why
cookie upload is the one admin portal feature in scope.

**Terms of service.** Automated downloading from these platforms is against their terms. This
is accepted as a known risk for a personal deployment.

#### Open assumptions carried forward

1. Media above 50 MB is rejected with a message to the user, rather than always presigned.
2. Images follow the same size logic as video rather than always attaching, since a Reddit
   gallery can be large.

### Stage 2: Group into a theme

#### Theme

**The foundational platform for the bot, bounded by a single end-to-end media download path.**
Everything required to take a URL from a Discord slash command to a file in the requester's
hands, and nothing that path does not require.

#### Justification

This is one theme rather than two because none of the infrastructure is built speculatively:
the database, the object store, the container topology, the command sync strategy, the cookie
upload, and the test harness each exist because the download path cannot ship or be maintained
without them, so the capability and the foundation are the same body of work.

#### The theme as a Stage 3 test

Admitted: Alembic migrations, Makefile, README, the development and production bot split, the
cookie upload portal, the pytest harness.

Rejected: Prometheus metrics and Grafana, a Redis cache, voice client connection handling,
structured logging with correlation IDs, an IAM role model.

### Stage 3: Decompose into tickets

Strictly linear. Every ticket depends only on the one before it.

`1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11 -> 12 -> 13`

| # | Title | Type | Goal | Files |
| --- | --- | --- | --- | --- |
| 1 | Project skeleton and developer tooling | Feature | A Python 3.12 package that installs, lints, and runs an empty test suite via the Makefile. | 9 |
| 2 | Bot process, command registration, and container image | Feature | The bot connects to Discord and answers a trivial command, registering instantly in development and globally in production. | 9 |
| 3 | Database foundation and guild registration | Feature | PostgreSQL, SQLAlchemy, and Alembic are wired up, proven by the bot recording every guild it joins. | 11 |
| 4 | URL parsing and media metadata extraction | Feature | `/download <url>` reports what media sits behind a supported link, and resolves its true total size, without fetching it. | 10 |
| 5 | Cookie storage and extractor authentication | Feature | yt-dlp authenticates with stored cookies, so all four platforms extract rather than three. | 8 |
| 6 | Media fetch and Discord attachment delivery | Feature | Media within the guild's attachment limit is downloaded and delivered ephemerally as a file. | 8 |
| 7 | Per-user download concurrency lock | Feature | A user with a download in flight is refused a second one until the first finishes. | 6 |
| 8 | MinIO storage and presigned URL delivery | Feature | Media too large to attach is uploaded to MinIO and returned as a 24 hour presigned link. | 8 |
| 9 | Stored object expiry | Feature | Objects are deleted 24 hours after upload so the link and the object die together. | 6 |
| 10 | User-facing failure handling | Feature | Every way a download can fail produces a clear ephemeral message instead of a traceback or silence. | 7 |
| 11 | Admin portal with super admin cookie upload | Feature | A super admin can replace cookie files through a web page rather than a Makefile target. | 10 |
| 12 | Regression coverage | Feature | The delivered path is covered by pytest well enough that a change breaking it fails the suite. | 7 |
| 13 | README and deployment documentation | Feature | The README explains what the bot is, and the deployment notes explain how to run it on the Debian host. | 4 |

#### Decisions embedded in this ordering

- **Cookies land at 5, immediately after extraction.** Instagram does not extract without them, so
  shipping ticket 4 before cookies would claim four platforms while only three worked. Cookies are
  stored on the SSD or in PostgreSQL, not in MinIO, because Stage 1 puts bot data on the SSD.
- **The concurrency lock lands at 7, after the fetch rather than before it.** At that position it
  guards a real multi-second download and can be demonstrated naturally. The accepted cost is that
  between tickets 6 and 7 a user can issue concurrent downloads.
- **Failure handling is its own ticket at 10**, after every failure surface exists, so the messages
  are designed as one coherent set.
- **Ticket 6 owns the temp file decision:** where downloaded bytes land before being attached or
  uploaded, and when they are cleaned up.
- **Ticket 3 is knowingly at the eleven file ceiling.** Alembic generates four files before any
  schema exists, and splitting the plumbing from the guild registration that consumes it would
  create a ticket with no consumer.

#### Size policy

The 50 MB cap applies per post, not per file.

Ticket 4 resolves the true total size before any bytes are fetched: yt-dlp metadata first, then an
HTTP HEAD (or a ranged GET where HEAD is rejected) against the direct media URLs, summed across all
entries of a multi-image post. If the total exceeds 50 MB the post is refused. If the size still
cannot be determined, for example a segmented HLS or DASH format, the post is refused.

Ticket 6 trusts ticket 4's answer and does not re-check.

### Stage 4: Ticket detail

Tooling decision inherited by every ticket: **uv** for dependency management, committed `uv.lock`,
`uv sync --frozen` in Docker builds.

---

#### Ticket 1: Project skeleton and developer tooling

**Goal.** A Python 3.12 package that installs, lints, and runs an empty test suite via the Makefile.

| File | Purpose |
| --- | --- |
| `pyproject.toml` | Single manifest: package metadata, `requires-python = ">=3.12,<3.13"`, runtime and dev dependencies, and Ruff / pytest / pytest-asyncio configuration in `[tool.*]` sections. The upper Python bound makes the Stage 1 version constraint enforceable at install time rather than a convention. |
| `uv.lock` | Resolved dependency graph, committed, so a build on the Debian host matches a build on the development machine. Generated. |
| `Makefile` | The deliverable of this ticket and the interface every later ticket extends (`migrate` in 3, `load-cookies` in 5, `coverage` in 12). Recipe lines are tabs; `.PHONY` is required because `test` collides with the directory name. |
| `src/criwin/__init__.py` | Establishes the src layout. Tests then run against installed code rather than the working directory, which is what makes ticket 12's suite trustworthy. |
| `src/criwin/config.py` | Typed settings from the environment via `pydantic-settings`, validated at boot. The seam every later ticket extends. Carries `environment: Literal["development", "production"]` from day one because ticket 2's sync strategy branches on it. |
| `.env.example` | Committed documentation of which variables exist, with no real values. Grows with every ticket that adds a setting. |
| `.gitignore` | Keeps `.env`, `.venv`, `__pycache__`, and the later temp download directory out of the repository. Highest-consequence file in the ticket: without it you commit the bot token. |
| `tests/conftest.py` | Roots the suite and hosts the fixtures that tickets 3, 6, and 12 add. |
| `tests/test_config.py` | Proves the suite runs and `Settings` loads. A suite with zero tests passes vacuously. |
| `README.md` | Stub naming the project and listing Make targets. Ticket 13 owns the real content. |

**Done when.** `make install`, `make lint`, and `make test` succeed on a clean checkout, and `make test` reports one passing test rather than zero collected.

---

#### Ticket 2: Bot process, command registration, and container image

**Goal.** The bot connects to Discord and answers a trivial command, registering instantly in development and globally in production.

**Concepts.** `discord.ext.commands.Bot` owns a `CommandTree` that holds application (slash) commands. Async startup work belongs in `setup_hook`, which runs after login and before the gateway connection is ready. `tree.sync()` with no argument registers globally, and `tree.sync(guild=...)` registers to one guild instantly; `tree.copy_global_to(guild=...)` is what puts the globally defined commands into that guild first. Slash commands need no privileged intents, so `Intents.default()` is sufficient and the message content intent is not required.

| File | Purpose |
| --- | --- |
| `src/criwin/config.py` (edit) | Adds `discord_token` and `development_guild_id`. |
| `src/criwin/bot.py` | The `Bot` subclass. `setup_hook` loads command modules and applies the sync strategy chosen by `environment`. |
| `src/criwin/__main__.py` | Entrypoint, so `python -m criwin` runs the bot and the container has a stable command. |
| `src/criwin/commands/__init__.py` | Command module registry, so later tickets add a command without editing `bot.py`. |
| `src/criwin/commands/ping.py` | A trivial command whose only job is to prove registration and sync work. Throwaway by design. |
| `docker/bot.Dockerfile` | `python:3.12-slim` base, uv install, `uv sync --frozen`. FFmpeg is added in ticket 4 when yt-dlp needs it. |
| `docker-compose.yml` | Bot service only. Later tickets add PostgreSQL (3), MinIO (8), and the portal (11) alongside the code that consumes each. |
| `.env.example` (edit) | Documents the token and development guild ID. |
| `Makefile` (edit) | `run`, `docker-build`, `docker-up`. |
| `tests/test_sync.py` | Asserts that the development branch syncs to a guild and the production branch does not, using a fake tree. |

**Mechanic worth knowing.** Do not sync on every production startup. Global command registration is rate limited, and a bot that restarts frequently will hit that limit. Production should sync only when commands actually change, ideally behind an explicit flag or an owner-only command. Development syncing per guild on every boot is fine.

**Done when.** The development bot appears online and `/ping` responds within seconds of a restart. The production bot connects without issuing a global sync.

---

#### Ticket 3: Database foundation and guild registration

**Goal.** PostgreSQL, SQLAlchemy, and Alembic are wired up, proven by the bot recording every guild it joins.

**Concepts.** SQLAlchemy 2.0 async requires an async driver (`asyncpg`) and the `sqlalchemy[asyncio]` extra. Alembic compares your `DeclarativeBase.metadata` against the live database to autogenerate migrations, which is why `migrations/env.py` must import the models and read the database URL from the environment rather than from `alembic.ini`.

| File | Purpose |
| --- | --- |
| `pyproject.toml` (edit) | Adds `sqlalchemy[asyncio]`, `asyncpg`, `alembic`. |
| `src/criwin/config.py` (edit) | Adds `database_url`. |
| `src/criwin/db/base.py` | The `DeclarativeBase` whose metadata Alembic diffs against. |
| `src/criwin/db/session.py` | Async engine and session factory, with a context manager later tickets use to open a session per command invocation. |
| `src/criwin/models/guild.py` | The `Guild` table: Discord guild ID, name, joined timestamp. The consumer that keeps this ticket from being pure plumbing. |
| `alembic.ini` | Alembic configuration, with the URL deliberately left out so it comes from the environment. |
| `migrations/env.py` | Points Alembic at the metadata and the runtime URL. Always requires hand editing after `alembic init`. |
| `migrations/script.py.mako` | Migration template. Generated. |
| `migrations/versions/0001_create_guild.py` | First migration. |
| `src/criwin/bot.py` (edit) | Upserts guild rows on `on_ready` and `on_guild_join`, which is the multi-guild support from Stage 1 made real. |
| `docker-compose.yml` (edit) | PostgreSQL service with its volume on the SSD, per the Stage 1 disk split. |
| `Makefile` (edit) | `migrate` and `revision` targets. |
| `tests/test_guild_registration.py` | Asserts a join writes a row and a re-join does not duplicate it. |

**Sizing.** Twelve files, over the ten file guideline, two of them Alembic boilerplate. Left whole deliberately: splitting the plumbing from the guild registration produces a ticket with no consumer, which the Stage 2 theme forbids. If it runs long in review, the seam is between the Alembic setup and `models/guild.py`.

**Done when.** `make migrate` creates the schema, and joining the bot to a fresh server writes exactly one row.

---

#### Ticket 4: URL parsing and media metadata extraction

**Goal.** `/download <url>` reports what media sits behind a supported link, and resolves its true total size, without fetching it.

**Concepts.** `yt_dlp.YoutubeDL.extract_info(url, download=False)` returns a metadata dictionary without fetching media: title, extractor name, `formats`, `filesize` or `filesize_approx`, and an `entries` list for multi-image posts. Where those size fields are absent, an HTTP HEAD against the direct media URL returns `Content-Length`; where a server rejects HEAD, a ranged GET of a single byte returns the total in `Content-Range`.

| File | Purpose |
| --- | --- |
| `pyproject.toml` (edit) | Adds `yt-dlp` and `httpx`. |
| `src/criwin/media/platforms.py` | Domain allowlist for the four supported platforms, so an unsupported URL is rejected before yt-dlp is invoked. |
| `src/criwin/media/types.py` | `MediaItem` and `MediaPost` shapes, so the rest of the codebase never handles yt-dlp's raw dictionary. |
| `src/criwin/media/extractor.py` | The yt-dlp wrapper. Normalizes single posts and carousels into one `MediaPost` shape. |
| `src/criwin/media/sizing.py` | Resolves true total size: yt-dlp fields first, then HEAD, then ranged GET, summed across every entry. Applies the 50 MB per-post gate and the refuse-when-unknown rule. |
| `src/criwin/commands/download.py` | The `/download` command. Defers ephemerally, extracts, and reports title, item count, resolved size, and whether the post is accepted. |
| `docker/bot.Dockerfile` (edit) | Installs FFmpeg, which `python:3.12-slim` does not include and yt-dlp requires. |
| `src/criwin/config.py` (edit) | Adds `max_post_bytes`, defaulting to 50 MB. |
| `tests/test_platforms.py` | Allowlist behavior for supported and unsupported hosts. |
| `tests/test_sizing.py` | The size resolution ladder, including the unknown case that must refuse. |
| `tests/test_extractor.py` | Normalization of a single video and a carousel, against recorded metadata fixtures. |

**Mechanic worth knowing.** yt-dlp is synchronous and blocking. Calling it directly inside a discord.py coroutine stalls the event loop, which stops the bot answering anything and eventually causes gateway heartbeat timeouts and a disconnect. Every yt-dlp call must go through `asyncio.to_thread` or a dedicated executor. This applies to extraction here and to the fetch in ticket 6.

**Sizing.** Eleven files, marginally over. The natural split, if needed, is `sizing.py` and its test into a separate ticket, since size resolution is genuinely independent of extraction.

**Done when.** `/download` on a YouTube, Reddit, and TikTok link reports accurate metadata and size, an oversized post is refused, and an unmeasurable post is refused. Instagram is expected to fail here; ticket 5 fixes it.

---

#### Ticket 5: Cookie storage and extractor authentication

**Goal.** yt-dlp authenticates with stored cookies, so all four platforms extract rather than three.

**Concepts.** yt-dlp reads cookies from a Netscape-format text file passed as its `cookiefile` option. Cookies expire, so replacing them is routine maintenance rather than one-time setup.

**Storage decision.** Cookie contents live in PostgreSQL, not MinIO and not a bind-mounted file. Stage 1 puts bot data on the SSD, which PostgreSQL already occupies, and ticket 11's portal runs in a separate container, so a shared database row is the only storage both processes can reach without coupling them to the same host filesystem.

| File | Purpose |
| --- | --- |
| `src/criwin/models/cookie_file.py` | One row per platform: platform name, cookie content, updated timestamp. Global rather than per guild, per Stage 1. |
| `migrations/versions/0002_create_cookie_file.py` | Schema for the above. |
| `src/criwin/media/cookies.py` | Reads the row and materializes it to a temporary file with `0600` permissions for the duration of one extraction, then removes it. |
| `src/criwin/media/extractor.py` (edit) | Passes `cookiefile` when a cookie exists for the platform being extracted. |
| `src/criwin/config.py` (edit) | Temp directory for materialized cookies, on the SSD. |
| `scripts/load_cookies.py` | Loads a cookie file from disk into the database, so the feature is usable before ticket 11 exists. |
| `Makefile` (edit) | `load-cookies` target wrapping that script. |
| `tests/test_cookies.py` | Materialization, permissions, and cleanup, including cleanup when extraction raises. |
| `tests/test_extractor.py` (edit) | Asserts `cookiefile` is passed when a cookie exists and omitted when it does not. |

**Done when.** An Instagram post that failed in ticket 4 extracts successfully after `make load-cookies`.

---

#### Ticket 6: Media fetch and Discord attachment delivery

**Goal.** Media within the guild's attachment limit is downloaded and delivered ephemerally as a file.

**Concepts.** `discord.Guild.filesize_limit` gives the guild's upload ceiling in bytes directly, so there is no need to derive it from `premium_tier`. Files are sent as `discord.File` objects through `interaction.followup.send(files=[...], ephemeral=True)`, since the interaction was already deferred.

| File | Purpose |
| --- | --- |
| `src/criwin/media/downloader.py` | Fetches bytes with yt-dlp into a per-job temp directory, through `asyncio.to_thread`, and guarantees the directory is removed on both success and failure. |
| `src/criwin/discord/limits.py` | Reads `guild.filesize_limit` and decides attach versus defer-to-storage, with the ticket 8 branch stubbed until then. |
| `src/criwin/commands/download.py` (edit) | Wires extraction to fetch to delivery. |
| `src/criwin/config.py` (edit) | Temp media directory, on the HDD per the Stage 1 disk split. |
| `docker-compose.yml` (edit) | Mounts the HDD path into the bot container. |
| `tests/test_downloader.py` | Fetch and temp directory cleanup, including cleanup on error. |
| `tests/test_limits.py` | The attach versus link decision across guild tiers. |
| `tests/test_download_command.py` (edit) | End to end with a faked downloader. |

**Mechanic worth knowing.** Discord allows at most ten attachments per message. A carousel of twelve images cannot be delivered in one follow up, so delivery must either split across several follow up messages or fall back to storage. This ticket owns that decision.

**Done when.** A small TikTok video and a three image Reddit gallery both arrive as ephemeral attachments, and the temp directory is empty afterward.

---

#### Ticket 7: Per-user download concurrency lock

**Goal.** A user with a download in flight is refused a second one until the first finishes.

| File | Purpose |
| --- | --- |
| `src/criwin/models/download_job.py` | Job rows with user ID, status, and started timestamp, plus a unique partial index over active jobs per user. |
| `migrations/versions/0003_create_download_job.py` | Schema and the partial index. |
| `src/criwin/services/job_lock.py` | Acquire, release, and reclaim jobs left active by a crash. |
| `src/criwin/commands/download.py` (edit) | Acquires before the fetch and releases in a `finally`. |
| `tests/test_job_lock.py` | Acquire, contention, release, and stale reclamation. |
| `tests/test_download_concurrency.py` | A second command during an in-flight download is refused. |

**Design note.** The lock is in the database rather than in process memory. A single bot process would be served by an in-memory set, but the deferred clones idea implies multiple processes, and an in-memory lock does not survive a restart, which leaks a permanent block on whichever user was mid-download. The unique partial index makes the constraint the database's job, so two racing commands cannot both acquire.

**Done when.** Two `/download` commands issued in quick succession result in one download and one refusal, and killing the bot mid-download does not leave the user permanently blocked.

---

#### Ticket 8: MinIO storage and presigned URL delivery

**Goal.** Media too large to attach is uploaded to MinIO and returned as a 24 hour presigned link.

| File | Purpose |
| --- | --- |
| `pyproject.toml` (edit) | Adds `minio`. |
| `src/criwin/config.py` (edit) | Internal endpoint, public endpoint, credentials, bucket name. |
| `src/criwin/storage/client.py` | Bucket creation, upload, and `presigned_get_object` with a 24 hour expiry. |
| `src/criwin/commands/download.py` (edit) | Takes the storage branch when the file exceeds the guild limit. |
| `docker-compose.yml` (edit) | MinIO service with its data volume on the HDD. |
| `.env.example` (edit) | Documents the new settings. |
| `Makefile` (edit) | Target to bring MinIO up and create the bucket. |
| `tests/test_storage.py` | Upload, presign, and that the generated URL uses the public endpoint. |

**Mechanic worth knowing.** A presigned URL embeds the endpoint hostname it was generated against. Generated against the Compose service name, it produces `http://minio:9000/...`, which resolves only inside the Docker network and is a dead link for the user. MinIO's client must be configured so that signing happens against the externally reachable hostname. This is the single most likely way this ticket ships broken while passing its own tests.

**Done when.** A file exceeding the guild's attachment limit returns a link that opens from a browser outside the Docker host.

---

#### Ticket 9: Stored object expiry

**Goal.** Objects are deleted 24 hours after upload so the link and the object die together.

| File | Purpose |
| --- | --- |
| `src/criwin/models/stored_object.py` | Object key, created and expiry timestamps. |
| `migrations/versions/0004_create_stored_object.py` | Schema. |
| `src/criwin/tasks/cleanup.py` | A periodic loop that deletes expired objects from MinIO and their rows. |
| `src/criwin/storage/client.py` (edit) | Adds object removal. |
| `src/criwin/bot.py` (edit) | Starts and stops the loop with the bot lifecycle. |
| `tests/test_cleanup.py` | Expired objects are removed, unexpired ones are not, and a MinIO failure does not kill the loop. |

**Why a task and not a lifecycle rule.** S3 and MinIO lifecycle expiration is day granular, so it cannot express a 24 hour deadline measured from upload time. `discord.ext.tasks.loop` runs the sweep inside the existing bot process, which avoids adding a scheduler container to a 2 GB host.

**Done when.** An object uploaded with a backdated expiry is gone after one sweep, and its database row with it.

---

#### Ticket 10: User-facing failure handling

**Goal.** Every way a download can fail produces a clear ephemeral message instead of a traceback or silence.

| File | Purpose |
| --- | --- |
| `src/criwin/errors.py` | Typed exceptions: unsupported platform, size unknown, too large, extraction failed, authentication required, download already in progress. |
| `src/criwin/media/extractor.py` (edit) | Maps yt-dlp's `DownloadError` text onto typed errors, distinguishing a private post from an expired cookie from a genuine extractor break. |
| `src/criwin/media/sizing.py` (edit) | Raises the typed size errors rather than returning sentinels. |
| `src/criwin/commands/download.py` (edit) | One handler mapping each error to its user-facing message. |
| `src/criwin/bot.py` (edit) | `CommandTree.on_error` catches anything unmapped so the user always gets a response. |
| `tests/test_errors.py` | yt-dlp error text maps to the right typed error. |
| `tests/test_error_messages.py` | Every typed error produces a distinct ephemeral message. |

**Why this matters more than it looks.** Stage 1 accepts extractor breakage as ongoing maintenance, which means these messages are your diagnostic surface. In particular, "too large" and "size could not be determined" must read differently, otherwise you cannot tell whether the refuse-on-unknown policy is rejecting too much. An unhandled exception after a defer leaves the user with Discord's generic failure text and leaves you with nothing.

**Done when.** A private Instagram post, an expired cookie, an unsupported host, an oversized post, and an unmeasurable post each produce a different, specific message.

---

#### Ticket 11: Admin portal with super admin cookie upload

**Goal.** A super admin can replace cookie files through a web page rather than a Makefile target.

**Scope reminder.** Cookie upload only. No server select element, since cookies are global. No sound management, since the soundboard is deferred. No role model, since the portal is gated to one super admin.

| File | Purpose |
| --- | --- |
| `pyproject.toml` (edit) | Adds `fastapi`, `uvicorn`, `jinja2`, `python-multipart`. |
| `portal/app.py` | Application factory and startup. |
| `portal/auth.py` | Single super admin credential check from configuration. |
| `portal/routes/cookies.py` | Upload form and handler, writing the same `cookie_file` rows ticket 5 defined. |
| `portal/templates/base.html` | Shared layout. |
| `portal/templates/cookies.html` | Per platform upload form showing each cookie's last update time. |
| `docker/portal.Dockerfile` | Separate image from the bot. |
| `docker-compose.yml` (edit) | Portal service, sharing the database and nothing else. |
| `src/criwin/config.py` (edit) | Admin credentials and portal bind address. |
| `tests/test_portal_auth.py` | Unauthenticated requests are rejected. |
| `tests/test_cookie_upload.py` | An upload replaces the row and the bot reads the new value. |

**Why this works without shared volumes.** Ticket 5 put cookie contents in PostgreSQL specifically so the portal and the bot could be separate containers. The portal writes a row; the bot reads it on the next extraction. There is no file handoff and no restart required.

**Done when.** Uploading a fresh Instagram cookie through the portal makes a previously failing extraction succeed without restarting the bot.

---

#### Ticket 12: Regression coverage

**Goal.** The delivered path is covered by pytest well enough that a change breaking it fails the suite.

| File | Purpose |
| --- | --- |
| `tests/fakes/discord.py` | Fake interaction, guild, and follow up, so command tests need no gateway. |
| `tests/fakes/ytdlp.py` | Recorded metadata fixtures for each of the four platforms, including a carousel. |
| `tests/fakes/storage.py` | In-memory object store standing in for MinIO. |
| `tests/test_end_to_end.py` | The full path: command to extraction to size gate to fetch to delivery, for the attach branch and the link branch. |
| `tests/conftest.py` (edit) | Registers the fakes as fixtures. |
| `pyproject.toml` (edit) | Coverage configuration and a failure threshold. |
| `Makefile` (edit) | `coverage` target. |

**Note on ordering.** Stage 1 asked for tests after the features were built. Each ticket above carries its own tests instead, and this ticket fills the gaps and adds the end to end path. Deferring all testing to here would mean retrofitting coverage across eleven merged tickets, and the concurrency lock in particular is far easier to verify with a test than by hand in Discord.

**Done when.** `make coverage` passes the threshold, and deliberately breaking the size gate fails the suite.

---

#### Ticket 13: README and deployment documentation

**Goal.** The README explains what the bot is, and the deployment notes explain how to run it on the Debian host.

| File | Purpose |
| --- | --- |
| `README.md` | Replaces the ticket 1 stub: what the bot does, supported platforms, the size and expiry rules, and local setup. |
| `docs/deployment.md` | The Debian host: the SSD and HDD volume split, Compose bring-up order, migration on deploy, and the fact that production global command sync is deliberate rather than automatic. |
| `docs/configuration.md` | Every environment variable, its default, and which component reads it. |
| `Makefile` (edit) | A production bring-up target matching the deployment document. |

**Done when.** A clean Debian host can be brought to a working bot using only these documents.

---

### Stage 5: PR summaries

Each body is deliberately short. The reasoning lives in the Stage 4 ticket, which every PR
references rather than repeats.

---

**1. Project skeleton and developer tooling**

Sets up the `criwin` package: `pyproject.toml` with a `>=3.12,<3.13` bound, uv with a committed
lockfile, Ruff and pytest configured in-manifest, a typed `Settings` class, and a Makefile with
`install`, `lint`, and `test`.

This is the base every later ticket builds on, so the conventions chosen here (src layout,
uv, settings from the environment) are the ones worth arguing about now rather than at ticket 8.

Look hardest at: the Python upper bound, which makes the version constraint enforceable rather
than aspirational, and `.gitignore` covering `.env` before any token exists to leak.

Verified by: `make install`, `make lint`, and `make test` on a clean checkout, with one test
collected and passing.

---

**2. Bot process, command registration, and container image**

Adds the `Bot` subclass, the `python -m criwin` entrypoint, a throwaway `/ping` command, the bot
Dockerfile, and a Compose file with the bot service. Command sync branches on `environment`:
development copies globals into the configured guild and syncs instantly, production does not
sync on boot.

Look hardest at: the production sync path. Global command registration is rate limited, so
syncing on every restart will eventually get the bot throttled. Production sync is deliberate,
not automatic, and the Stage 1 "waits an hour" behavior is Discord's propagation delay rather
than anything this code implements.

Verified by: the development bot answering `/ping` within seconds of a restart, and the
production bot connecting without issuing a global sync.

---

**3. Database foundation and guild registration**

Wires up PostgreSQL with SQLAlchemy 2.0 async and `asyncpg`, initializes Alembic against the
declarative metadata, adds the `guild` table, and upserts a row on `on_ready` and `on_guild_join`.
Adds the PostgreSQL service with its volume on the SSD.

Twelve files, over the usual size guideline. Splitting the Alembic plumbing from the guild model
would leave a PR with nothing consuming it, so it is left whole.

Look hardest at: `migrations/env.py`, which must import the models and read the database URL from
the environment rather than from `alembic.ini`, and the upsert path, which has to be idempotent
because `on_ready` fires again after a reconnect.

Verified by: `make migrate` creating the schema, and a fresh server join writing exactly one row
across repeated reconnects.

---

**4. URL parsing and media metadata extraction**

Adds `/download <url>`. Rejects unsupported hosts against an allowlist, extracts metadata with
yt-dlp without fetching media, normalizes single posts and carousels into one shape, and resolves
the true total post size via yt-dlp fields, then HTTP HEAD, then a ranged GET. Posts over 50 MB
are refused, and so are posts whose size cannot be determined.

Look hardest at: the `asyncio.to_thread` boundary. yt-dlp is synchronous, and calling it inline
stalls the event loop until the gateway heartbeat times out and the bot disconnects. Also worth
scrutiny is the size ladder, since `filesize` is frequently absent and only `filesize_approx`
is present.

Verified by: accurate metadata and size for YouTube, Reddit, and TikTok links, refusal of an
oversized post, and refusal of a segmented format whose size is unmeasurable. Instagram is
expected to fail here and is fixed in ticket 5.

---

**5. Cookie storage and extractor authentication**

Stores one Netscape-format cookie file per platform in PostgreSQL, materializes it to a
`0600` temp file for the duration of an extraction, and passes it to yt-dlp as `cookiefile`.
Adds `make load-cookies` so the feature is usable before the portal exists.

Cookies live in the database rather than MinIO or a bind mount so that ticket 11's portal, which
runs in a separate container, can write them without a shared filesystem.

Look hardest at: temp file cleanup on the failure path, since a leaked cookie file is a leaked
credential, and the permission bits on that file.

Verified by: an Instagram post that failed in ticket 4 extracting successfully after
`make load-cookies`.

---

**6. Media fetch and Discord attachment delivery**

Downloads accepted posts into a per-job temp directory on the HDD and delivers them as ephemeral
attachments when they fit `guild.filesize_limit`. Carousels exceeding Discord's ten attachment
per message cap are split across follow ups.

Look hardest at: temp directory cleanup, which must happen on the error path as well as the happy
path, and the `to_thread` boundary again for the fetch itself. The attachment cap is easy to miss
because it only bites on larger carousels.

Verified by: a small TikTok video and a three image Reddit gallery arriving as ephemeral
attachments, with the temp directory empty afterward.

---

**7. Per-user download concurrency lock**

Adds a `download_job` table with a unique partial index over active jobs per user, acquired before
the fetch and released in a `finally`. Jobs left active by a crash are reclaimed after a timeout.

The lock is in the database rather than in process memory: an in-memory lock does not survive a
restart, which would permanently block whichever user was mid-download, and the deferred clones
idea implies more than one process eventually.

Look hardest at: the partial index, which is what makes two racing commands unable to both
acquire, and the reclamation timeout, which is the difference between a crash costing one download
and costing a user their access.

Verified by: two rapid `/download` commands producing one download and one refusal, and a
mid-download kill not leaving the user blocked.

---

**8. MinIO storage and presigned URL delivery**

Uploads media exceeding the guild attachment limit to MinIO and returns a 24 hour presigned URL.
Adds the MinIO service with its data volume on the HDD.

Look hardest at: the endpoint configuration. A presigned URL embeds the host it was signed
against, so signing against the Compose service name produces `http://minio:9000/...`, which
resolves only inside the Docker network and is a dead link for every user. Internal and public
endpoints are configured separately for exactly this reason, and this is the one defect that
passes its own tests.

Verified by: an oversized file returning a link that opens from a browser outside the Docker host.

---

**9. Stored object expiry**

Tracks uploaded objects with an expiry timestamp and sweeps them from MinIO on a periodic
`discord.ext.tasks` loop, so the object and its 24 hour link die together.

An S3 lifecycle rule cannot express this: expiration is day granular and cannot be measured from
upload time. Running the sweep inside the bot process avoids adding a scheduler container to a
2 GB host.

Look hardest at: loop resilience. A MinIO error during a sweep must not kill the task, or expiry
silently stops and the HDD fills.

Verified by: an object with a backdated expiry, and its row, both gone after one sweep.

---

**10. User-facing failure handling**

Introduces a typed error hierarchy, maps yt-dlp's `DownloadError` text onto it, and gives each
error a distinct ephemeral message. Adds a `CommandTree.on_error` catch-all so an unmapped
exception never leaves the user with Discord's generic failure text.

Stage 1 accepts extractor breakage as ongoing maintenance, which makes these messages the primary
diagnostic surface.

Look hardest at: the distinction between "too large" and "size could not be determined." They are
the same refusal to a user but completely different signals to you, and collapsing them makes it
impossible to tell whether the refuse-on-unknown policy is rejecting too much.

Verified by: a private Instagram post, an expired cookie, an unsupported host, an oversized post,
and an unmeasurable post each producing a different message.

---

**11. Admin portal with super admin cookie upload**

Adds a FastAPI portal in its own container and image, gated to a single super admin, with one
page: per platform cookie upload showing each cookie's last update time. It writes the same rows
ticket 5 defined, so the bot picks up a new cookie on its next extraction with no restart and no
shared volume.

Scope is cookie upload only. No server select element, because cookies are global. No sound
management, because the soundboard is deferred. No role model, because there is one admin.

Look hardest at: the authentication check, since this is the only externally reachable component
in the stack, and the bind address in Compose.

Verified by: uploading a fresh Instagram cookie through the portal making a previously failing
extraction succeed without a restart.

---

**12. Regression coverage**

Adds shared fakes for Discord, yt-dlp, and object storage, an end to end test covering the
command through extraction, the size gate, fetch, and both delivery branches, plus coverage
configuration and a `make coverage` target.

Note that tests were written per ticket rather than deferred wholesale to this one. Retrofitting
coverage across eleven merged tickets produces worse tests, and the concurrency lock in particular
is far easier to verify with a test than by hand in Discord. This PR fills gaps and adds the
end to end path.

Look hardest at: whether the fakes are faithful. A fake that accepts what the real API rejects
gives false confidence, which is worse than no test.

Verified by: `make coverage` passing its threshold, and a deliberate break of the size gate
failing the suite.

---

**13. README and deployment documentation**

Replaces the ticket 1 README stub with real content, and adds deployment and configuration
documents covering the Debian host, the SSD and HDD volume split, Compose bring-up order,
migration on deploy, and the deliberate production command sync.

Look hardest at: whether the deployment document is actually sufficient. The test is a clean host,
not a familiar one.

Verified by: bringing a clean Debian host to a working bot using only these documents.
