-- Review the rows first. The application operation defaults to dry-run.
-- Example retention window: keep two years of audit history.
SELECT 'pick_line_status_history' AS table_name,
       COUNT(*) AS rows_eligible
FROM pick_line_status_history
WHERE changed_at < CURRENT_TIMESTAMP - INTERVAL '2 years'
UNION ALL
SELECT 'stock_adjustment_history' AS table_name,
       COUNT(*) AS rows_eligible
FROM stock_adjustment_history
WHERE changed_at < CURRENT_TIMESTAMP - INTERVAL '2 years';
