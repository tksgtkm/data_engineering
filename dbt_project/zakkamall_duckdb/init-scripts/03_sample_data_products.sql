/*
EC サイト「ZakkaMall」サンプルデータ - 商品データ
*/

SET search_path = 'zakka_mall';

-- 商品データ（エレクトロニクス - ノートパソコン）
INSERT INTO product (product_name, product_code, sku, category_id, supplier_id, unit_price, description, specifications) VALUES
('MacBook Air 13インチ M2チップ', 'MBA-M2-13-256', 'APPLE-MBA-M2-256GB', 16, 1, 148800.00, 'Apple M2チップ搭載の軽量ノートパソコン', '{"brand": "Apple", "model": "MacBook Air", "cpu": "M2", "memory": "8GB", "storage": "256GB SSD", "display": "13.6インチ", "weight": "1.24kg", "warranty_years": 1}'),
('ThinkPad X1 Carbon Gen 11', 'TP-X1C-G11-512', 'LENOVO-X1C-G11-512GB', 16, 1, 198000.00, 'ビジネス向け軽量高性能ノートパソコン', '{"brand": "Lenovo", "model": "ThinkPad X1 Carbon", "cpu": "Intel Core i7-1365U", "memory": "16GB", "storage": "512GB SSD", "display": "14インチ", "weight": "1.12kg", "warranty_years": 3}'),
('Surface Laptop 5', 'SF-LP5-13-256', 'MS-SURFACE-LP5-256GB', 16, 6, 139800.00, 'Microsoft Surface Laptop 第5世代', '{"brand": "Microsoft", "model": "Surface Laptop 5", "cpu": "Intel Core i5-1235U", "memory": "8GB", "storage": "256GB SSD", "display": "13.5インチ", "weight": "1.29kg", "warranty_years": 1}'),
('VAIO FE14', 'VAIO-FE14-512', 'VAIO-FE14-512GB', 16, 1, 89800.00, 'VAIO製軽量ビジネスノートパソコン', '{"brand": "VAIO", "model": "FE14", "cpu": "Intel Core i5-1235U", "memory": "8GB", "storage": "512GB SSD", "display": "14インチ", "weight": "1.25kg", "warranty_years": 1}'),

-- 商品データ（エレクトロニクス - スマートフォン）
('iPhone 15 Pro 128GB', 'IP15P-128-TI', 'APPLE-IP15P-128GB-TI', 7, 1, 159800.00, 'iPhone 15 Pro チタニウム 128GB', '{"brand": "Apple", "model": "iPhone 15 Pro", "storage": "128GB", "color": "チタニウム", "display": "6.1インチ", "camera": "48MP", "warranty_years": 1}'),
('Galaxy S24 Ultra 256GB', 'GS24U-256-BK', 'SAMSUNG-GS24U-256GB', 7, 6, 189800.00, 'Samsung Galaxy S24 Ultra 256GB', '{"brand": "Samsung", "model": "Galaxy S24 Ultra", "storage": "256GB", "color": "ブラック", "display": "6.8インチ", "camera": "200MP", "warranty_years": 1}'),
('Pixel 8 Pro 128GB', 'PX8P-128-WH', 'GOOGLE-PX8P-128GB', 7, 6, 128000.00, 'Google Pixel 8 Pro 128GB', '{"brand": "Google", "model": "Pixel 8 Pro", "storage": "128GB", "color": "ホワイト", "display": "6.7インチ", "camera": "50MP", "warranty_years": 1}'),

-- 商品データ（ファッション - メンズ）
('ビジネススーツ ネイビー', 'SUIT-NV-M-L', 'MENS-SUIT-NAVY-L', 10, 2, 39800.00, 'フォーマルビジネススーツ ネイビー Lサイズ', '{"brand": "ZAKKA", "category": "スーツ", "color": "ネイビー", "size": "L", "material": "ウール100%", "season": "オールシーズン"}'),
('カジュアルシャツ 白', 'SHIRT-WH-M-M', 'MENS-SHIRT-WHITE-M', 10, 2, 4980.00, 'コットンカジュアルシャツ 白 Mサイズ', '{"brand": "ZAKKA", "category": "シャツ", "color": "白", "size": "M", "material": "コットン100%", "sleeve": "長袖"}'),
('デニムパンツ インディゴ', 'JEANS-IN-M-32', 'MENS-JEANS-INDIGO-32', 10, 2, 8900.00, 'ストレートデニムパンツ インディゴ 32インチ', '{"brand": "ZAKKA", "category": "パンツ", "color": "インディゴ", "size": "32", "material": "デニム", "fit": "ストレート"}'),

