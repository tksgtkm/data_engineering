/*
EC サイト「ZakkaMall」サンプルデータ - マスタデータ
*/

SET search_path = 'zakka_mall';

-- 1. カテゴリデータ（階層構造）
INSERT INTO category (category_name, category_code, parent_category_id, description) VALUES
-- ルートカテゴリ
('エレクトロニクス', 'electronics', NULL, '電子機器・家電製品'),
('ファッション', 'fashion', NULL, '衣類・アクセサリー'),
('ホーム・キッチン', 'home_kitchen', NULL, '家庭用品・キッチン用品'),
('スポーツ・アウトドア', 'sports_outdoor', NULL, 'スポーツ用品・アウトドア用品'),
('本・メディア', 'books_media', NULL, '書籍・音楽・映画'),

-- サブカテゴリ（エレクトロニクス）
('コンピュータ・IT', 'computers', 1, 'パソコン・IT機器'),
('スマートフォン・携帯電話', 'smartphones', 1, 'モバイル機器'),
('家電', 'appliances', 1, '生活家電'),
('カメラ・AV機器', 'camera_av', 1, 'カメラ・オーディオビジュアル機器'),

-- サブカテゴリ（ファッション）
('メンズファッション', 'mens_fashion', 2, '男性向け衣類'),
('レディースファッション', 'womens_fashion', 2, '女性向け衣類'),
('バッグ・靴・小物', 'bags_shoes', 2, 'バッグ・靴・アクセサリー'),

-- サブカテゴリ（ホーム・キッチン）
('キッチン用品', 'kitchen', 3, '調理器具・食器'),
('インテリア・寝具', 'interior', 3, 'インテリア・寝具・収納'),
('日用品・生活雑貨', 'daily_goods', 3, '日用品・掃除用品'),

-- 詳細カテゴリ（コンピュータ・IT）
('ノートパソコン', 'laptops', 6, 'ノートブック型パソコン'),
('デスクトップパソコン', 'desktops', 6, 'デスクトップ型パソコン'),
('タブレット', 'tablets', 6, 'タブレット端末'),
('PC周辺機器', 'pc_accessories', 6, 'マウス・キーボード・モニター等');

-- カテゴリ階層パスの設定
-- PostgreSQL 版では ltree とトリガーで自動設定していたが、DuckDB 版は
-- 再帰 CTE で 'electronics.computers.laptops' 形式の文字列を組み立てて UPDATE する
UPDATE category
   SET category_path = paths.category_path
  FROM (
      WITH RECURSIVE tree AS (
          SELECT category_id, category_code::VARCHAR AS category_path
            FROM category
           WHERE parent_category_id IS NULL
          UNION ALL
          SELECT c.category_id, t.category_path || '.' || c.category_code
            FROM category AS c
           INNER JOIN tree AS t ON c.parent_category_id = t.category_id
      )
      SELECT category_id, category_path FROM tree
  ) AS paths
 WHERE category.category_id = paths.category_id;

-- 2. 仕入先データ
INSERT INTO supplier (supplier_name, supplier_code, contact_email, contact_phone, address, status, contact_details) VALUES
('テックサプライ株式会社', 'TECH001', 'contact@techsupply.co.jp', '03-1234-5678', '東京都渋谷区渋谷1-1-1', 'active', '{"担当者": "田中太郎", "部署": "営業部", "FAX": "03-1234-5679"}'),
('ファッションワールド', 'FASH001', 'info@fashionworld.co.jp', '06-2345-6789', '大阪府大阪市中央区心斎橋1-2-3', 'active', '{"担当者": "佐藤花子", "部署": "卸売部", "営業時間": "9:00-18:00"}'),
('ホームライフ商事', 'HOME001', 'sales@homelife.co.jp', '052-3456-7890', '愛知県名古屋市中区栄2-3-4', 'active', '{"担当者": "鈴木一郎", "部署": "商品部", "配送対応": "全国"}'),
('スポーツギア株式会社', 'SPORT001', 'order@sportsgear.co.jp', '092-4567-8901', '福岡県福岡市博多区博多駅前3-4-5', 'active', '{"担当者": "高橋次郎", "部署": "営業部", "専門分野": "アウトドア用品"}'),
('ブックディストリビューター', 'BOOK001', 'books@bookdist.co.jp', '011-5678-9012', '北海道札幌市中央区大通西4-5-6', 'active', '{"担当者": "山田三郎", "部署": "出版営業部", "取扱ジャンル": "全般"}'),
('グローバルエレクトロニクス', 'ELEC001', 'global@electronics.co.jp', '03-6789-0123', '東京都港区六本木6-7-8', 'active', '{"担当者": "Johnson Smith", "部署": "International Sales", "言語対応": "英語・日本語"}'),
('アジアファッション貿易', 'ASIA001', 'trade@asiafashion.co.jp', '045-7890-1234', '神奈川県横浜市西区みなとみらい7-8-9', 'active', '{"担当者": "李美香", "部署": "貿易部", "得意分野": "アジアンファッション"}');

