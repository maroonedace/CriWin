# Criwin Discord Bot

A Discord bot built with discord.py on Python 3.12, packaged as a Docker image. Right now it
exposes a single command, `/ping`, which replies `Pong!`, used to confirm the bot is connected
and responding before anything else gets built on top of it.

## Environments

The bot reads an `ENVIRONMENT` variable and behaves differently depending on its value:

- **development** — slash commands sync to a single guild (`DEV_GUILD_ID`) and are available
  within seconds, for fast iteration.
- **production** — slash commands sync globally, which can take Discord up to an hour to
  propagate to users.

The same Docker image is used for both. Only the environment variables supplied at run time
change.

## Running with Docker Compose

1. Copy `.env.example` to `.env.development` and fill in a development bot token
   and guild ID.
2. Copy `.env.example` to `.env.production` and fill in a production bot token.
3. Start the bot:

   ```
   make dev    # development, runs in the foreground, rebuilds each time
   make prod   # production, runs detached
   ```

4. Stop it:

   ```
   make dev-down
   make prod-down
   ```

5. Tail logs for whichever environment is currently running:

   ```
   make logs
   ```

## Running without Docker

1. Copy `.env.example` to `.env` and fill in the values.
2. `pip install -r requirements.txt`
3. `python -m bot`
