-- Report records that require data-quality review.
SELECT
    'pick_line_status_metadata' AS issue,
    pick_line_id::TEXT AS record_id,
    status AS details
FROM pick_lines
WHERE (status = 'OPEN'
       AND (pick_date IS NOT NULL OR picked_by IS NOT NULL OR picked_at IS NOT NULL))
   OR (status IN ('PICKED', 'SHORT')
       AND (pick_date IS NULL OR picked_by IS NULL OR picked_at IS NULL))
UNION ALL
SELECT
    'short_line_details' AS issue,
    pick_line_id::TEXT AS record_id,
    'missing or invalid short quantity/reason' AS details
FROM pick_lines
WHERE status = 'SHORT'
  AND (
      short_reason IS NULL
      OR btrim(short_reason) = ''
      OR short_qty IS NULL
      OR short_qty < 1
      OR short_qty > qty
  )
UNION ALL
SELECT
    'multiple_cycle_counts_same_day' AS issue,
    sku || ':' || location_id || ':' || counted_at::DATE::TEXT AS record_id,
    COUNT(*)::TEXT AS details
FROM cycle_counts
GROUP BY sku, location_id, counted_at::DATE
HAVING COUNT(*) > 1
UNION ALL
SELECT
    'future_demand_date' AS issue,
    sku || ':' || day::TEXT AS record_id,
    'daily demand date is in the future' AS details
FROM daily_demand
WHERE day > CURRENT_DATE
UNION ALL
SELECT
    'location_metadata' AS issue,
    location_id AS record_id,
    'zone must be nonblank and pick_sequence must be positive' AS details
FROM location
WHERE btrim(zone) = ''
   OR (pick_sequence IS NOT NULL AND pick_sequence <= 0)
UNION ALL
SELECT
    'missing_demand_date' AS issue,
    COALESCE(sku, '<null>') AS record_id,
    'daily demand day is required' AS details
FROM daily_demand
WHERE day IS NULL
ORDER BY issue, record_id
