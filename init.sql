-- A sound belongs to exactly one guild: only that guild's panel shows it, and only
-- its members can play it. Display names are unique per guild, not globally.
CREATE TABLE IF NOT EXISTS sounds (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    volume REAL NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Backfill for databases created before the volume column existed.
ALTER TABLE sounds ADD COLUMN IF NOT EXISTS volume REAL NOT NULL DEFAULT 1.0;

-- Backfill for databases created before sounds were guild-scoped. Existing rows land
-- in guild 0; point them at the real guild before use (see README, "Migrating an
-- existing database"), then the unique index below applies per guild.
ALTER TABLE sounds ADD COLUMN IF NOT EXISTS guild_id BIGINT NOT NULL DEFAULT 0;
ALTER TABLE sounds DROP CONSTRAINT IF EXISTS sounds_name_key;
CREATE UNIQUE INDEX IF NOT EXISTS sounds_guild_name_key ON sounds (guild_id, name);

-- Tracks each guild's soundboard button panel so the hourly sync can update its
-- message(s); message_ids holds one Discord message id per panel message. Replaces
-- the old single-row soundboard_panel table, which let one guild's setup clobber
-- another's — guilds with a panel there must re-run /soundboard-panel.
DROP TABLE IF EXISTS soundboard_panel;

CREATE TABLE IF NOT EXISTS soundboard_panels (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    message_ids BIGINT[] NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Guilds the bot is in, refreshed by the bot on ready/join. The admin web panel has
-- no Discord token, so this table is where it gets its server list from.
CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Roles allowed to use the soundboard button panel, per guild. With no rows for a
-- guild the panel is open to everyone; otherwise a member needs one of these roles.
CREATE TABLE IF NOT EXISTS soundboard_access (
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY (guild_id, role_id)
);
