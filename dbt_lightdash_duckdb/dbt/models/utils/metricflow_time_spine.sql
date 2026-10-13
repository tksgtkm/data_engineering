{{ config(materialized='table') }}

SELECT
    CAST(d AS date) AS date_day
FROM
    UNNEST(GENERATE_SERIES(DATE '2024-01-01', DATE '2027-12-31', INTERVAL 1 DAY)) AS T(d)