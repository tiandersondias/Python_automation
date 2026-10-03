-- Apply as a PostgreSQL administrator after replacing role names.
-- Supply passwords interactively or through a secret manager; do not commit
-- passwords to this file or shell history.
CREATE ROLE warehouse_app LOGIN;
CREATE ROLE warehouse_migrator LOGIN;

-- The application can read reporting data and update operational quantities,
-- but cannot change the schema or run migrations.
GRANT USAGE ON SCHEMA public TO warehouse_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO warehouse_app;
GRANT UPDATE (system_qty) ON stock TO warehouse_app;
GRANT UPDATE (
    status,
    pick_date,
    picked_by,
    picked_at,
    short_reason,
    short_qty
) ON pick_lines TO warehouse_app;

-- The migration role owns schema changes. Keep it separate from the runtime
-- application role and use it only from a controlled deployment environment.
GRANT USAGE, CREATE ON SCHEMA public TO warehouse_migrator;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO warehouse_migrator;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO warehouse_migrator;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO warehouse_app;

-- The audit trigger functions are SECURITY DEFINER and should be owned by a
-- role that can insert into the audit tables but is not used by the app.
