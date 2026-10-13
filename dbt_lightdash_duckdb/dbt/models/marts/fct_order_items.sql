SELECT
    i.order_item_id,
    i.order_id,
    i.product_id,
    o.customer_id,
    o.ordered_at,
    o.status,
    i.quantity,
    i.unit_price,
    i.discount_rate,
    i.line_amount,
    i.discount_rate > 0 AS is_discounted
FROM
    {{ ref('stg_order_items') }} i
JOIN
    {{ ref('stg_orders') }} o USING (order_id)