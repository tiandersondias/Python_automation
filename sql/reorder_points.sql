SELECT
    d.sku,
    d.day,
    d.qty,
    s.lead_time_days
FROM daily_demand AS d
JOIN sku AS s USING (sku)
ORDER BY d.sku, d.day
