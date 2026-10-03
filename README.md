# Warehouse inventory utilities

This project contains PostgreSQL schema and reporting utilities for inventory
replenishment, ABC slotting, batch picking, and inventory accuracy.

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -r requirements-dev.txt
```

The project uses PostgreSQL. Set a connection URL before running the Python
utilities:

```bash
export DATABASE_URL="postgresql://user:password@localhost/warehouse"
```

Initialize a new database with the migration runner:

```bash
.venv/bin/python migrate.py
```

See [MIGRATIONS.md](MIGRATIONS.md) for migration and rollback procedures.
See [DEPLOYMENT.md](DEPLOYMENT.md) for production TLS, roles, network,
backup, and recovery guidance.
Migration safety tests cover rollback of failed migrations and rejection of
out-of-order files; run the PostgreSQL integration suite to exercise them.
For a disposable database or a direct `psql` workflow, the compatibility
entry point `sql/schema.sql` includes the same versioned migrations in order.

## Utilities

```bash
.venv/bin/python reorder_point.py
.venv/bin/python batch_picking.py
```

The utilities exit with status 1 and print an actionable message if
PostgreSQL is unavailable or the required tables have not been migrated.
Connection URLs and credentials are not included in error messages.

`reorder_point.py` reads `daily_demand` and each SKU's `lead_time_days`.
`batch_picking.py` produces a walking-order plan for open pick lines using
warehouse location and `pick_sequence`.

Both utilities support `--output-format table|csv|json`. Reorder points also
support `--service-level-z`, which must be greater than zero:

```bash
.venv/bin/python reorder_point.py --service-level-z 1.96 --output-format csv
.venv/bin/python batch_picking.py --output-format json
```

Batch picking uses a default capacity of 100 units, assigns complete orders
greedily without splitting them, and accepts a custom capacity:

```bash
.venv/bin/python batch_picking.py --max-units 250
```

The ABC report currently uses completed picks from the last 90 days and an
80% cumulative threshold. Change those report parameters through a reviewed
SQL migration or a future parameterized report wrapper rather than embedding
credentials or ad-hoc SQL in shell history.

The SQL reports can be run directly with `psql`:

```bash
psql "$DATABASE_URL" -f sql/abc_slotting.sql
psql "$DATABASE_URL" -f sql/batch_picking_by_zone.sql
psql "$DATABASE_URL" -f sql/inventory_accuracy_checks.sql
```

ABC slotting uses completed (`PICKED`) lines from the last 90 days. Inventory
accuracy uses the latest cycle count for each SKU/location pair.
`SHORT` pick lines require a reason and a positive short quantity not exceeding
the requested quantity. Run `sql/data_quality_checks.sql` to review legacy
records that need cleanup.

The CLI utilities log report parameters, UTC generation timestamps, and
failure categories to stderr without logging database URLs or credentials.
Migration `003_audit_history.sql` adds history tables and triggers for pick
status transitions and stock quantity changes. Applications can identify the
acting operator for these triggers with:

```sql
SELECT set_config('app.user', 'operator-id', true);
```

For production deployments, use separate PostgreSQL roles for runtime access
and migrations. Review and adapt `sql/security_roles.sql` as an administrator;
it intentionally contains no passwords. Store credentials in the deployment
secret manager, grant only the required schema/table privileges, and never use
the migration role as the application `DATABASE_URL`.

Audit history is retained by default. Review eligible rows with
`sql/audit_retention.sql`, then call `operations.purge_audit_history()` from a
controlled maintenance job with an explicit cutoff date. Use `dry_run=True`
first and take a verified backup before deletion. Report failures emit
`alert=report_failure` markers for log-based monitoring.

## Tests

```bash
.venv/bin/python -m pytest
.venv/bin/ruff format --check .
.venv/bin/ruff check .
```

PostgreSQL query results are converted through the project’s psycopg cursor
adapter in `database.py`, avoiding unsupported raw-connection warnings from
`pandas.read_sql_query`.

The PostgreSQL integration test is skipped unless `TEST_DATABASE_URL` is set.
Use a disposable test database rather than the production database:

```bash
export TEST_DATABASE_URL="postgresql://user:password@localhost/warehouse_test"
.venv/bin/python -m pytest tests/test_postgres_integration.py -q
```

The integration fixture creates and removes an isolated PostgreSQL schema,
applies `migrations/001_initial.sql`, and validates the SQL reports and Python query
functions against PostgreSQL.
