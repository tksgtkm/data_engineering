{{
    config(
        materialized='view',
        tags=['staging', 'master']
    )
}}

WITH source AS (
    SELECT
        *
    FROM
        {{ source('zakka_mall', 'category') }}
),
cleaned AS (
    SELECT
        category_id,
        category_code,
        category_name,
        parent_category_id,
        description,
        is_active,
        category_path,
        created_at,
        updated_at,
        CASE
            WHEN category_name IS NULL OR trim(category_name) = '' THEN false
            WHEN category_code IS NULL OR trim(category_code) = '' THEN false
            ELSE true
        END AS is_valid_record
    FROM
        source
)
SELECT
    *
FROM
    cleaned