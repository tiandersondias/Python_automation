import argparse
import os
import re
import sys
from pathlib import Path

import psycopg

MIGRATION_PATTERN = re.compile(r"^(?P<version>\d+)_(?P<name>[a-z0-9_]+)\.sql$")
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def discover_migrations(
    migrations_dir: Path = MIGRATIONS_DIR,
) -> list[tuple[str, Path]]:
    migrations = []
    for path in migrations_dir.glob("*.sql"):
        match = MIGRATION_PATTERN.fullmatch(path.name)
        if not match:
            raise ValueError(
                f"invalid migration filename {path.name!r}; expected NNN_name.sql"
            )
        migrations.append((match.group("version"), path))

    migrations.sort(key=lambda item: int(item[0]))
    versions = [version for version, _ in migrations]
    if len(versions) != len(set(versions)):
        raise ValueError("duplicate migration version detected")
    return migrations


def acquire_migration_lock(conn: psycopg.Connection) -> None:
    conn.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_KEY,))


MIGRATION_LOCK_KEY = 914_2026


def apply_migrations(
    conn: psycopg.Connection, *, migrations_dir: Path = MIGRATIONS_DIR
) -> list[str]:
    migrations = discover_migrations(migrations_dir)
    acquire_migration_lock(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(100) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT now()
        )
        """
    )
    applied = {
        row[0]
        for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }
    applied_versions = {int(version) for version in applied}
    pending = []

    for version, path in migrations:
        numeric_version = int(version)
        if version in applied:
            continue
        if any(previous > numeric_version for previous in applied_versions):
            raise RuntimeError(
                f"migration {path.name} is out of order; "
                "a newer migration is already applied"
            )
        conn.execute(path.read_text())
        conn.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
            (version, path.name),
        )
        pending.append(path.name)

    conn.commit()
    return pending


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply pending PostgreSQL migrations.")
    parser.add_argument(
        "database_url",
        nargs="?",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL connection URL (default: DATABASE_URL environment variable)",
    )
    args = parser.parse_args()
    if not args.database_url:
        parser.error(
            "provide database_url or set the DATABASE_URL environment variable"
        )

    try:
        with psycopg.connect(args.database_url) as conn:
            applied = apply_migrations(conn)
    except (psycopg.Error, ValueError, RuntimeError) as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if applied:
        print("Applied migrations:")
        print("\n".join(f"- {name}" for name in applied))
    else:
        print("No pending migrations.")


if __name__ == "__main__":
    main()
