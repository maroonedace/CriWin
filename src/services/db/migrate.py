"""Apply Alembic migrations, baselining a pre-Alembic database first.

Run as ``python -m src.services.db.migrate``; the compose ``migrate`` service is its
only caller in normal operation.

Databases created by the retired ``init.sql`` already have the revision-0001 schema
but no ``alembic_version`` table to say so, so a plain ``upgrade head`` would start
from scratch and fail on CREATE TABLE. Those are detected and stamped first. Both
steps are idempotent, so running this repeatedly is safe.

The check deliberately lives here rather than in ``alembic/env.py``, which runs for
every online Alembic command -- putting it there would mean ``alembic current`` and
``alembic heads`` silently stamped production.
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import inspect

from src.services.db import get_engine

logger = logging.getLogger(__name__)

# src/services/db/migrate.py -> src/services/db -> src/services -> src -> repo root
ALEMBIC_INI = Path(__file__).resolve().parents[3] / "alembic.ini"

# The revision whose schema a database built by the old init.sql already has.
BASELINE_REVISION = "0001"


def needs_baseline() -> bool:
    """True for a pre-Alembic database: it has our tables but no version table."""
    with get_engine().connect() as connection:
        tables = set(inspect(connection).get_table_names())
    return "alembic_version" not in tables and "sounds" in tables


def main() -> None:
    """Stamp a pre-Alembic database if needed, then upgrade to head."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    config = AlembicConfig(str(ALEMBIC_INI))

    if needs_baseline():
        logger.info(
            "Database predates Alembic; stamping revision %s before upgrading",
            BASELINE_REVISION,
        )
        command.stamp(config, BASELINE_REVISION)

    logger.info("Upgrading database to head")
    command.upgrade(config, "head")
    logger.info("Database is up to date")


if __name__ == "__main__":
    main()
