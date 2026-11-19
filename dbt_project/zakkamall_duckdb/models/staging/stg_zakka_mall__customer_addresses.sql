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
        {{ source('zakka_mall', 'customer_address') }}
),
cleaned AS (
    SELECT
        address_id,
        customer_id,
        address_type,
        postal_code,
        prefecture,
        city,
        address_line1,
        address_line2,
        is_default,
        created_at,
        updated_at,
        -- 正規化された住所
        concat_ws(
            ' ',
            prefecture,
            city,
            address_line1,
            coalesce(address_line2, '')
        ) AS full_address,
        -- 地域区分
        CASE
            WHEN prefecture IN ('北海道') THEN '北海道'
            WHEN prefecture IN ('青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県') THEN '東北'
            WHEN prefecture IN ('茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県') THEN '関東'
            WHEN prefecture IN ('新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県') THEN '中部'
            WHEN prefecture IN ('三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県') THEN '関西'
            WHEN prefecture IN ('鳥取県', '島根県', '岡山県', '広島県', '山口県') THEN '中国'
            WHEN prefecture IN ('徳島県', '香川県', '愛媛県', '高知県') THEN '四国'
            WHEN prefecture IN ('福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県') THEN '九州・沖縄'
            ELSE 'その他'
        END AS region
    FROM 
        source
),
with_quality AS (
    SELECT
        *,
        -- データ品質フラグ（DB 制約に頼れないビジネスルールを検証）
        -- 形式・値域に関する検証のみをis_valid_recordに集中させる
        CASE
            -- 郵便番号は7ケタ数字（ハイフン有無は問わない）
            WHEN postal_code !~ '^[0-9]{3}-?[0-9]{4}$' THEN false
            -- 住所詳細が空文字列のみ
            WHEN trim(address_line1) = '' THEN false
            -- 都道府県が46都道府県以外(region判定でその他になるケース)
            WHEN region = 'その他' THEN false
            ELSE true
        END AS is_valid_record
    FROM
        cleaned
)
SELECT
    *
FROM
    with_quality