-- 商品データ（ファッション - レディース）
('ワンピース フローラル', 'DRESS-FL-W-M', 'WOMENS-DRESS-FLORAL-M', 11, 2, 12800.00, 'フローラル柄ワンピース Mサイズ', '{"brand": "ZAKKA", "category": "ワンピース", "pattern": "フローラル", "size": "M", "material": "ポリエステル", "season": "春夏"}'),
('ニットセーター ベージュ', 'KNIT-BG-W-S', 'WOMENS-KNIT-BEIGE-S', 11, 7, 6800.00, 'カシミヤ混ニットセーター ベージュ Sサイズ', '{"brand": "ASIA", "category": "ニット", "color": "ベージュ", "size": "S", "material": "カシミヤ30%・ウール70%", "season": "秋冬"}'),
('スカート プリーツ', 'SKIRT-PL-W-M', 'WOMENS-SKIRT-PLEATS-M', 11, 2, 7900.00, 'プリーツスカート Mサイズ', '{"brand": "ZAKKA", "category": "スカート", "style": "プリーツ", "size": "M", "material": "ポリエステル", "length": "ミディ"}'),

-- 商品データ（ホーム・キッチン）
('ステンレス包丁セット', 'KNIFE-SET-ST-3', 'KITCHEN-KNIFE-SET-3PC', 13, 3, 15800.00, 'プロ仕様ステンレス包丁3本セット', '{"brand": "HOMELIFE", "category": "調理器具", "material": "ステンレス", "pieces": 3, "includes": ["三徳包丁", "ペティナイフ", "パン切り包丁"]}'),
('電気ケトル 1.2L', 'KETTLE-EL-12', 'KITCHEN-KETTLE-1.2L', 13, 3, 8900.00, '電気ケトル 1.2L 温度調節機能付き', '{"brand": "HOMELIFE", "category": "電気製品", "capacity": "1.2L", "features": ["温度調節", "保温機能", "空焚き防止"], "power": "1200W"}'),
('食器セット 4人用', 'DISH-SET-4P', 'KITCHEN-DISH-SET-4', 13, 3, 12800.00, '磁器食器セット 4人用 20ピース', '{"brand": "HOMELIFE", "category": "食器", "material": "磁器", "persons": 4, "pieces": 20, "dishwasher_safe": true}'),

-- 商品データ（スポーツ・アウトドア）
('ランニングシューズ', 'RUN-SHOES-BK-26', 'SPORTS-RUN-SHOES-26', 4, 4, 12800.00, 'ランニングシューズ ブラック 26.0cm', '{"brand": "SPORTSGEAR", "category": "シューズ", "color": "ブラック", "size": "26.0cm", "type": "ランニング", "cushion": "高反発"}'),
('テント 4人用', 'TENT-4P-GR', 'OUTDOOR-TENT-4PERSON', 4, 4, 28900.00, 'ドーム型テント 4人用 グリーン', '{"brand": "SPORTSGEAR", "category": "テント", "capacity": "4人", "type": "ドーム型", "color": "グリーン", "waterproof": "3000mm", "weight": "4.2kg"}'),
('バックパック 30L', 'BACKPACK-30L-BL', 'OUTDOOR-BACKPACK-30L', 4, 4, 15800.00, 'トレッキングバックパック 30L ブルー', '{"brand": "SPORTSGEAR", "category": "バックパック", "capacity": "30L", "color": "ブルー", "features": ["レインカバー", "ハイドレーション対応"], "weight": "1.8kg"}'),
('ヨガマット', 'YOGA-MAT-PK', 'SPORTS-YOGA-MAT', 4, 4, 3980.00, 'ヨガマット ピンク 6mm', '{"brand": "SPORTSGEAR", "thickness": "6mm", "color": "ピンク", "material": "TPE", "size": "183cm×61cm"}'),
('ダンベルセット', 'DUMBBELL-SET-20', 'SPORTS-DUMBBELL-20KG', 4, 4, 12800.00, '可変式ダンベルセット 20kg', '{"brand": "SPORTSGEAR", "weight": "20kg", "type": "可変式", "material": "鉄製", "adjustable": true}'),
('自転車 クロスバイク', 'BIKE-CROSS-BK', 'SPORTS-BIKE-CROSS', 4, 4, 58000.00, 'クロスバイク ブラック', '{"brand": "SPORTSGEAR", "type": "クロスバイク", "color": "ブラック", "gear": "21段変速", "wheel_size": "700C"}'),

