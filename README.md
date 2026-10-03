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

Initialize a new database with:

```bash
psql "$DATABASE_URL" -f sql/schema.sql
```

## Utilities

```bash
.venv/bin/python reorder_point.py
.venv/bin/python batch_picking.py
```

`reorder_point.py` reads `daily_demand` and each SKU's `lead_time_days`.
`batch_picking.py` produces a walking-order plan for open pick lines using
warehouse location and `pick_sequence`.

The SQL reports can be run directly with `psql`:

```bash
psql "$DATABASE_URL" -f sql/abc_slotting.sql
psql "$DATABASE_URL" -f sql/batch_picking_by_zone.sql
psql "$DATABASE_URL" -f sql/inventory_accuracy_checks.sql
```

ABC slotting uses completed (`PICKED`) lines from the last 90 days. Inventory
accuracy uses the latest cycle count for each SKU/location pair.

## Tests

```bash
.venv/bin/python -m pytest
```

The PostgreSQL integration test is skipped unless `TEST_DATABASE_URL` is set.
Use a disposable test database rather than the production database:

```bash
export TEST_DATABASE_URL="postgresql://user:password@localhost/warehouse_test"
.venv/bin/python -m pytest tests/test_postgres_integration.py -q
```

The integration fixture creates and removes an isolated PostgreSQL schema,
applies `sql/schema.sql`, and validates the SQL reports and Python query
functions against PostgreSQL.
