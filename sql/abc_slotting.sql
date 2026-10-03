-- Classify SKUs by completed pick volume over the last 90 days.
-- The SKU that crosses the 80% cumulative threshold remains in class A.
WITH sku_picks AS (
    SELECT
        sku,
        SUM(qty) AS picks
    FROM pick_lines
    WHERE status = 'PICKED'
      AND pick_date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY sku
),
ranked_picks AS (
    SELECT
        sku,
        picks,
        SUM(picks) OVER (
            ORDER BY picks DESC, sku
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_picks,
        SUM(picks) OVER () AS total_picks
    FROM sku_picks
)
SELECT
    sku,
    picks,
    ROUND(100.0 * cumulative_picks / NULLIF(total_picks, 0), 2)
        AS cumulative_pick_pct,
    CASE
        WHEN cumulative_picks - picks < 0.8 * total_picks THEN 'A'
        ELSE 'B/C'
    END AS class
FROM ranked_picks
    ORDER BY picks DESC, sku
