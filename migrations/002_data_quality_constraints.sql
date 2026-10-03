ALTER TABLE pick_lines
    ADD COLUMN short_reason TEXT,
    ADD COLUMN short_qty INT;

ALTER TABLE pick_lines
    ADD CONSTRAINT pick_lines_short_qty_check
    CHECK (
        (status = 'SHORT'
            AND short_reason IS NOT NULL
            AND btrim(short_reason) <> ''
            AND short_qty BETWEEN 1 AND qty)
        OR (status <> 'SHORT'
            AND short_reason IS NULL
            AND short_qty IS NULL)
    ) NOT VALID;

ALTER TABLE pick_lines
    ADD CONSTRAINT pick_lines_status_metadata_check
    CHECK (
        (status = 'OPEN'
            AND pick_date IS NULL
            AND picked_by IS NULL
            AND picked_at IS NULL)
        OR (status IN ('PICKED', 'SHORT')
            AND pick_date IS NOT NULL
            AND picked_by IS NOT NULL
            AND picked_at IS NOT NULL)
    ) NOT VALID;

CREATE INDEX idx_cycle_counts_counted_at
    ON cycle_counts (counted_at, sku, location_id);
