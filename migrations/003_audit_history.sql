CREATE TABLE pick_line_status_history (
    history_id    BIGSERIAL PRIMARY KEY,
    pick_line_id  BIGINT NOT NULL REFERENCES pick_lines(pick_line_id),
    old_status    VARCHAR(15),
    new_status    VARCHAR(15) NOT NULL,
    changed_at    TIMESTAMP NOT NULL DEFAULT now(),
    changed_by    VARCHAR(30)
);

CREATE TABLE stock_adjustment_history (
    adjustment_id BIGSERIAL PRIMARY KEY,
    sku           VARCHAR(30) NOT NULL,
    location_id   VARCHAR(20) NOT NULL,
    old_system_qty INT NOT NULL,
    new_system_qty INT NOT NULL,
    changed_at    TIMESTAMP NOT NULL DEFAULT now(),
    changed_by    VARCHAR(30),
    FOREIGN KEY (sku, location_id) REFERENCES stock(sku, location_id)
);

CREATE INDEX idx_pick_line_status_history_line_time
    ON pick_line_status_history (pick_line_id, changed_at DESC);

CREATE INDEX idx_stock_adjustment_history_item_time
    ON stock_adjustment_history (sku, location_id, changed_at DESC);

CREATE OR REPLACE FUNCTION record_pick_line_status_change()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        EXECUTE format(
            'INSERT INTO %I.pick_line_status_history
                (pick_line_id, old_status, new_status, changed_by)
             VALUES ($1, $2, $3, $4)',
            TG_TABLE_SCHEMA
        )
        USING NEW.pick_line_id, OLD.status, NEW.status,
            current_setting('app.user', true);
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_pick_line_status_history
AFTER UPDATE OF status ON pick_lines
FOR EACH ROW
EXECUTE FUNCTION record_pick_line_status_change();

CREATE OR REPLACE FUNCTION record_stock_adjustment()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF NEW.system_qty IS DISTINCT FROM OLD.system_qty THEN
        EXECUTE format(
            'INSERT INTO %I.stock_adjustment_history
                (sku, location_id, old_system_qty, new_system_qty, changed_by)
             VALUES ($1, $2, $3, $4, $5)',
            TG_TABLE_SCHEMA
        )
        USING NEW.sku, NEW.location_id, OLD.system_qty, NEW.system_qty,
            current_setting('app.user', true);
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_stock_adjustment_history
AFTER UPDATE OF system_qty ON stock
FOR EACH ROW
EXECUTE FUNCTION record_stock_adjustment();
