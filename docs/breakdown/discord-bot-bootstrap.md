# Breakdown: discord-bot-bootstrap

Started: 2026-08-03
Theme: A running discord.py bot, provable and deployable.

## Stages
- [x] 1. Frame the scope
- [x] 2. Group into a theme
- [x] 3. Decompose into tickets
- [x] 4. Flesh out each ticket
- [x] 5. PR summaries

## Artifacts

### Stage 1: Frame the scope

#### Problem statement

There is currently no running Discord bot process for this project. Every later capability
depends on a live bot connection, a container it can run in, and a way to prove during
development that a deployed change actually works. None of that exists yet.

#### Goal

A discord.py bot written for Python 3.12, packaged as a Docker image, that connects to Discord
under either a development or a production configuration and answers a `/ping` command with
`pong` to confirm it is running.

#### In scope

- A minimal discord.py bot process (Python 3.12) that logs in and stays connected to the
  Discord gateway.
- A single slash command, `/ping`, returning `pong`. No other commands.
- A Dockerfile that builds the bot into a runnable container image.
- Two distinct runtime configurations, development and production, distinguished at minimum by
  which bot token or application is used and by how the slash command is registered
  (guild-scoped instant sync for development, global sync for production).
- The minimal environment-variable configuration needed to select between the two (bot token,
  an environment flag, and a guild ID for development-scoped sync).

#### Out of scope

- Any command beyond `/ping`.
- A database of any kind.
- Object or file storage of any kind.
- Deployment orchestration beyond a single Dockerfile: no Compose file, no Kubernetes, no
  CI/CD pipeline, unless stated otherwise later.
- Any feature-level bot behavior. Nothing tied to the media-download plan in the existing
  `criwin-discord-bot` breakdown.

#### Constraints

- Python 3.12.
- Must run inside a Docker container.
- discord.py's own sync mechanics are an inherited constraint, not a design choice:
  guild-scoped sync registers instantly, global sync can take up to an hour to propagate, which
  is why the dev/prod split has to touch command registration and not just configuration
  values.
- No constraint stated on target host, timeline, or where the container is ultimately
  deployed ("none specified").

### Stage 2: Group into a theme

#### Theme

**A running discord.py bot, provable and deployable.** The minimum set of things required to
take this project from no bot process to a bot that connects, answers `/ping`, builds into a
container image, and can be pointed at either a development or a production Discord
application.

#### Justification

Every candidate ticket in Stage 1's scope exists only to make the bot demonstrably alive in
both environments: the bot process itself, the `/ping` command that proves the connection
works, the Dockerfile that makes it runnable, and the dev/prod split that determines which
application it connects as and how commands register. None of these pieces has independent
value without the others, so they form one theme rather than several.

#### The theme as a Stage 3 test

Admitted: the bot skeleton, dependency and tooling setup, the `/ping` command, the Dockerfile,
environment-based configuration, dev-guild-scoped versus global command sync.

Rejected: anything from Stage 1's out-of-scope list (a database, object storage, additional
commands), and anything not needed to prove the bot is alive (CI/CD pipelines, Compose
orchestration, logging infrastructure).

### Stage 3: Decompose into tickets

Linear. Ticket 2 depends on ticket 1.

`1 -> 2`

| # | Title | Type | Goal | Files |
| --- | --- | --- | --- | --- |
| 1 | Bot skeleton, environment configuration, and `/ping` command | Feature | A Python 3.12 discord.py bot connects to Discord, reads dev/prod configuration from the environment, and answers `/ping` with `pong`, syncing commands instantly in development and globally in production. | 7 |
| 2 | Docker image | Feature | The ticket 1 bot builds into a runnable Docker image and behaves identically to running it directly, in both the development and production configuration. | 3 |

#### Decisions embedded in this ordering

- **Two tickets, not one.** The bot's Python code and its container packaging are reviewable
  independently: a reviewer can validate the bot's logic and command sync behavior without
  also reasoning about the Dockerfile, and vice versa. They are kept separate rather than
  merged for size padding, since ticket 2 alone is well under the ten-file guideline.
- **The dev/prod split lives entirely in ticket 1, not as its own ticket.** It is not a
  separable capability. It touches the same handful of files (configuration and the bot's
  startup hook) that ticket 1 already owns, and splitting it out would produce a ticket with
  no independent consumer.
- **Ticket 2 is deliberately small.** Three files is below the usual floor worth worrying
  about, but the theme from Stage 2 treats "deployable" as a first-class half of the goal, not
  an afterthought folded into ticket 1, so it earns its own PR and its own done-when check.

### Stage 4: Ticket detail

---

#### Ticket 1: Bot skeleton, environment configuration, and `/ping` command

**Goal.** A Python 3.12 discord.py bot connects to Discord, reads dev/prod configuration from the environment, and answers `/ping` with `pong`, syncing commands instantly in development and globally in production.

**Concepts.** `discord.ext.commands.Bot` owns a `CommandTree` that holds slash commands. Asynchronous startup work belongs in `setup_hook`, which runs once after login and before the gateway connection reports ready. `tree.sync()` with no argument registers commands globally and can take up to an hour to propagate to users. `tree.sync(guild=discord.Object(id=...))` registers to one guild only and is visible within seconds, which is what makes it usable for development. Slash commands require no privileged intents, so `discord.Intents.default()` is enough; the message-content intent, which does require privileged access, is not needed anywhere in this ticket.

