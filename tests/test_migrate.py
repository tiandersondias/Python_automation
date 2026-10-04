import pytest

import migrate


def test_discover_migrations_in_numeric_order():
    migrations = migrate.discover_migrations()

    assert [version for version, _ in migrations] == [
        "001",
        "002",
        "003",
        "004",
        "005",
        "006",
    ]


def test_invalid_migration_name_is_rejected(monkeypatch, tmp_path):
    bad_migration = tmp_path / "bad-name.sql"
    bad_migration.write_text("SELECT 1")
    with pytest.raises(ValueError, match="invalid migration filename"):
        migrate.discover_migrations(tmp_path)


def test_all_migrations_are_discovered_in_order():
    assert [version for version, _ in migrate.discover_migrations()] == [
        "001",
        "002",
        "003",
        "004",
        "005",
        "006",
    ]


def test_migration_checksum_is_sha256(tmp_path):
    migration = tmp_path / "001_initial.sql"
    migration.write_bytes(b"SELECT 1;\n")

    assert migrate.migration_checksum(migration) == (
        "b4e0497804e46e0a0b0b8c31975b062152d551bac49c3c2e80932567b4085dcd"
    )
