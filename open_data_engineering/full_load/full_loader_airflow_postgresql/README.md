# Full Loader - データ公開（Data Exposition）デモ手順

## 概要

Apache Airflow を使った「フルローダー（Full Loader）」パターンのデモです。
PostgreSQL へのデータロード時に、**タイムスタンプ付きの隠しテーブル → View への昇格**という2段階の手法を使い、データの差し替えをアトミックに行います。

### 処理の流れ

```
入力CSVファイル待機（FileSensor）
    ↓
タイムスタンプ付き新テーブルを作成してデータをロード
（この時点ではまだ非公開）
    ↓
CREATE OR REPLACE VIEW devices でViewを差し替え
（ここで初めてユーザーから見える）
```

### 重要な設計ポイント

- **`mode='reschedule'`** — ファイル待機中に Worker スロットを占有しない
- **View による公開制御** — テーブルを直接差し替えるのではなく、View を切り替えることでダウンタイムゼロを実現
- **ロールバック可能** — 旧タスクを再実行するだけで以前のデータに戻せる（条件あり。後述の注意事項を参照）

### ライブラリ構成

```
apache-airflow==3.2.1
apache-airflow-providers-postgres==6.6.3
apache-airflow-providers-fab==3.6.2
pendulum==3.2.0
```

---

## 事前準備

### ディレクトリ構成

```
docker/
├── dataset/
│   ├── docker-compose.yml
│   └── generation_configuration.yaml
└── postgresql/
    ├── docker-compose.yml
    └── init.sql
dags/
├── devices_loader.py
├── macros.py
└── sql/
    ├── load_file_to_device_table.sql
    └── expose_new_table.sql
```

---

## 手順

### ステップ1：データセットの生成

```bash
cd docker/dataset
mkdir -p /tmp/dedp/full-loader/data-exposition/input
docker-compose down --volumes; docker-compose up
```

データが生成されたことを確認します。

```bash
ls -la /tmp/dedp/full-loader/data-exposition/input/dataset.csv
```

### ステップ2：PostgreSQL の起動

⚠️ **ステップ1でデータセットが生成されていることを必ず確認してから起動してください。**
PostgreSQL コンテナはホストの `/tmp/dedp/full-loader/data-exposition/input` をコンテナ内の `/data_to_load` にマウントします。データが存在しないと DAG 実行時にエラーになります。

```bash
cd ../postgresql
docker-compose down --volumes; docker-compose up
```

コンテナ内からファイルが見えることを確認します。

```bash
docker exec -ti dedp_test_full_loader_postgresql ls -la /data_to_load/
```

`dataset.csv` が表示されれば OK です。

### ステップ3：Apache Airflow の起動

```bash
# ⚠️ 先に仮想環境を有効化する
source venv/bin/activate

./start.sh
```

**Airflow 3.2.1 での注意：** `airflow webserver` コマンドは廃止されています。`start.sh` の中身が `airflow webserver` を呼んでいる場合は `airflow api-server` に書き換えてください。

### ステップ4：Airflow UI にアクセス

ブラウザで `http://localhost:8080/` を開き、ログインします。

- ID: `dedp`
- PW: `dedp`

### ステップ5：DAG の確認

`http://localhost:8080/dags/devices_loader` を開きます。

Airflow 3 では DAG 詳細ページに以下のタブがあります。

- **Overview** — 概要ダッシュボード
- **Grid** — 各 DAG ランとタスクの状態をマトリクス表示
- **Graph** — タスクの依存関係をグラフ表示

**Graph** タブを開くと、以下の3ステップの構成が確認できます。

```
input_data_sensor → load_data_to_table → load_data_to_the_final_table
```

### ステップ6：DAG の実行

Airflow UI で `devices_loader` DAG の **トグルを ON** にします。
`start_date` が4日前、`schedule=@daily` のため、3回の DAG ランが自動的に実行されます。

**Grid** タブで全タスクが緑（成功）になるまで待ちます。

### ステップ7：データの確認

```bash
docker exec -ti dedp_test_full_loader_postgresql psql --user dedp_test -d dedp_test
```

```sql
SELECT * FROM devices;
```

50件のデバイスデータが表示されれば成功です。`\q` で psql を抜けます。

---

## 障害シミュレーション

### ステップ8：空ファイルの投入

ヘッダーのみの空 CSV を作成します。

```bash
echo "type;full_name;version" > /tmp/dedp/full-loader/data-exposition/input/dataset.csv
```

### ステップ9：最後の DAG ランを再実行

Airflow UI で以下の操作を行います。

1. `devices_loader` の **Grid** タブを開く
2. **一番右の列**（最新の DAG ラン）のいずれかのタスクセルをクリック
3. 表示されるパネルで **「Clear Task Instance」**（日本語UIの場合は「タスクインスタンスをクリア」）をクリック
4. 確認して実行

