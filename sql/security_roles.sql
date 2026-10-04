-- Apply as a PostgreSQL administrator after replacing role names.
-- Supply passwords interactively or through a secret manager; do not commit
-- passwords to this file or shell history.
CREATE ROLE warehouse_app LOGIN;
CREATE ROLE warehouse_migrator LOGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'warehouse_audit_owner') THEN
        CREATE ROLE warehouse_audit_owner NOLOGIN;
    END IF;
END
$$;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;

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
REVOKE INSERT, UPDATE, DELETE, TRUNCATE
    ON pick_line_status_history, stock_adjustment_history
    FROM warehouse_app;

-- The migration role owns schema changes. Keep it separate from the runtime
-- application role and use it only from a controlled deployment environment.
GRANT USAGE, CREATE ON SCHEMA public TO warehouse_migrator;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO warehouse_migrator;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO warehouse_migrator;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO warehouse_app;

-- The audit trigger functions run with this non-login owner, not the runtime
-- application role. The owner can append audit rows but cannot log in.
GRANT USAGE ON SCHEMA public TO warehouse_audit_owner;
GRANT INSERT ON pick_line_status_history, stock_adjustment_history
    TO warehouse_audit_owner;
ALTER FUNCTION record_pick_line_status_change()
    OWNER TO warehouse_audit_owner;
ALTER FUNCTION record_stock_adjustment()
    OWNER TO warehouse_audit_owner;
REVOKE ALL ON FUNCTION record_pick_line_status_change() FROM PUBLIC;
REVOKE ALL ON FUNCTION record_stock_adjustment() FROM PUBLIC;
