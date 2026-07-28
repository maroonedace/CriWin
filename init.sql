CREATE TABLE IF NOT EXISTS sounds (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    file_name VARCHAR(255) NOT NULL,
    volume REAL NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Backfill for databases created before the volume column existed.
ALTER TABLE sounds ADD COLUMN IF NOT EXISTS volume REAL NOT NULL DEFAULT 1.0;
