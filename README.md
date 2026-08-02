# Criwin
A Discord bot that lets users download short form videos and play audio on demand from platforms like YouTube, TikTok, Instagram, and Reddit.

## Tech Stack
![Python](https://shields.io/badge/Python-3776AB?logo=Python&logoColor=FFF)
![FastAPI](https://shields.io/badge/FastAPI-009485?logo=fastapi&logoColor=FFF)
![Postgres](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-257BD6?logo=docker&logoColor=white)
![MinIO](https://img.shields.io/badge/MinIO-C72E29?&logo=minio&logoColor=white)

## Features

### Short Form Content Downloads
Download videos and audio from popular platforms including YouTube, Reddit, Instagram, and TikTok, all through simple slash commands.

### Soundboard Audio Playback
Play audio clips on demand from a curated selection of sounds using the soundboard command, perfect for adding personality and fun to your voice channels.

## Slash Commands

| Command | Description |
|---|---|
| `/soundboard <sound_name>` | Join your voice channel and play a stored sound. |
| `/soundboard-add <sound_name> <sound_file>` | Upload a new sound to the soundboard. |
| `/soundboard-delete <sound_name>` | Remove a sound from the soundboard. |
| `/download-audio <url>` | Download the audio track from a URL and post it. |
| `/download-media <url>` | Download video or images from a URL and post them. |
| `/leave` | Disconnect the bot from your voice channel. |

## Architecture

Criwin is built on `discord.py` using **slash commands only** — it subclasses a
raw `discord.Client` with an `app_commands.CommandTree` (no cogs). The code is
organized into four layers, from the outside in:

| Layer | Location | Responsibility |
|---|---|---|
| **config** | `src/config.py` | Single source of truth for environment configuration. Calls `load_dotenv()` once and exposes `Config` + `validate_config()`. |
| **core** | `src/core/` | Cross-cutting helpers with no feature knowledge (e.g. `messaging.send_message`). |
| **events** | `src/events.py` | Gateway event handlers that aren't slash commands (e.g. the DM handler). |
| **services** | `src/services/` | Business and infrastructure logic with **no Discord command wiring** — the media download engine and the soundboard data layer. |
| **commands** | `src/commands/` | The Discord-facing layer: slash-command registration and handlers only. |

### Entry flow

```
main.py                     # bootstrap: logging, validate_config(), build & run the bot, signal handling
  └─ src/bot.py             # DiscordBot(discord.Client): builds the CommandTree
       ├─ setup_hook()      # → src/commands/setup.py: setup_commands(tree) → tree.sync()
       │    ├─ setup_soundboard(tree)
       │    ├─ setup_download(tree)
       │    └─ setup_leave(tree)
       └─ on_message()      # → src/events.py: handle_dm_message
```

### Command package convention

Every feature under `src/commands/<feature>/` follows the same shape:

- `__init__.py` — the registrar `setup_<feature>(tree)` that declares the slash commands.
- handler file(s) — one `handle_*` coroutine per command, holding the command logic.
- `constants.py` — user-facing message strings for that feature.

Handlers stay thin and delegate real work to the **services** layer.

### Services

- **`src/services/media/`** — framework-agnostic download/transcode engine
  (`downloader.py`: yt-dlp + gallery-dl + ffmpeg/Pillow conversions; `constants.py`:
  cookie maps, upload-size tiers, and yt-dlp option sets).
- **`src/services/db/`** — the database plumbing: `models.py` holds the SQLAlchemy
  models that define the schema, `__init__.py` the engine/session factory, and
  `migrate.py` the entry point that applies Alembic migrations.
- **`src/services/soundboard/`** — the soundboard data layer, split by concern:
  `repository.py` (PostgreSQL metadata), `storage.py` (S3/MinIO audio),
  `cache.py` (local playback cache), `errors.py`, and `service.py`
  which orchestrates them behind a small public API.

### Project layout

```
main.py                       # entry point / composition root
alembic.ini                   # Alembic configuration
alembic/
├── env.py                    # points autogenerate at the SQLAlchemy models
└── versions/                 # migration scripts, applied in order
src/
├── bot.py                    # DiscordBot client + command tree
├── config.py                 # central configuration + validation
├── events.py                 # non-command gateway events (DM handler)
├── core/
│   └── messaging.py          # send_message helper
├── services/
│   ├── db/                   # models (the schema), engine/session, migrate entrypoint
│   ├── media/                # download engine (downloader.py, constants.py)
│   └── soundboard/           # errors, repository, storage, cache, service
└── commands/
    ├── setup.py              # setup_commands: aggregates all feature registrars
    ├── soundboard/           # __init__ (registrar) + play/add/delete.py + constants.py
    ├── download/             # __init__ (registrar) + download_audio/media.py + constants.py
    └── leave/                # __init__ (registrar) + leave.py + constants.py
tests/                        # pytest suite
```

## Configuration

All configuration is read from environment variables (loaded from a `.env` file
in local development). Copy [`.env.example`](.env.example) to `.env` and fill in
the values:

- **Discord** — `DISCORD_TOKEN`, `GUILD_ID`
- **Logging** — `LOG_LEVEL`
- **Database** — `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- **Object storage** — `STORAGE_ENDPOINT`, `STORAGE_REGION`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_BUCKET_NAME`, `STORAGE_SECURE`
- **Media downloads** — `DOWNLOAD_DIR`, `COOKIE_DIR`
- **Admin panel** — `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_HOST`, `ADMIN_PORT`

## Running

### With Docker

Compose starts five services: `db` (PostgreSQL), `storage` (MinIO), `migrate` (a one-shot
that brings the database schema up to date and exits), `app` (the bot), and `admin` (the
web panel). `app` and `admin` wait for `migrate` to succeed, so a failed migration stops
the stack instead of letting the bot run against a schema it doesn't expect. All
configuration comes from the env file — the compose files only pass `${VARS}` through. So
for Docker your env file must point the app at the compose service names: set
`DB_HOST=db` and `STORAGE_ENDPOINT=storage:9000` (the `localhost` values in
`.env.example` are for non-Docker `python main.py` runs).

Configuration is split across three files so the same stack runs for local development
and on the production server:

- `docker-compose.yml` — shared base (prod-safe defaults; code baked into the image).
- `docker-compose.override.yml` — development only; **auto-loaded** by `docker compose up`.
  Bind-mounts `./src` and `./main.py` for live editing and exposes the DB / MinIO ports on
  loopback for debugging.
- `docker-compose.prod.yml` — production tuning; loaded **explicitly** with `-f`, which
  skips the dev override so source mounts never reach production.

**Development (macOS / Windows / Linux):**

```bash
docker compose up -d --build
```

Edit code, then `docker compose restart app admin` to pick up the change.

**Production (Debian server)** — put production values in `.env.prod`, then:

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Here the bot runs the code baked into the image (no source mounts); persistent state lives
in the `db_data` and `storage_data` volumes, and only the loopback admin port is published.

**Makefile shortcuts** — a [`Makefile`](Makefile) wraps these commands; run `make help` for
the full list. Common ones: `make up` / `make down` / `make logs` / `make restart` (dev),
and `make prod-up` / `make prod-down` / `make prod-logs` (prod). Point prod at a different
env file with `make prod-up PROD_ENV=.env.staging`. (On Windows, run `make` from WSL or Git
Bash, or use the `docker compose` commands above directly.)

### Admin panel

The `admin` service publishes on `${ADMIN_PUBLISH_HOST}:${ADMIN_PORT}`. Keep
`ADMIN_PUBLISH_HOST=127.0.0.1` (the default in `.env.example`) to bind the host loopback
only, so there is no public port — reach it over an SSH or Tailscale tunnel. Inside the
container uvicorn always binds `0.0.0.0` so the published port can reach it; the two are
separate on purpose. From your machine:

```bash
ssh -L 8080:localhost:8080 your-server
```

then open `http://localhost:8080` and sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD`
(both are required — the panel returns 401 until they match). From there
you can upload/delete sounds, set per-sound volume, and upload/replace the
yt-dlp/gallery-dl cookies.

Sounds belong to one server: pick it in the **Server** dropdown before uploading, and the
sound list shows only that server's sounds. The dropdown is populated from the `guilds`
table, which the bot fills in as it connects — so start the bot at least once before
uploading. Display names only need to be unique within a server.

### Locally

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in the values
python main.py
```

`ffmpeg` must be installed and on your `PATH` (used for audio playback and media conversion).

## Database migrations

The schema is defined by the SQLAlchemy models in
[`src/services/db/models.py`](src/services/db/models.py) — those are the source of
truth. [Alembic](https://alembic.sqlalchemy.org/) compares them against the live
database and writes the SQL to reconcile the two, so a schema change goes:

```bash
# 1. edit the model in src/services/db/models.py, then:
make revision m="add a description column to sounds"

# 2. READ the generated file in alembic/versions/ before committing it.
#    Autogenerate is a good first draft, not a finished migration — it does not
#    detect table or column renames, and it cannot know how to backfill data.

# 3. apply it
make migrate
```

`make migrate` also runs automatically as part of `make up`, via the one-shot `migrate`
compose service. Other targets: `make migrate-status` (current revision),
`make migrate-down` (roll back one), and `make prod-migrate` to migrate production on
its own before `make prod-up`.

A test in [`tests/test_migrations.py`](tests/test_migrations.py) fails if the migrations
and the models drift apart, so forgetting step 1 is caught in CI rather than in
production.

### Migrating an existing database

Databases created before Alembic — that is, by the old `init.sql` — are handled
automatically. On first run the `migrate` service notices the tables exist but the
Alembic version table doesn't, stamps the database at the initial revision, and applies
everything since. It is idempotent, so re-running it is safe. Take a `pg_dump` before
the first deploy anyway.

Two things Alembic will not do for you, because both need a human decision.

Sounds that predate guild scoping sit in guild `0`, where they are invisible to every
server. Point them at the right server:

```sql
UPDATE sounds SET guild_id = <your GUILD_ID> WHERE guild_id = 0;
```

And the old single-row `soundboard_panel` table is replaced by per-guild
`soundboard_panels`, so run `/soundboard-panel` again in each server to recreate its
panel; the messages the old panel left behind are no longer tracked and can be deleted
by hand.

## Tests

```bash
pytest
```

The repository and migration tests run against a real PostgreSQL database, because the
schema uses a Postgres `BIGINT[]` and `ON CONFLICT` that SQLite cannot stand in for.
Start one with `make test-db` (and `make test-db-stop` when you're done); without it
those tests skip locally. CI always runs them against a service container, and fails
rather than skipping if the database is missing.

Point them somewhere else with `TEST_DATABASE_URL`:

```bash
TEST_DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/criwin_test pytest
```
