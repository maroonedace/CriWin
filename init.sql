CREATE TABLE IF NOT EXISTS sounds (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    file_name VARCHAR(255) NOT NULL,
    volume REAL NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Backfill for databases created before the volume column existed.
ALTER TABLE sounds ADD COLUMN IF NOT EXISTS volume REAL NOT NULL DEFAULT 1.0;

-- Tracks the soundboard button panel so the hourly sync can update its message(s).
-- Single row (id = 1); message_ids holds one Discord message id per panel message.
CREATE TABLE IF NOT EXISTS soundboard_panel (
    id INTEGER PRIMARY KEY DEFAULT 1,
    channel_id BIGINT NOT NULL,
    message_ids BIGINT[] NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT soundboard_panel_single_row CHECK (id = 1)
);

-- Roles allowed to use the soundboard button panel, per guild. With no rows for a
-- guild the panel is open to everyone; otherwise a member needs one of these roles.
CREATE TABLE IF NOT EXISTS soundboard_access (
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY (guild_id, role_id)
);