| File | Purpose |
| --- | --- |
| `requirements.txt` | Pins `discord.py` and `python-dotenv`. `python-dotenv` is the one addition beyond the bare minimum, so `.env` can be loaded in development without exporting variables by hand; production is expected to supply real environment variables directly. |
| `.env.example` | Documents the three variables this ticket introduces: `DISCORD_TOKEN`, `ENVIRONMENT` (`development` or `production`), and `DEV_GUILD_ID`. No real values. |
| `.gitignore` | Excludes `.env`, `__pycache__/`, and `.venv/`. Written before any token exists to leak. |
| `bot/config.py` | A small `Settings` object that reads the three environment variables, raises immediately if `DISCORD_TOKEN` is missing, and exposes `is_development` as the single branch point the sync logic reads. |
| `bot/client.py` | The `Bot` subclass. `setup_hook` registers the `/ping` command and calls the sync strategy: guild-scoped sync when `settings.is_development` is true, global sync otherwise. |
| `bot/commands/ping.py` | The `/ping` command, returning `pong`. The only command in this ticket, and, per Stage 1, the only command in this breakdown. |
| `bot/__main__.py` | Entry point. Loads `.env` (a no-op in production, where the file will not exist), builds `Settings`, constructs the `Bot`, and calls `bot.run(settings.discord_token)`. Gives the project a stable run command: `python -m bot`. |

**Mechanic worth knowing.** Do not call `tree.sync()` (the global form) on every startup. Global sync is rate-limited by Discord, and a production process that restarts frequently will eventually get throttled. This ticket's production path syncs once in `setup_hook` on boot, which is acceptable at this scope, but if the bot later restarts often in production, that call should move behind an explicit trigger rather than firing on every boot. Worth flagging now even though fixing it is out of scope for this ticket.

**Naming note.** A flat `bot/` package is used rather than a `src/` layout, since there is no packaging or distribution requirement in scope, and no `pyproject.toml` build backend, since this is not being published anywhere.

**Done when.** Running `python -m bot` with `ENVIRONMENT=development` connects the bot and `/ping` responds with `pong` in the configured dev guild within seconds of startup. Running it with `ENVIRONMENT=production` connects the bot and issues a global sync instead of a guild-scoped one.

---

#### Ticket 2: Docker image

**Goal.** The ticket 1 bot builds into a runnable Docker image and behaves identically to running it directly, in both the development and production configuration.

**Concepts.** A single-stage `python:3.12-slim` base is enough here, since `requirements.txt` has exactly two dependencies and there is no compiled extension to build. The image itself carries no environment-specific values; `ENVIRONMENT`, `DISCORD_TOKEN`, and `DEV_GUILD_ID` are supplied at `docker run` time, which is what makes one image usable for both configurations from Stage 1 rather than requiring two separate builds.

| File | Purpose |
| --- | --- |
| `Dockerfile` | `python:3.12-slim` base. Copies `requirements.txt` first and installs it, then copies the `bot/` package, so the dependency layer caches independently of code changes. `CMD ["python", "-m", "bot"]` matches ticket 1's entry point exactly, so there is no divergence between the containerized command and the one used for local runs. |
| `.dockerignore` | Excludes `.env`, `.git`, `__pycache__/`, and `.venv/` from the build context. Without this, a local `.env` containing a real token could be baked into an image layer. |
| `README.md` | Documents the two `docker run` invocations, development and production, each passing the three environment variables from ticket 1 at run time rather than baking them into the image. This is the only place those commands are written down, since this breakdown has no Makefile in scope. |

**Mechanic worth knowing.** Do not `COPY .env` into the image, and do not pass a token through a build-time `ARG`, since `docker history` can expose build arguments after the fact. Both environments' `DISCORD_TOKEN` must reach the container only through `docker run -e` or an orchestrator's secret mechanism, never through the image itself.

**Done when.** `docker build` succeeds, and `docker run` with the development environment variables produces the same guild-scoped `/ping` behavior ticket 1 verified directly, with no code or dependency changes between the two.

---

### Stage 5: PR summaries

---

**1. Bot skeleton, environment configuration, and `/ping` command**

Adds a Python 3.12 discord.py bot: a `Bot` subclass, environment-based `Settings` (token,
environment flag, dev guild ID), a `/ping` command, and a `python -m bot` entry point. Command
sync branches on `ENVIRONMENT`: development syncs to a single guild instantly, production
syncs globally.

Look hardest at: the sync branch in `setup_hook`, since a bot that syncs globally on every
restart will eventually get rate limited by Discord, and at `.gitignore` covering `.env`
before any token exists to leak.

Verified by: `/ping` responding with `pong` within seconds of a development restart, and a
production run issuing a global sync rather than a guild-scoped one.

---

**2. Docker image**

Adds a `Dockerfile` and `.dockerignore` that package the ticket 1 bot into a single image, with
`CMD ["python", "-m", "bot"]` matching the local entry point exactly. All three environment
variables are supplied at `docker run` time rather than baked into the image, so one image
serves both the development and production configuration. A `README.md` documents both
invocations.

Look hardest at: the `.dockerignore` entry for `.env`, since without it a local token can end
up baked into an image layer, and confirm no build-time `ARG` is used to pass the token.

Verified by: `docker build` succeeding, and `docker run` with the development environment
variables reproducing the same guild-scoped `/ping` behavior verified directly in ticket 1.

---
