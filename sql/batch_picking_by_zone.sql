-- Build a walking-order batch plan across open orders.
-- Expected columns:
--   pick_lines(order_id, location_id, status, qty)
--   location(location_id, zone, pick_sequence)
SELECT
    l.pick_sequence,
    l.zone,
    p.location_id,
    COUNT(DISTINCT p.order_id) AS orders,
    COUNT(*) AS lines,
    SUM(p.qty) AS units
FROM pick_lines AS p
JOIN location AS l USING (location_id)
WHERE p.status = 'OPEN'
GROUP BY l.pick_sequence, l.zone, p.location_id
ORDER BY l.zone, l.pick_sequence, p.location_id