**「Clear Task Instance」とは？**
タスクの実行状態（ステータス）を「未実行」にリセットする操作です。ジョブの履歴は消えません。スケジューラーが再検知して自動的に再実行します。

### ステップ10：データが空になったことを確認

```bash
docker exec -ti dedp_test_full_loader_postgresql psql --user dedp_test -d dedp_test
```

```sql
SELECT * FROM devices;
```

```
 type | full_name | version
------+-----------+---------
(0 rows)
```

---

## ロールバック（復旧）

### ステップ11：前のバージョンに戻す

Airflow UI で以下の操作を行います。

1. `devices_loader` の **Grid** タブを開く
2. **右から2番目の列**（1つ前の DAG ラン）を探す
3. その列の中から **`load_data_to_the_final_table`** タスクのセルをクリック
4. **「Clear Task Instance」** をクリック
5. 確認して実行

### ステップ12：データが復活したことを確認

```bash
docker exec -ti dedp_test_full_loader_postgresql psql --user dedp_test -d dedp_test
```

```sql
SELECT * FROM devices;
```

50件のデータが戻っていればロールバック成功です。

---

## ⚠️ ロールバックに関する重要な注意事項

### クリアするタスクを間違えないこと

ロールバック時は必ず **`load_data_to_the_final_table` だけ**をクリアしてください。

`load_data_to_table` をクリアしてしまうと、以下の SQL が実行されます。

```sql
DROP VIEW IF EXISTS devices;
DROP TABLE IF EXISTS devices_YYYYMMDD;
```

**View と既存テーブルが削除されてしまい、復旧できなくなります。**

### テーブル名は日付単位

テーブル名は `devices_YYYYMMDD`（例: `devices_20260508`）という日付単位の命名です。同じ日に複数回実行すると同じテーブル名になり上書きされます。**異なる日付の DAG ラン間でのみロールバックが有効です。**

### テーブルの存在確認方法

ロールバック前に、前回のテーブルが残っているか確認してください。

```sql
-- テーブル一覧を確認
\dt

-- 特定のテーブルの件数を確認
SELECT count(*) FROM devices_20260507;
```

---

## トラブルシューティング

### `could not open file "/data_to_load/dataset.csv": No such file or directory`

PostgreSQL コンテナ内にデータファイルがマウントされていません。

1. ホスト側にファイルがあるか確認
```bash
   ls -la /tmp/dedp/full-loader/data-exposition/input/dataset.csv
```
2. ファイルが無ければデータセットを再生成
```bash
   cd docker/dataset
   docker-compose down --volumes; docker-compose up
```
3. PostgreSQL コンテナを再起動（**データ生成後に**再起動すること）
```bash
   cd docker/postgresql
   docker-compose down --volumes; docker-compose up
```
4. コンテナ内から確認
```bash
   docker exec -ti dedp_test_full_loader_postgresql ls -la /data_to_load/
```

### DAG を停止したい

```bash
# CLI で停止
airflow dags pause devices_loader
```

または Airflow UI の DAG 一覧画面で `devices_loader` のトグルを OFF にしてください。

### ロールバックできない（テーブルが1つしかない）

データセットを再生成して再実行するのが確実な復旧方法です。

```bash
cd docker/dataset
docker-compose down --volumes; docker-compose up

cd ../postgresql
docker-compose down --volumes; docker-compose up
```

その後、Airflow UI で DAG ランのタスクをクリアして再実行してください。

---

## DAG の構成詳細

### devices_loader.py

| タスク | 説明 |
|---|---|
| `input_data_sensor` | 入力 CSV ファイルの存在を待機（`mode='reschedule'`） |
| `load_data_to_table` | タイムスタンプ付きテーブルを作成しデータをロード |
| `load_data_to_the_final_table` | `CREATE OR REPLACE VIEW devices` で View を差し替え |

### テーブル命名規則

`get_table_name(ds_nodash)` マクロにより `devices_YYYYMMDD` の形式で生成されます。

### SQL の内容

**load_file_to_device_table.sql:**

```sql
{% set table_name = get_table_name(ds_nodash) %}
DROP VIEW IF EXISTS devices;
DROP TABLE IF EXISTS {{ table_name }};
CREATE TABLE {{ table_name }} (...);
COPY {{ table_name }} FROM '/data_to_load/dataset.csv' CSV DELIMITER ';' HEADER;
```

**expose_new_table.sql:**

```sql
{% set table_name = get_table_name(ds_nodash) %}
CREATE OR REPLACE VIEW devices AS SELECT * FROM {{ table_name }}
```