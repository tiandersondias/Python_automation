-- Run sql/data_quality_checks.sql and repair any reported legacy rows before
-- applying this migration to an existing database.
ALTER TABLE pick_lines
    VALIDATE CONSTRAINT pick_lines_short_qty_check;

ALTER TABLE pick_lines
    VALIDATE CONSTRAINT pick_lines_status_metadata_check;
