SELECT
    id AS product_id,
    name AS product_name,
    category,
    list_price
FROM
    {{ ref('raw_products') }}