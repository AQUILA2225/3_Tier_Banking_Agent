from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, pool, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from tests.integration.db_config import TestDatabaseSettings


BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:

    settings = TestDatabaseSettings()

    engine = create_engine(
        settings.database_url,
        poolclass=pool.NullPool,
        hide_parameters=True
    )

    try:
        with engine.begin() as connection:

            database_name, database_user = connection.execute(
                text("select current_database(), current_user")
            ).one()

            if (
                database_name != "banking_agent_test_db"
                or database_user != "banking_test_app"
            ):
                raise RuntimeError(
                    "Integration tests connected to an unsafe database."
                )

            alembic_config = Config(
                str(BACKEND_DIR / "alembic.ini")
            )

            alembic_config.set_main_option(
                "script_location",
                str(BACKEND_DIR / "alembic")
            )

            alembic_config.attributes["connection"] = connection

            command.upgrade(alembic_config, "head")

        yield engine

    finally:
        engine.dispose()


@pytest.fixture
def db_session(
    test_engine: Engine
) -> Generator[Session, None, None]:

    with test_engine.connect() as connection:

        transaction = connection.begin()

        session = Session(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint"
        )

        try:
            yield session

        finally:
            session.close()

            if transaction.is_active:
                transaction.rollback()