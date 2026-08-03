"""reconcile legacy schema

Replays the backfill statements the retired init.sql carried below its CREATE TABLEs.
Those only ever ran when a database volume was first created, so a long-lived
deployment can still be missing the volume/guild_id columns, or still carry the old
single-row soundboard_panel table and the global sounds_name_key constraint.

Every statement is idempotent and a no-op against a database created by revision
0001, which is what makes it safe to run after stamping a pre-Alembic database.
Leaving these out would strand that legacy shape in the database, where autogenerate
would report it as pending "drop this" work on every future run.

DDL only. The data fix for sounds parked in guild 0 stays a documented manual step
(see the README) -- a migration should not guess which guild those rows belong to.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-02

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Bring a pre-Alembic database up to the shape revision 0001 creates."""
    op.execute("ALTER TABLE sounds ADD COLUMN IF NOT EXISTS volume REAL NOT NULL DEFAULT 1.0")
    op.execute("ALTER TABLE sounds ADD COLUMN IF NOT EXISTS guild_id BIGINT NOT NULL DEFAULT 0")
    # init.sql added guild_id with a default so the backfill could run; 0001 creates
    # the column without one. Converge on 0001 so the two never diverge.
    op.execute("ALTER TABLE sounds ALTER COLUMN guild_id DROP DEFAULT")
    # Display names used to be globally unique; they are now unique per guild.
    op.execute("ALTER TABLE sounds DROP CONSTRAINT IF EXISTS sounds_name_key")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS sounds_guild_name_key ON sounds (guild_id, name)")
    # The old single-row panel table, replaced by per-guild soundboard_panels.
    op.execute("DROP TABLE IF EXISTS soundboard_panel")


def downgrade() -> None:
    """Nothing here is safely reversible: these are one-way reconciliations."""