-- 3. 顧客データ
INSERT INTO customer (customer_name, email, phone, registration_date, status) VALUES
('田中太郎', 'tanaka.taro@example.com', '090-1234-5678', '2023-01-15', 'active'),
('佐藤花子', 'sato.hanako@example.com', '080-2345-6789', '2023-02-20', 'active'),
('鈴木一郎', 'suzuki.ichiro@example.com', '070-3456-7890', '2023-03-10', 'active'),
('高橋次郎', 'takahashi.jiro@example.com', '090-4567-8901', '2023-04-05', 'active'),
('山田三郎', 'yamada.saburo@example.com', '080-5678-9012', '2023-05-12', 'active'),
('伊藤美咲', 'ito.misaki@example.com', '070-6789-0123', '2023-06-18', 'active'),
('渡辺健太', 'watanabe.kenta@example.com', '090-7890-1234', '2023-07-22', 'active'),
('中村由美', 'nakamura.yumi@example.com', '080-8901-2345', '2023-08-30', 'active'),
('小林大輔', 'kobayashi.daisuke@example.com', '070-9012-3456', '2023-09-14', 'active'),
('加藤麻衣', 'kato.mai@example.com', '090-0123-4567', '2023-10-08', 'active'),
('吉田雄介', 'yoshida.yusuke@example.com', '080-1234-5678', '2023-11-25', 'active'),
('松本さくら', 'matsumoto.sakura@example.com', '070-2345-6789', '2023-12-03', 'active'),
('井上拓也', 'inoue.takuya@example.com', '090-3456-7890', '2024-01-10', 'active'),
('木村愛子', 'kimura.aiko@example.com', '080-4567-8901', '2024-01-10', 'active'),
('斎藤博', 'saito.hiroshi@example.com', '070-5678-9012', '2024-01-10', 'active'),
-- 追加顧客データ（16-30）
('森田直子', 'morita.naoko@example.com', '090-6789-0123', '2023-04-12', 'active'),
('清水雄一', 'shimizu.yuichi@example.com', '080-7890-1234', '2023-05-28', 'active'),
('橋本麻衣', 'hashimoto.mai@example.com', '070-8901-2345', '2023-06-15', 'active'),
('石川浩二', 'ishikawa.koji@example.com', '090-9012-3456', '2023-07-22', 'active'),
('斎藤優子', 'saito.yuko@example.com', '080-0123-4567', '2023-08-18', 'active'),
('前田信也', 'maeda.shinya@example.com', '070-1234-5678', '2023-09-05', 'active'),
('藤田千春', 'fujita.chiharu@example.com', '090-2345-6789', '2023-10-11', 'active'),
('岡田拓也', 'okada.takuya@example.com', '080-3456-7890', '2023-11-27', 'active'),
('村上綾香', 'murakami.ayaka@example.com', '070-4567-8901', '2023-12-13', 'active'),
('長谷川健', 'hasegawa.ken@example.com', '090-5678-9012', '2024-01-09', 'active'),
('近藤美穂', 'kondo.miho@example.com', '080-6789-0123', '2024-02-25', 'active'),
('後藤正樹', 'goto.masaki@example.com', '070-7890-1234', '2024-03-01', 'active'),
('坂本理恵', 'sakamoto.rie@example.com', '090-8901-2345', '2023-03-20', 'active'),
('内田慎一', 'uchida.shinichi@example.com', '080-9012-3456', '2023-04-07', 'active'),
('西村香織', 'nishimura.kaori@example.com', '070-0123-4567', '2023-05-14', 'active'),
-- 追加顧客データ（31-50）
('平野大介', 'hirano.daisuke@example.com', '090-1234-5679', '2023-06-30', 'active'),
('三浦恵美', 'miura.emi@example.com', '080-2345-6780', '2023-07-17', 'active'),
('原田光男', 'harada.mitsuo@example.com', '070-3456-7891', '2023-08-03', 'active'),
('菊地裕子', 'kikuchi.yuko@example.com', '090-4567-8902', '2023-09-19', 'active'),
('野村秀樹', 'nomura.hideki@example.com', '080-5678-9013', '2023-10-06', 'active'),
('大野智子', 'ohno.tomoko@example.com', '070-6789-0124', '2023-11-22', 'active'),
('福田和彦', 'fukuda.kazuhiko@example.com', '090-7890-1235', '2023-12-09', 'active'),
('上田真由美', 'ueda.mayumi@example.com', '080-8901-2346', '2024-01-26', 'active'),
('杉山俊介', 'sugiyama.shunsuke@example.com', '070-9012-3457', '2024-02-12', 'active'),
('青木恵', 'aoki.megumi@example.com', '090-0123-4568', '2024-03-01', 'active'),
('竹内健一', 'takeuchi.kenichi@example.com', '080-1234-5679', '2023-01-28', 'active'),
('小川美紀', 'ogawa.miki@example.com', '070-2345-6780', '2023-02-15', 'active'),
('池田雅人', 'ikeda.masato@example.com', '090-3456-7891', '2023-03-04', 'active'),
('山口千恵', 'yamaguchi.chie@example.com', '080-4567-8902', '2023-04-21', 'active'),
('金子隆志', 'kaneko.takashi@example.com', '070-5678-9013', '2023-05-08', 'active'),
('宮崎美和', 'miyazaki.miwa@example.com', '090-6789-0124', '2023-06-25', 'active'),
('島田浩', 'shimada.hiroshi@example.com', '080-7890-1235', '2023-07-12', 'active'),
('今井由香', 'imai.yuka@example.com', '070-8901-2346', '2023-08-29', 'active'),
('横山誠', 'yokoyama.makoto@example.com', '090-9012-3457', '2023-09-16', 'active'),
('田村恵子', 'tamura.keiko@example.com', '080-0123-4568', '2023-10-03', 'active');

