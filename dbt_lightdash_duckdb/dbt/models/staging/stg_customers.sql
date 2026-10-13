SELECT
    id AS customer_id,
    region,
    segment,
    signup_date AS signed_up_at
FROM
    {{ ref('raw_customers') }}