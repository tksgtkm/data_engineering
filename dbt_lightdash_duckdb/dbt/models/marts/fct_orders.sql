WITH items AS (
    SELECT
        order_id,
        SUM(line_amount) AS order_total,
        SUM(quantity) AS item_quantity,
        COUNT(*) AS line_count,
    FROM
        {{ ref('stg_order_items') }}
    GROUP BY 1
),
orders AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY ordered_at, order_id) AS customer_order_seq
    FROM
        {{ ref('stg_orders') }}
)
SELECT
    o.order_id,
    o.customer_id,
    o.ordered_at,
    o.status,
    o.channel,
    o.status = 'completed' AS is_completed,
    o.customer_order_seq = 1 AS is_first_order,
    COALESCE(i.order_total, 0) AS order_total,
    COALESCE(i.item_quantity, 0) AS item_quantity,
    COALESCE(i.line_count) AS line_count
FROM
    orders o
LEFT JOIN
    items i USING (order_id)