-- 顧客の created_at / updated_at を registration_date に合わせる
-- （SCD Type 2 の snapshot で valid_from が注文日より過去になるように）
-- （DuckDB 版はトリガーがないため、そのまま UPDATE すれば明示した値が残る）
UPDATE customer
   SET created_at = registration_date::timestamp,
       updated_at = registration_date::timestamp;

-- 4. 顧客住所データ
INSERT INTO customer_address (customer_id, address_type, postal_code, prefecture, city, address_line1, address_line2, is_default) VALUES
(1, 'both', '150-0001', '東京都', '渋谷区', '神宮前1-2-3', 'マンション神宮前101', true),
(2, 'shipping', '530-0001', '大阪府', '大阪市北区', '梅田2-3-4', 'タワーマンション梅田502', true),
(2, 'billing', '530-0002', '大阪府', '大阪市北区', '曽根崎1-1-1', '佐藤ビル3F', false),
(3, 'both', '460-0008', '愛知県', '名古屋市中区', '栄3-4-5', 'プラザ栄201', true),
(4, 'both', '812-0011', '福岡県', '福岡市博多区', '博多駅前4-5-6', 'ステーション博多301', true),
(5, 'both', '060-0001', '北海道', '札幌市中央区', '北1条西5-6-7', 'センタービル札幌401', true),
(6, 'both', '220-0012', '神奈川県', '横浜市西区', 'みなとみらい6-7-8', 'オーシャンタワー1205', true),
(7, 'both', '980-0021', '宮城県', '仙台市青葉区', '中央7-8-9', 'グリーンハイツ仙台303', true),
(8, 'both', '730-0011', '広島県', '広島市中区', '基町8-9-10', 'パークサイド広島501', true),
(9, 'both', '760-0017', '香川県', '高松市', '番町9-10-11', 'サンシャイン高松201', true),
(10, 'both', '900-0015', '沖縄県', '那覇市', '久茂地10-11-12', 'トロピカル那覇401', true),
(11, 'both', '951-8067', '新潟県', '新潟市中央区', '本町11-12-13', 'スノーパレス新潟301', true),
(12, 'both', '390-0811', '長野県', '松本市', '中央12-13-14', 'アルプスビュー松本201', true),
(13, 'both', '420-0853', '静岡県', '静岡市葵区', '追手町13-14-15', 'キャッスル静岡501', true),
(14, 'both', '640-8137', '和歌山県', '和歌山市', '吹上14-15-16', 'オレンジハウス和歌山301', true),
(15, 'both', '770-0832', '徳島県', '徳島市', '寺島本町西15-16-17', 'リバーサイド徳島201', true),
(16, 'both', '100-0001', '東京都', '千代田区', '千代田1-1-1', '千代田マンション101', true),
(17, 'both', '550-0001', '大阪府', '大阪市西区', '土佐堀1-2-3', '土佐堀ハイツ202', true),
(18, 'both', '231-0001', '神奈川県', '横浜市中区', '太田町2-3-4', '太田町レジデンス303', true),
(19, 'both', '450-0001', '愛知県', '名古屋市中村区', '那古野3-4-5', '那古野タワー404', true),
(20, 'both', '810-0001', '福岡県', '福岡市中央区', '天神4-5-6', '天神プラザ505', true),
(21, 'both', '980-0001', '宮城県', '仙台市青葉区', '一番町5-6-7', '一番町ビル606', true),
(22, 'both', '730-0001', '広島県', '広島市中区', '大手町6-7-8', '大手町センター707', true),
(23, 'both', '700-0001', '岡山県', '岡山市北区', '表町7-8-9', '表町マンション808', true),
(24, 'both', '760-0001', '香川県', '高松市', '寿町8-9-10', '寿町ハイツ909', true),
(25, 'both', '790-0001', '愛媛県', '松山市', '湊町9-10-11', '湊町レジデンス1010', true),
(26, 'both', '870-0001', '大分県', '大分市', '府内町10-11-12', '府内町タワー1111', true),
(27, 'both', '860-0001', '熊本県', '熊本市中央区', '手取本町11-12-13', '手取本町プラザ1212', true),
(28, 'both', '890-0001', '鹿児島県', '鹿児島市', '山下町12-13-14', '山下町ビル1313', true),
(29, 'both', '900-0001', '沖縄県', '那覇市', '港町13-14-15', '港町マンション1414', true),
(30, 'both', '950-0001', '新潟県', '新潟市東区', '物見山14-15-16', '物見山ハイツ1515', true),
(31, 'both', '380-0001', '長野県', '長野市', '大字鶴賀15-16-17', '鶴賀レジデンス1616', true),
(32, 'both', '400-0001', '山梨県', '甲府市', '愛宕町16-17-18', '愛宕町タワー1717', true),
(33, 'both', '410-0001', '静岡県', '沼津市', '大手町17-18-19', '大手町プラザ1818', true),
(34, 'both', '500-0001', '岐阜県', '岐阜市', '橋本町18-19-20', '橋本町ビル1919', true),
(35, 'both', '520-0001', '滋賀県', '大津市', '京町19-20-21', '京町マンション2020', true),
(36, 'both', '600-0001', '京都府', '京都市下京区', '四条通20-21-22', '四条通ハイツ2121', true),
(37, 'both', '630-0001', '奈良県', '奈良市', '法華寺町21-22-23', '法華寺町レジデンス2222', true),
(38, 'both', '650-0001', '兵庫県', '神戸市中央区', '加納町22-23-24', '加納町タワー2323', true),
(39, 'both', '680-0001', '鳥取県', '鳥取市', '浜坂23-24-25', '浜坂プラザ2424', true),
(40, 'both', '690-0001', '島根県', '松江市', '朝日町24-25-26', '朝日町ビル2525', true),
(41, 'both', '710-0001', '岡山県', '倉敷市', '本町25-26-27', '本町マンション2626', true),
(42, 'both', '750-0001', '山口県', '下関市', '赤間町26-27-28', '赤間町ハイツ2727', true),
(43, 'both', '770-0001', '徳島県', '徳島市', '新町橋27-28-29', '新町橋レジデンス2828', true),
(44, 'both', '780-0001', '高知県', '高知市', '本町28-29-30', '本町タワー2929', true),
(45, 'both', '800-0001', '福岡県', '北九州市門司区', '西海岸29-30-31', '西海岸プラザ3030', true),
(46, 'both', '840-0001', '佐賀県', '佐賀市', '駅前中央30-31-32', '駅前中央ビル3131', true),
(47, 'both', '850-0001', '長崎県', '長崎市', '江戸町31-32-33', '江戸町マンション3232', true),
(48, 'both', '880-0001', '宮崎県', '宮崎市', '橘通東32-33-34', '橘通東ハイツ3333', true),
(49, 'both', '010-0001', '秋田県', '秋田市', '中通33-34-35', '中通レジデンス3434', true),
(50, 'both', '020-0001', '岩手県', '盛岡市', '中央通34-35-36', '中央通タワー3535', true);
