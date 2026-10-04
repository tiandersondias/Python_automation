from pathlib import Path


def test_schema_entrypoint_includes_all_migrations_in_order():
    schema_sql = (
        Path(__file__).resolve().parents[1] / "sql" / "schema.sql"
    ).read_text()
    migration_names = [
        "001_initial.sql",
        "002_data_quality_constraints.sql",
        "003_audit_history.sql",
        "004_validate_data_quality_constraints.sql",
        "005_audit_security.sql",
        "006_write_data_quality.sql",
    ]
    positions = [schema_sql.index(name) for name in migration_names]

    assert positions == sorted(positions)
    assert schema_sql.count("\\ir") == len(migration_names)
