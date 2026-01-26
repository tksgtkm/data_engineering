SELECT
    user_id,
    CASE
        WHEN register_device = 1 THEN 'PC'
        WHEN register_device = 2 THEN 'SP'
        WHEN register_device = 3 THEN 'アプリ'
    END AS device_name
FROM
    mst_users
;