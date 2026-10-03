import os
import uuid

import psycopg
import pytest
from psycopg import sql

from migrate import apply_migrations


@pytest.fixture
def postgres_connection():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set TEST_DATABASE_URL to run PostgreSQL integration tests")

    schema_name = f"test_{uuid.uuid4().hex}"
    try:
        with psycopg.connect(database_url, autocommit=True) as admin_conn:
            admin_conn.execute(
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name))
            )

        with psycopg.connect(database_url) as conn:
            conn.execute(
                sql.SQL("SET search_path TO {}").format(sql.Identifier(schema_name))
            )
            apply_migrations(conn)
            yield conn
    finally:
        with psycopg.connect(database_url, autocommit=True) as admin_conn:
            admin_conn.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema_name))
            )
