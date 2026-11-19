{{
    config(
        materialized='view',
        tags=['staging', 'customer']
    )
}}

WITH source AS (
    SELECT
        *
    FROM
        {{ source('zakka_mall', 'customer') }}
),
cleaned AS (
    SELECT
        customer_id,
        phone,
        registration_date,
        STATUS AS customer_status,
        created_at,
        updated_at,
        trim(customer_name),
        lower(trim(email)) AS email,
        -- 計算フィールド
        CASE
            WHEN registration_date >= current_date - interval '30 days' THEN 'new'
            WHEN registration_date >= current_date - interval '365 days' THEN 'existing'
            ELSE 'long_term'
        END AS customer_tenure_segment,
        -- データ品質フラグ
        CASE
            WHEN customer_name IS NULL OR trim(customer_name) = '' THEN false
            WHEN email IS NULL OR trim(email) = '' THEN false
            WHEN email NOT LIKE '%@%' THEN false
            ELSE true
        END AS is_valid_record
    FROM
        source
)
SELECT
    *
FROM
    cleaned