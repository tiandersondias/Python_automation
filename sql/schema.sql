CREATE TABLE sku (
    sku          VARCHAR(30) PRIMARY KEY,
    description  TEXT NOT NULL,
    unit_cost    NUMERIC(10,2) CHECK (unit_cost IS NULL OR unit_cost >= 0),
    lead_time_days INT NOT NULL DEFAULT 5 CHECK (lead_time_days >= 0)
);

CREATE TABLE location (
    location_id   VARCHAR(20) PRIMARY KEY,
    zone          VARCHAR(10) NOT NULL,
    aisle         INT NOT NULL CHECK (aisle >= 0),
    bay           INT NOT NULL CHECK (bay >= 0),
    level         INT NOT NULL CHECK (level >= 0),
    pick_sequence INT
);

CREATE TABLE orders (
    order_id   BIGINT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    status     VARCHAR(15) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'CLOSED', 'CANCELLED'))
);

CREATE TABLE pick_lines (
    pick_line_id BIGSERIAL PRIMARY KEY,
    order_id     BIGINT NOT NULL REFERENCES orders(order_id),
    sku          VARCHAR(30) NOT NULL REFERENCES sku(sku),
    location_id  VARCHAR(20) NOT NULL REFERENCES location(location_id),
    qty          INT NOT NULL CHECK (qty > 0),
    status       VARCHAR(15) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'PICKED', 'SHORT')),
    pick_date    DATE,
    picked_by   VARCHAR(30),
    picked_at   TIMESTAMP,
    CHECK (
        status = 'OPEN'
        OR (picked_by IS NOT NULL AND picked_at IS NOT NULL)
    ),
    CHECK (
        status <> 'OPEN'
        OR (picked_by IS NULL AND picked_at IS NULL)
    )
);

CREATE TABLE stock (
    sku         VARCHAR(30) REFERENCES sku(sku),
    location_id VARCHAR(20) REFERENCES location(location_id),
    system_qty  INT NOT NULL DEFAULT 0 CHECK (system_qty >= 0),
    PRIMARY KEY (sku, location_id)
);

CREATE TABLE cycle_counts (
    count_id    BIGSERIAL PRIMARY KEY,
    sku         VARCHAR(30) NOT NULL,
    location_id VARCHAR(20) NOT NULL,
    counted_qty INT NOT NULL CHECK (counted_qty >= 0),
    counted_at  TIMESTAMP NOT NULL DEFAULT now(),
    counted_by  VARCHAR(30),
    FOREIGN KEY (sku, location_id) REFERENCES stock(sku, location_id)
);

CREATE TABLE daily_demand (
    sku VARCHAR(30) REFERENCES sku(sku),
    day DATE,
    qty INT NOT NULL CHECK (qty >= 0),
    PRIMARY KEY (sku, day)
);

CREATE INDEX idx_pick_lines_date
    ON pick_lines (pick_date, sku);

CREATE INDEX idx_pick_lines_status
    ON pick_lines (status, order_id);

CREATE INDEX idx_pick_lines_status_location
    ON pick_lines (status, location_id, order_id);

CREATE INDEX idx_pick_lines_status_date_sku
    ON pick_lines (status, pick_date, sku);

CREATE INDEX idx_cycle_counts_location_time
    ON cycle_counts (sku, location_id, counted_at DESC, count_id DESC);

CREATE INDEX idx_stock_location
    ON stock (location_id, sku);

CREATE INDEX idx_daily_demand_day_sku
    ON daily_demand (day, sku);
