# Production deployment checklist

## Secrets and connection security

- Store `DATABASE_URL` in the deployment platform's secret manager.
- Use the `warehouse_app` role for runtime reports and updates.
- Use `warehouse_migrator` only from a controlled migration job.
- Require TLS with `sslmode=verify-full` and a managed CA bundle in production.
- Never put passwords in committed files, logs, command history, or CI output.
- Keep production and test databases on separate hosts or databases.

Example shape only:

```text
postgresql://warehouse_app:<secret>@db.example.com:5432/warehouse?sslmode=verify-full
```

## Network and database access

- Restrict PostgreSQL ingress to application and migration networks.
- Do not expose PostgreSQL directly to the public internet.
- Use firewall/security-group rules and rotate credentials regularly.
- Confirm the runtime role cannot create schemas, alter tables, or run migrations.
- Apply the audit-owner section of `sql/security_roles.sql` so audit trigger
  functions are owned by the non-login `warehouse_audit_owner` role.
- Ensure the runtime role cannot insert, update, delete, or truncate audit
  history, and treat `database_user` as the authoritative database identity;
  `app.user` is supplemental application attribution.
- Review `sql/security_roles.sql` before applying it to a shared database.

## Backups and recovery

- Take a backup before every migration or audit-retention deletion.
- Test restoring a backup into an isolated PostgreSQL instance.
- Record backup age, restore result, and migration version.
- Keep enough audit-history retention to meet operational and compliance needs.

## Deployment order

1. Provision or rotate secrets in the secret manager.
2. Verify network access using the runtime role.
3. Back up the database.
4. Run `.venv/bin/python migrate.py` with the migration role.
5. Run smoke tests using the runtime role.
6. Monitor `alert=report_failure` logs and database health metrics.
