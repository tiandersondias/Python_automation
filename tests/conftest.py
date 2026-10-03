import os
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import sql


@pytest.fixture
def postgres_connection():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set TEST_DATABASE_URL to run PostgreSQL integration tests")

    schema_name = f"test_{uuid.uuid4().hex}"
    schema_sql = (Path(__file__).resolve().parents[1] / "sql" / "schema.sql").read_text()

    try:
        with psycopg.connect(database_url, autocommit=True) as admin_conn:
            admin_conn.execute(
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name))
            )

        with psycopg.connect(database_url) as conn:
            conn.execute(
                sql.SQL("SET search_path TO {}").format(sql.Identifier(schema_name))
            )
            conn.execute(schema_sql)
            yield conn
    finally:
        with psycopg.connect(database_url, autocommit=True) as admin_conn:
            admin_conn.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema_name))
            )
