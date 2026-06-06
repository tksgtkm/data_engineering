# Change Data Capture with Debezium

PostgreSQL の変更を Debezium で捕捉し、Kafka 経由で Spark Structured Streaming に流して 30 秒ウィンドウで集計するサンプルです。

## 構成

| コンポーネント | イメージ / バージョン | 役割 |
| --- | --- | --- |
| Kafka | `bitnamilegacy/kafka:3.5` | メッセージブローカー (KRaft モード) |
| PostgreSQL | `quay.io/debezium/postgres:15` | ソース DB (`wal_level=logical` 設定済み) |
| Kafka Connect | `quay.io/debezium/connect:2.0` | Debezium による CDC ワーカー |
| data_generator | `waitingforcode/data-generator-blogging-platform:0.3-beta` | `visits` テーブルへ継続的にデータ投入 |
| Spark | PySpark 3.5.8 + `spark-sql-kafka-0-10_2.12:3.5.8` | ストリーミング集計 |

> **バージョン整合の注意**
> - Spark 本体と `spark-sql-kafka-0-10` コネクタは **完全に同じバージョン** で揃える (例: 3.5.8 同士)。コネクタは Maven Central に公開されているバージョンしか使えない (4.x 系は未公開)。
> - Kafka ブローカーと Spark クライアントはバージョンが違っても互換性で吸収されるが、ブローカーと Debezium Connect の組み合わせは相性が出やすい。動作確認の取れた `Kafka 3.5 × Debezium 2.0` を基準にするのが無難。

## 前提

- Docker / Docker Compose
- Python 3.11+ と PySpark 3.5.8 (`pip install 'pyspark==3.5.8'`)
- Java 17

## 手順

### 1. コンテナ起動

```bash
cd docker/
docker compose down --volumes; docker compose up
```

`--volumes` を付けることで、前回の Connect 内部トピックや DB の状態を引きずらずクリーンに起動できる。

#### 確認: コンテナと PostgreSQL

```bash
# 全コンテナが Up になっているか
docker ps

# 対象テーブルが作成されているか
docker exec -it cdc_postgres psql -U postgres -d dedp -c '\dt dedp_schema.*'

# 論理レプリケーションが有効か (logical であること)
docker exec -it cdc_postgres psql -U postgres -d dedp -c 'SHOW wal_level;'
```

### 2. Connect の準備完了を待つ

`docker compose up` の直後は Connect ワーカーがクラスタへの参加中で、コネクタ登録を受け付けられない。**必ず準備完了を確認してから次へ進む。**

```bash
# Herder started が出れば登録を受け付け可能
docker logs cdc_kafka_connect --tail 100 | grep -i "Herder started"

# REST API が [] を即座に返せば準備OK
curl -s http://localhost:8083/connectors
```

`curl` が `[]` を即座に返すようになるまで待つ (起動直後は数十秒〜数分かかることがある)。

### 3. Debezium コネクタを登録

```bash
cd docker/
curl -i -X POST -H "Accept:application/json" -H "Content-Type:application/json" \
  http://localhost:8083/connectors/ -d @register-postgresql-connector.json
```

`HTTP/1.1 201 Created` が返れば成功。

#### 確認: コネクタのステータスとトピック生成

```bash
# connector / tasks が両方 RUNNING であること
curl -s http://localhost:8083/connectors/visits-connector/status | jq

# dedp.dedp_schema.visits が一覧に現れること
docker exec docker_kafka_1 \
    kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### 4. Spark ストリーミング処理を実行

`visits_stream_processor.py` は、作成イベント (`filter('visit.payload.op = "c"')`) を抽出し、`event_time` を 30 秒ウィンドウで集計するコンシューマ。

```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8 \
  visits_stream_processor.py
```

コンソールにウィンドウごとのカウントが出力される。

### 5. (任意) 生の CDC イベントを確認

Debezium が実際に流している JSON (op / before / after を含む) を直接確認できる。Spark 側の出力が空のときの切り分けに有用。

```bash
docker exec -ti docker_kafka_1 kafka-console-consumer.sh \
    --bootstrap-server kafka:9092 \
    --from-beginning \
    --property print.key=true \
    --topic dedp.dedp_schema.visits
```

## よくあるエラーと対処

### `pyspark.errors...JAVA_GATEWAY_EXITED: Java gateway process exited`

JVM の起動失敗。主な原因:

- **Java バージョン不整合**: Spark 3.5.x は Java 17 推奨。`java -version` と `echo $JAVA_HOME` を確認。
- **Kafka コネクタのバージョン不整合**: `spark.jars.packages` のバージョンを Spark 本体に一致させる。
- **`SPARK_HOME` の競合**: pip 版 PySpark だけを使うなら `unset SPARK_HOME`。

切り分けには、まずパッケージ指定なしで JVM が起動するか確認する:

```bash
python -c "from pyspark.sql import SparkSession; s=SparkSession.builder.master('local[*]').getOrCreate(); print(s.version); s.stop()"
```

### `unresolved dependency: org.apache.spark#spark-sql-kafka-0-10_2.12;X.Y.Z: not found`

指定したコネクタのバージョンが Maven Central に存在しない。公開済みバージョンを確認して指定し直す:

```bash
# 公開されているバージョン一覧
curl -s https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/maven-metadata.xml
```

PySpark 本体側も、コネクタが公開されているバージョン (例: 3.5.8) に合わせる。

### `AnalysisException: Failed to find data source: kafka`

Kafka コネクタの JAR がロードされていない。

- `spark-submit --packages ...` で実行する (素の `python script.py` よりパッケージ解決が確実)。
- 同一プロセスで既存の SparkSession を使い回していないか確認 (`spark.jars.packages` は最初の `getOrCreate()` 時にしか効かない)。
- 起動ログに `spark-sql-kafka-0-10 added as a dependency` と resolution report が出ているか確認。

### `Request timed out. The worker is currently ensuring membership in the cluster`

Connect ワーカーがまだクラスタ参加中。**待ってから登録する** (ステップ 2 参照)。

エラーメッセージ内の開始時刻が固定されたまま変わらない、またはログに次が繰り返し出る場合はストール状態:

```
[AdminClient ...] Rebootstrapping with Cluster(id = null, ... controller = null)
```

この場合はブローカーと Connect のバージョン相性を疑い、`docker compose down --volumes` でクリーンに作り直す。動作確認の取れた `Kafka 3.5 × Debezium 2.0` の組み合わせに戻すのが確実。

### `UnknownTopicOrPartitionException: This server does not host this topic-partition`

Spark が subscribe しているトピックが未生成。Debezium コネクタが登録・RUNNING で、`kafka-topics.sh --list` に `dedp.dedp_schema.visits` が現れていることを確認する (ステップ 3)。コネクタが流し始めて初めてトピックが作られる。

### コネクタ登録時に `curl: Failed to open ... .json`

`-d @ファイル名` のパスが実在しない。JSON ファイルのある `docker/` ディレクトリに移動してから実行するか、正しい相対 / 絶対パスを指定する。