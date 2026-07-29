# Criwin
A Discord bot that lets users download short form videos and play audio on demand from platforms like YouTube, TikTok, Instagram, and Reddit.

## Tech Stack
![Python](https://shields.io/badge/Python-3776AB?logo=Python&logoColor=FFF)
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
- **`src/services/soundboard/`** — the soundboard data layer, split by concern:
  `repository.py` (PostgreSQL metadata), `storage.py` (S3/MinIO audio),
  `cache.py` (local playback cache), `models.py`, `errors.py`, and `service.py`
  which orchestrates them behind a small public API.

### Project layout

```
main.py                       # entry point / composition root
src/
├── bot.py                    # DiscordBot client + command tree
├── config.py                 # central configuration + validation
├── events.py                 # non-command gateway events (DM handler)
├── core/
│   └── messaging.py          # send_message helper
├── services/
│   ├── media/                # download engine (downloader.py, constants.py)
│   └── soundboard/           # models, errors, repository, storage, cache, service
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
- **Object storage (S3 / MinIO)** — `STORAGE_ENDPOINT`, `STORAGE_REGION`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_BUCKET_NAME`, `STORAGE_SECURE`
- **Media downloads** — `DOWNLOAD_DIR`, `COOKIE_DIR`
- **Admin panel** — `ADMIN_PASSWORD`, `ADMIN_HOST`, `ADMIN_PORT`

## Running

### With Docker

`docker compose up` starts four services: `db` (PostgreSQL), `storage` (MinIO),
`app` (the bot), and `admin` (the web panel). The database schema is bootstrapped
from `init.sql`. Inside the compose network the app addresses the database at
`db:5432` and object storage at `storage:9000`.

### Admin panel

The `admin` service publishes only to the host loopback
(`127.0.0.1:${ADMIN_PORT}`), so there is no public port. Reach it over an SSH or
Tailscale tunnel — e.g. from your machine:

```bash
ssh -L 8080:localhost:8080 your-server
```

then open `http://localhost:8080` and sign in with `ADMIN_PASSWORD`. From there
you can upload/delete sounds, set per-sound volume, and upload/replace the
yt-dlp/gallery-dl cookies.

### Locally

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in the values
python main.py
```

`ffmpeg` must be installed and on your `PATH` (used for audio playback and media conversion).

## Tests

```bash
pytest
```
