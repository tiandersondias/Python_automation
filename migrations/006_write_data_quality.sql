ALTER TABLE location
    ADD CONSTRAINT location_zone_nonblank_check
    CHECK (btrim(zone) <> '') NOT VALID;

ALTER TABLE location
    ADD CONSTRAINT location_pick_sequence_check
    CHECK (pick_sequence IS NULL OR pick_sequence > 0) NOT VALID;

ALTER TABLE daily_demand
    ADD CONSTRAINT daily_demand_day_required_check
    CHECK (day IS NOT NULL) NOT VALID;

CREATE OR REPLACE FUNCTION reject_future_demand()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF NEW.day > CURRENT_DATE THEN
        RAISE EXCEPTION 'daily demand day cannot be in the future';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_reject_future_demand
BEFORE INSERT OR UPDATE OF day ON daily_demand
FOR EACH ROW
EXECUTE FUNCTION reject_future_demand();

CREATE OR REPLACE FUNCTION enforce_pick_line_status_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF OLD.status <> NEW.status
       AND OLD.status <> 'OPEN' THEN
        RAISE EXCEPTION
            'pick line % cannot transition from % to %',
            OLD.pick_line_id, OLD.status, NEW.status;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_enforce_pick_line_status_transition
BEFORE UPDATE OF status ON pick_lines
FOR EACH ROW
EXECUTE FUNCTION enforce_pick_line_status_transition();
