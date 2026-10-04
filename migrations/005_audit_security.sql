ALTER TABLE pick_line_status_history
    ADD COLUMN database_user VARCHAR(63);

ALTER TABLE stock_adjustment_history
    ADD COLUMN database_user VARCHAR(63);

CREATE OR REPLACE FUNCTION record_pick_line_status_change()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        EXECUTE format(
            'INSERT INTO %I.pick_line_status_history
                (pick_line_id, old_status, new_status, changed_by, database_user)
             VALUES ($1, $2, $3, $4, $5)',
            TG_TABLE_SCHEMA
        )
        USING NEW.pick_line_id, OLD.status, NEW.status,
            current_setting('app.user', true), session_user;
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION record_stock_adjustment()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
BEGIN
    IF NEW.system_qty IS DISTINCT FROM OLD.system_qty THEN
        EXECUTE format(
            'INSERT INTO %I.stock_adjustment_history
                (sku, location_id, old_system_qty, new_system_qty,
                 changed_by, database_user)
             VALUES ($1, $2, $3, $4, $5, $6)',
            TG_TABLE_SCHEMA
        )
        USING NEW.sku, NEW.location_id, OLD.system_qty, NEW.system_qty,
            current_setting('app.user', true), session_user;
    END IF;
    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION record_pick_line_status_change() FROM PUBLIC;
REVOKE ALL ON FUNCTION record_stock_adjustment() FROM PUBLIC;