-- 商品データ（本・メディア）
('プログラミング入門書', 'BOOK-PROG-001', 'BOOK-PROGRAMMING-INTRO', 5, 5, 2980.00, 'Python プログラミング入門', '{"category": "技術書", "language": "Python", "level": "初級", "pages": 320, "publisher": "テック出版", "isbn": "978-4-12345-678-9"}'),
('料理レシピ本', 'BOOK-COOK-001', 'BOOK-COOKING-RECIPE', 5, 5, 980.00, '家庭料理レシピ集 100選', '{"category": "料理", "recipes": 100, "level": "初級〜中級", "pages": 240, "publisher": "クッキング出版", "isbn": "978-4-23456-789-0"}'),
('ビジネス書', 'BOOK-BIZ-001', 'BOOK-BUSINESS-SUCCESS', 5, 5, 1680.00, '成功するビジネス戦略', '{"category": "ビジネス", "topic": "戦略", "pages": 280, "publisher": "ビジネス出版", "isbn": "978-4-34567-890-1"}'),
('小説 ベストセラー', 'BOOK-NOVEL-001', 'BOOK-NOVEL-BESTSELLER', 5, 5, 880.00, '話題の小説 ベストセラー', '{"category": "小説", "genre": "現代文学", "pages": 350, "publisher": "文芸出版", "isbn": "978-4-45678-901-2"}'),
('健康・ダイエット本', 'BOOK-HEALTH-001', 'BOOK-HEALTH-DIET', 5, 5, 780.00, '健康的なダイエット法', '{"category": "健康", "topic": "ダイエット", "pages": 200, "publisher": "健康出版", "isbn": "978-4-56789-012-3"}'),
('旅行ガイドブック', 'BOOK-TRAVEL-001', 'BOOK-TRAVEL-GUIDE', 5, 5, 1880.00, '日本全国旅行ガイド', '{"category": "旅行", "region": "日本全国", "pages": 400, "publisher": "旅行出版", "isbn": "978-4-67890-123-4"}'),

-- 商品データ（エレクトロニクス - 家電）
('4K液晶テレビ 55インチ', 'TV-4K-55', 'ELEC-TV-4K-55INCH', 8, 6, 89800.00, '4K対応液晶テレビ 55インチ', '{"brand": "GLOBAL", "size": "55インチ", "resolution": "4K", "smart_tv": true, "warranty_years": 3}'),
('冷蔵庫 400L', 'FRIDGE-400L', 'ELEC-FRIDGE-400L', 8, 6, 128000.00, '省エネ冷蔵庫 400L', '{"brand": "GLOBAL", "capacity": "400L", "energy_rating": "★★★★★", "features": ["自動製氷", "野菜室"], "warranty_years": 5}'),
('洗濯機 8kg', 'WASH-8KG', 'ELEC-WASHER-8KG', 8, 6, 78000.00, 'ドラム式洗濯機 8kg', '{"brand": "GLOBAL", "capacity": "8kg", "type": "ドラム式", "features": ["乾燥機能", "節水"], "warranty_years": 3}'),
('エアコン 6畳用', 'AC-6J', 'ELEC-AC-6TATAMI', 8, 6, 58000.00, 'ルームエアコン 6畳用', '{"brand": "GLOBAL", "capacity": "6畳", "energy_rating": "★★★★", "features": ["除湿", "空気清浄"], "warranty_years": 3}'),

-- 商品データ（ファッション - バッグ・靴・小物）
('レザーハンドバッグ', 'BAG-LEATHER-BK', 'FASHION-BAG-LEATHER', 12, 7, 24800.00, '本革ハンドバッグ ブラック', '{"brand": "ASIA", "material": "本革", "color": "ブラック", "size": "中", "features": ["内ポケット", "ショルダーストラップ"]}'),
('ビジネスシューズ', 'SHOES-BIZ-BK-26', 'FASHION-SHOES-BIZ-26', 12, 2, 18900.00, 'ビジネスシューズ ブラック 26cm', '{"brand": "ZAKKA", "type": "ビジネス", "color": "ブラック", "size": "26cm", "material": "本革"}'),
('腕時計 アナログ', 'WATCH-ANALOG-SV', 'FASHION-WATCH-ANALOG', 12, 2, 32000.00, 'アナログ腕時計 シルバー', '{"brand": "ZAKKA", "type": "アナログ", "color": "シルバー", "waterproof": "10気圧", "warranty_years": 2}'),

