-- Aggregate open lines by order/location for inspection.
-- Capacity-limited complete-order batching is performed by batch_picking.py.
SELECT
    p.order_id,
    l.pick_sequence,
    l.zone,
    p.location_id,
    COUNT(*) AS lines,
    SUM(p.qty) AS units
FROM pick_lines AS p
JOIN location AS l USING (location_id)
WHERE p.status = 'OPEN'
GROUP BY p.order_id, l.pick_sequence, l.zone, p.location_id
ORDER BY p.order_id, l.zone, l.pick_sequence, p.location_id
