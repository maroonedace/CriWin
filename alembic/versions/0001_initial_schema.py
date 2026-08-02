"""initial schema

The schema as it stood when Alembic took over, matching what the retired init.sql
produced. Databases that predate Alembic already have this and are stamped at this
revision rather than running it -- see src/services/db/migrate.py.

Revision ID: 0001
Revises:
Create Date: 2026-08-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "guilds",
        sa.Column("guild_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True
        ),
        sa.PrimaryKeyConstraint("guild_id"),
    )
    op.create_table(
        "soundboard_access",
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("guild_id", "role_id"),
    )
    op.create_table(
        "soundboard_panels",
        sa.Column("guild_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "message_ids",
            postgresql.ARRAY(sa.BigInteger()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True
        ),
        sa.PrimaryKeyConstraint("guild_id"),
    )
    op.create_table(
        "sounds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("volume", sa.REAL(), server_default=sa.text("1.0"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("sounds_guild_name_key", "sounds", ["guild_id", "name"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("sounds_guild_name_key", table_name="sounds")
    op.drop_table("sounds")
    op.drop_table("soundboard_panels")
    op.drop_table("soundboard_access")
    op.drop_table("guilds")