-- 商品データ（ホーム・キッチン - インテリア）
('ソファ 3人掛け', 'SOFA-3P-GY', 'HOME-SOFA-3PERSON', 14, 3, 89000.00, '3人掛けソファ グレー', '{"brand": "HOMELIFE", "seats": 3, "color": "グレー", "material": "ファブリック", "size": "幅180cm"}'),
('ダイニングテーブル', 'TABLE-DINING-4P', 'HOME-TABLE-DINING', 14, 3, 45000.00, 'ダイニングテーブル 4人用', '{"brand": "HOMELIFE", "seats": 4, "material": "木製", "size": "幅120cm×奥行80cm", "color": "ナチュラル"}'),
('ベッド シングル', 'BED-SINGLE-WH', 'HOME-BED-SINGLE', 14, 3, 38000.00, 'シングルベッド ホワイト', '{"brand": "HOMELIFE", "size": "シングル", "color": "ホワイト", "material": "木製", "mattress_included": false}'),
('カーテン 遮光', 'CURTAIN-BLOCK-BL', 'HOME-CURTAIN-BLOCK', 14, 3, 8900.00, '遮光カーテン ブルー', '{"brand": "HOMELIFE", "type": "遮光", "color": "ブルー", "size": "幅100cm×丈200cm", "light_blocking": "1級"}'),

-- 商品データ（エレクトロニクス - PC周辺機器）
('ワイヤレスマウス', 'MOUSE-WIRELESS-BK', 'PC-MOUSE-WIRELESS', 19, 1, 2980.00, 'ワイヤレスマウス ブラック', '{"brand": "TECH", "type": "ワイヤレス", "color": "ブラック", "dpi": "1600", "battery": "単3電池×2"}'),
('メカニカルキーボード', 'KB-MECHANICAL-WH', 'PC-KEYBOARD-MECH', 19, 1, 12800.00, 'メカニカルキーボード ホワイト', '{"brand": "TECH", "type": "メカニカル", "color": "ホワイト", "switch": "青軸", "backlight": true}'),
('Webカメラ 1080p', 'WEBCAM-1080P', 'PC-WEBCAM-1080P', 19, 1, 5980.00, 'Webカメラ 1080p対応', '{"brand": "TECH", "resolution": "1080p", "fps": "30fps", "microphone": "内蔵", "auto_focus": true}'),

-- 商品データ（ファッション - 季節商品）
('ダウンジャケット', 'JACKET-DOWN-NV', 'FASHION-JACKET-DOWN', 10, 2, 19800.00, 'ダウンジャケット ネイビー', '{"brand": "ZAKKA", "type": "ダウン", "color": "ネイビー", "size": "L", "season": "冬", "warmth_rating": "★★★★★"}'),
('サマードレス', 'DRESS-SUMMER-WH', 'FASHION-DRESS-SUMMER', 11, 7, 8900.00, 'サマードレス ホワイト', '{"brand": "ASIA", "type": "サマードレス", "color": "ホワイト", "size": "M", "season": "夏", "material": "リネン"}'),
('水着 ビキニ', 'SWIMWEAR-BIKINI-BL', 'FASHION-SWIM-BIKINI', 11, 7, 6800.00, 'ビキニ水着 ブルー', '{"brand": "ASIA", "type": "ビキニ", "color": "ブルー", "size": "M", "season": "夏", "uv_protection": true}'),

-- 商品データ（ホーム・キッチン - 日用品）
('掃除機 コードレス', 'VACUUM-CORDLESS', 'HOME-VACUUM-CORDLESS', 15, 3, 28000.00, 'コードレス掃除機', '{"brand": "HOMELIFE", "type": "コードレス", "battery_life": "60分", "weight": "2.1kg", "attachments": 5}'),
('空気清浄機', 'PURIFIER-AIR', 'HOME-PURIFIER-AIR', 15, 3, 18900.00, '空気清浄機 HEPA フィルター', '{"brand": "HOMELIFE", "filter": "HEPA", "coverage": "25畳", "features": ["PM2.5対応", "花粉対応"], "warranty_years": 2}'),
('加湿器 超音波式', 'HUMIDIFIER-ULTRA', 'HOME-HUMIDIFIER-ULTRA', 15, 3, 7800.00, '超音波式加湿器', '{"brand": "HOMELIFE", "type": "超音波式", "capacity": "4L", "coverage": "12畳", "timer": true}');

