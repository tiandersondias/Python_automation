# Database migrations

Versioned PostgreSQL migrations are stored in `migrations/` and are applied in
numeric filename order. The current schema is defined by `001_initial.sql` followed by
`002_data_quality_constraints.sql`, `003_audit_history.sql`,
`004_validate_data_quality_constraints.sql`, and `005_audit_security.sql`.
Write-time data-quality enforcement is added by `006_write_data_quality.sql`.
The audit tables and triggers are added by `003_audit_history.sql`; audit
database-user attribution and trigger hardening are added by
`005_audit_security.sql`.
The migration files are the single source of truth. `sql/schema.sql` is only a
`psql` compatibility entry point that includes those files in order; do not
edit it to add schema objects.

## Applying migrations

For a new database, apply every migration:

```bash
.venv/bin/python migrate.py
```

`migrate.py` creates `schema_migrations`, applies pending files in numeric
order, records each successful migration and its SHA-256 checksum, and commits
the complete run as one transaction. It rejects edits to an already-applied
migration, verifies the recorded filename, and takes a PostgreSQL advisory
transaction lock so concurrent deployments serialize safely. Every future
migration must be a new, forward-only file such as
`004_add_column.sql`; do not edit a migration that may already have been
applied.

Existing databases created before checksum tracking may have a null checksum.
The first successful runner invocation records the checksum of each matching
applied file as a compatibility baseline. Review the migration files and
database state before accepting that baseline; future edits are rejected.

Migration `002_data_quality_constraints.sql` intentionally adds its checks as
`NOT VALID` so existing databases can be upgraded without an immediate table
scan. Before applying migration 004 to an existing database, run:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/data_quality_checks.sql
```

Repair every reported row, then run `.venv/bin/python migrate.py` again.
Migration 004 validates the constraints and will fail atomically if invalid
legacy data remains.

## Rollback

Before applying a migration, take a database backup. Rollbacks are performed
with a reviewed, forward corrective migration rather than editing or deleting
an applied migration. For local disposable databases, drop and recreate the
database, then reapply all migration files.

## Security

Apply `sql/security_roles.sql` as an administrator after reviewing the
privileges for the deployment. Use separate runtime and migration credentials,
keep passwords in a secret manager, and do not commit credentials to SQL files,
environment examples, logs, or shell history.
The security role script creates a non-login `warehouse_audit_owner` role,
removes public schema creation, and transfers ownership of the `SECURITY
DEFINER` audit functions. The audit records retain both the application actor
(`app.user`) and the authenticated PostgreSQL session user; `app.user` remains
application-supplied and must not be treated as compliance-grade identity by
itself.
See [DEPLOYMENT.md](DEPLOYMENT.md) for TLS, network restrictions, backup, and
restore requirements.

## Audit retention and alerts

Audit tables are not deleted automatically. Review
`sql/audit_retention.sql`, back up the database, run a dry-run count, and only
then invoke `purge_audit_history()` with an explicit cutoff. Route
`alert=report_failure` log records to the deployment monitoring system.
