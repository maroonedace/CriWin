"""SQLAlchemy models: the single source of truth for the database schema.

Alembic diffs ``Base.metadata`` against the live database to autogenerate
migrations, so changing a column here is how a schema change starts. Every
definition mirrors what the retired ``init.sql`` produced, which is why a few
columns look more explicit than they need to be -- see the comments. Drift shows
up as a phantom diff on every future ``--autogenerate`` run rather than as an
error, so the details matter.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import ARRAY, REAL
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base. ``Base.metadata`` is Alembic's ``target_metadata``."""


class Sound(Base):
    """A sound belongs to exactly one guild: only that guild's panel shows it, and
    only its members can play it. Display names are unique per guild, not globally.
    """

    __tablename__ = "sounds"
    __table_args__ = (
        # A bare unique index, not a UniqueConstraint: Postgres records the latter in
        # pg_constraint and reflects the two differently, so a UniqueConstraint here
        # would make autogenerate want to swap them on every existing database.
        Index("sounds_guild_name_key", "guild_id", "name", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # add_sound() omits this column and lets the server default fill it in, so the
    # server_default is load-bearing rather than decorative.
    volume: Mapped[float] = mapped_column(REAL, nullable=False, server_default=text("1.0"))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class SoundboardPanel(Base):
    """Each guild's soundboard button panel, so the hourly sync can update its
    message(s); message_ids holds one Discord message id per panel message.
    """

    __tablename__ = "soundboard_panels"

    # autoincrement=False keeps this a plain BIGINT. A lone BigInteger primary key
    # otherwise renders as BIGSERIAL, creating a sequence init.sql never made.
    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), nullable=False, server_default=text("'{}'")
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class Guild(Base):
    """Guilds the bot is in, refreshed by the bot on ready/join. The admin web panel
    has no Discord token, so this table is where it gets its server list from.
    """

    __tablename__ = "guilds"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )


class SoundboardAccess(Base):
    """Roles allowed to use the soundboard button panel, per guild. With no rows for a
    guild the panel is open to everyone; otherwise a member needs one of these roles.
    """

    __tablename__ = "soundboard_access"

    # Composite primary key, so autoincrement never applies and needs no opting out.
    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
