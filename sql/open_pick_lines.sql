-- Return open pick lines used to build capacity-limited batches.
-- Orders are assigned to batches as complete units by batch_picking.py.
SELECT
    p.pick_line_id,
    p.order_id,
    p.sku,
    l.pick_sequence,
    l.zone,
    p.location_id,
    p.qty
FROM pick_lines AS p
JOIN location AS l USING (location_id)
WHERE p.status = 'OPEN'
ORDER BY p.order_id, l.zone, l.pick_sequence, p.location_id