-- 商品の created_at / updated_at を 2023-01-01 に固定
-- （SCD Type 2 の snapshot で valid_from が注文日より過去になるように）
-- （DuckDB 版はトリガーがないため、そのまま UPDATE すれば明示した値が残る）
UPDATE product
   SET created_at = '2023-01-01 00:00:00'::timestamp,
       updated_at = '2023-01-01 00:00:00'::timestamp;

-- 在庫データ
INSERT INTO inventory (product_id, quantity_on_hand, quantity_reserved, reorder_level, reorder_quantity) VALUES
-- エレクトロニクス
(1, 25, 3, 10, 20),  -- MacBook Air
(2, 15, 2, 5, 15),   -- ThinkPad
(3, 30, 5, 15, 25),  -- Surface Laptop
(4, 40, 8, 20, 30),  -- VAIO
(5, 50, 10, 25, 40), -- iPhone 15 Pro
(6, 20, 4, 10, 20),  -- Galaxy S24
(7, 35, 7, 15, 30),  -- Pixel 8 Pro

-- ファッション
(8, 12, 2, 5, 15),   -- ビジネススーツ
(9, 80, 15, 30, 50), -- カジュアルシャツ
(10, 45, 8, 20, 35), -- デニムパンツ
(11, 25, 5, 10, 20), -- ワンピース
(12, 60, 12, 25, 40), -- ニットセーター
(13, 35, 7, 15, 25), -- スカート

-- ホーム・キッチン
(14, 18, 3, 8, 15),  -- 包丁セット
(15, 55, 11, 25, 40), -- 電気ケトル
(16, 22, 4, 10, 20), -- 食器セット

-- スポーツ・アウトドア
(17, 40, 8, 20, 30), -- ランニングシューズ
(18, 8, 1, 3, 10),   -- テント
(19, 28, 5, 12, 25), -- バックパック
(20, 100, 20, 50, 80), -- ヨガマット
(21, 75, 15, 30, 60),  -- ダンベルセット
(22, 90, 18, 40, 70),  -- 自転車 クロスバイク

-- 本・メディア
(23, 12, 2, 5, 10),   -- プログラミング入門書
(24, 8, 1, 3, 8),     -- 料理レシピ本
(25, 15, 3, 6, 12),   -- ビジネス書
(26, 25, 5, 10, 20),  -- 小説 ベストセラー
(27, 18, 3, 8, 15),   -- 健康・ダイエット本
(28, 30, 6, 12, 25),  -- 旅行ガイドブック

-- エレクトロニクス - 家電
(29, 22, 4, 10, 20),  -- 4K液晶テレビ
(30, 6, 1, 2, 8),     -- 冷蔵庫
(31, 10, 2, 4, 10),   -- 洗濯機
(32, 15, 3, 6, 12),   -- エアコン

-- ファッション - バッグ・靴・小物
(33, 45, 9, 20, 35),  -- レザーハンドバッグ
(34, 60, 12, 25, 50), -- ビジネスシューズ
(35, 20, 4, 8, 18),   -- 腕時計

-- ホーム・キッチン - インテリア
(36, 8, 1, 3, 10),      -- ソファ 3人掛け
(37, 120, 24, 50, 100), -- ダイニングテーブル
(38, 80, 16, 35, 70),   -- ベッド シングル
(39, 65, 13, 25, 50),   -- カーテン 遮光

-- エレクトロニクス - PC周辺機器
(40, 85, 17, 35, 70),  -- ワイヤレスマウス
(41, 25, 5, 10, 20),   -- メカニカルキーボード
(42, 40, 8, 18, 35),   -- Webカメラ

-- ファッション - 季節商品
(43, 20, 4, 8, 18),    -- ダウンジャケット
(44, 35, 7, 15, 30),   -- サマードレス
(45, 28, 6, 12, 25),   -- 水着

-- ホーム・キッチン - 日用品
(46, 18, 3, 8, 15),    -- 掃除機
(47, 22, 4, 10, 20),   -- 空気清浄機
(48, 35, 7, 15, 30);   -- 加湿器
