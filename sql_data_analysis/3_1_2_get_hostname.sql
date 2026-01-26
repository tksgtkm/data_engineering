SELECT
    stamp,
    regexp_extract(referrer, 'https?://([^/]*)', 1) AS referrer_host
FROM
    access_log
;