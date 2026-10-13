SELECT
    id AS order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    discount_rate,
    ROUND(quantity * unit_price * (1 - discount_rate), 0) AS line_amount
FROM
    {{ ref('raw_order_items') }}