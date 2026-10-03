-- Report inventory variances between system stock and cycle counts.
-- Expected columns:
--   stock(sku, location_id, system_qty)
--   cycle_counts(sku, location_id, counted_qty)
WITH latest_counts AS (
    SELECT
        sku,
        location_id,
        counted_qty,
        counted_at,
        counted_by,
        ROW_NUMBER() OVER (
            PARTITION BY sku, location_id
            ORDER BY counted_at DESC, count_id DESC
        ) AS count_rank
    FROM cycle_counts
)
SELECT
    s.sku,
    s.location_id,
    s.system_qty,
    c.counted_qty,
    c.counted_qty - s.system_qty AS variance,
    c.counted_at,
    c.counted_by
FROM stock AS s
JOIN latest_counts AS c USING (sku, location_id)
WHERE ABS(c.counted_qty - s.system_qty) > 0
  AND c.count_rank = 1
ORDER BY s.sku, s.location_id
