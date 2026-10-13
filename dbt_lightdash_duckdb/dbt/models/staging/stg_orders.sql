SELECT
    id AS order_id,
    customer_id,
    order_date AS ordered_at,
    status,
    channel
FROM
    {{ ref('raw_orders') }}