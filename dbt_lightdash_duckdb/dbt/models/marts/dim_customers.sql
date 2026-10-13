WITH order_stats AS (
    SELECT
        customer_id,
        MIN(ordered_at) AS first_ordered_at,
        MAX(ordered_at) AS last_ordered_at,
        COUNT(*) AS order_count,
        SUM(order_total) AS lifetime_value
    FROM
        {{ ref('fct_orders') }}
    WHERE status <> 'cancelled'
    GROUP BY 1
)
SELECT
    c.customer_id,
    c.region,
    c.segment,
    c.signed_up_at,
    s.first_ordered_at,
    s.last_ordered_at,
    COALESCE(s.order_count, 0) AS order_count,
    COALESCE(s.lifetime_value, 0) AS lifetime_value,
    CASE
        WHEN s.order_count IS NULL THEN 'no_orders'
        WHEN s.order_count = 1 THEN 'one_time'
        WHEN s.order_count < 5 THEN 'repeat'
        ELSE 'loyal'
    END AS customer_tier
FROM
    {{ ref('stg_customers') }} c
LEFT JOIN
    order_stats s USING (customer_id)