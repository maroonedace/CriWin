"""Alembic environment.

Autogenerate diffs the live database against ``Base.metadata``, so the declarative
models in ``src.services.db.models`` are what drive migrations.

This file deliberately contains no baselining logic: it runs for every online
Alembic command, so stamping here would mean ``alembic current`` silently mutated
the database it was asked to report on. That lives in ``src/services/db/migrate.py``.
"""

from logging.config import fileConfig

from alembic import context

from src.services.db import database_url, get_engine
from src.services.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Column types are load-bearing here (REAL vs FLOAT(24), BIGINT vs BIGSERIAL), so type
# comparison stays on. This is Alembic's default since 1.12; it is stated explicitly
# because a type mismatch surfaces as a phantom diff rather than as an error.
#
# compare_server_default stays OFF: Postgres normalises DEFAULT CURRENT_TIMESTAMP to
# now() and '{}' to '{}'::bigint[], which autogenerate would then report as
# differences on every single run.
COMPARE_OPTIONS = {"compare_type": True}


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to a database."""
    context.configure(
        url=database_url().render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **COMPARE_OPTIONS,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the configured database."""
    with get_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, **COMPARE_OPTIONS)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
