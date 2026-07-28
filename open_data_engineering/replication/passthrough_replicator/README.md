# パススルーレプリケータ (Passthrough replicator)

## JSON のレプリケーション

1. データセットを生成し、Apache Kafka ブローカーを起動する:

```bash
cd docker
mkdir -p /tmp/dedp/ch02/replication/passthrough-replicator/input
docker-compose down --volumes; docker-compose up
```

2. [dataset_replicator_raw.py](dataset_replicator_raw.py) を開く
   * これは JSON や CSV といったテキストファイル形式向けのレプリケータである。ただしデータが変質する問題を避けるため、JSON リーダーや CSV リーダーは使っていない
     * 代わりに、最も基本的な `text` API を使用している
     * 💡 分散処理が不要であれば、このパターンはコピー用の CLI でも実装できる
3. `dataset_replicator_raw.py` を実行する
4. `dataset_reader_raw.py` を実行して同期結果を検証する

## Apache Kafka のレプリケーション

1. Docker コンテナを起動したままにして、デモ用のトピックを作成する:

```bash
docker exec -ti passthrough_replicator_kafka kafka-topics.sh --topic events --delete --bootstrap-server localhost:9094
docker exec -ti passthrough_replicator_kafka kafka-topics.sh --topic events --create --bootstrap-server localhost:9094 --partitions 2
docker exec -ti passthrough_replicator_kafka kafka-topics.sh --topic events-replicated --delete --bootstrap-server localhost:9094
docker exec -ti passthrough_replicator_kafka kafka-topics.sh --topic events-replicated --create --bootstrap-server localhost:9094 --partitions 2
```

2. [dataset_replicator_kafka.py](dataset_replicator_kafka.py) を開く
   * ここでのレプリケーションは、変換を一切伴わないデータコピーであるにもかかわらず、前の例ほど単純ではない
     * 難しさは「順序」に起因する。順序は Apache Kafka のトピックに本質的に備わった性質である。なお、前の例のファイルについても順序を保持する必要が生じる場合がある
   * このジョブも読み書きには最も素朴な IO API を使っているが、`events.sortWithinPartitions('offset', ascending=True).drop('offset')` として定義されたローカルソートを付加している
   * ⚠️ リトライが発生した場合、このレプリケーションは品質上の問題を引き起こす可能性がある
3. `dataset_replicator_kafka.py` を実行する
4. [kafka_data_producer.py](kafka_data_producer.py) を開く
   * これがデータジェネレータである。順序の特殊性をよりよく示すため、ここでは通常のデータジェネレータは使っていない
   * このジョブはレコードキーによるパーティショニングを利用し、関連するイベントをすべて同一パーティションに書き込む
5. `dataset_reader_kafka.py` と `dataset_reader_kafka_raw.py` を実行する
6. `kafka_data_producer.py` を数回実行する
   * プロデュースされたレコードとレプリケートされたレコードが一致していることを確認できるはずである

---

# トラブルシューティング

実行時に遭遇したエラーと、その原因・対処のまとめ。

## 1. `NoSuchMethodError: scala.Predef$.wrapRefArray` (Scala バイナリ非互換)

### 症状

`kafka_data_producer.py` の `.save()` で以下が発生する。

```
py4j.protocol.Py4JJavaError: An error occurred while calling o65.save.
: java.lang.NoSuchMethodError: 'scala.collection.mutable.WrappedArray scala.Predef$.wrapRefArray(java.lang.Object[])'
	at org.apache.spark.sql.kafka010.KafkaSourceProvider$.<init>(KafkaSourceProvider.scala:545)
```

### 原因

Spark 本体と Kafka コネクタで **Scala のバイナリバージョンが食い違っている**。

* 本教材のオリジナルは Spark 3.5 / Scala 2.12 前提で、`spark-sql-kafka-0-10_2.12:3.5.0` を指定している
* 一方、手元の PySpark は **4.1.1**。Spark 4.x は **Scala 2.13 ビルドのみ**が提供される

`Predef.wrapRefArray` の戻り値型は Scala 2.12 では `WrappedArray`、2.13 では `ArraySeq` に変更された。2.12 でコンパイルされたコネクタが 2.13 ランタイム上で旧シグネチャを呼び出すため、`NoSuchMethodError` になる。

スタックトレース中の `org.apache.spark.sql.classic.DataFrameWriter` が Spark 4 系である決定的な手がかり（`sql.classic` パッケージは Spark 4 で導入された）。冒頭の `WARNING: Using incubator modules: jdk.incubator.vector` も Spark 4 系の特徴。

### 対処

まず PySpark のバージョンを確認する。

```bash
python -c "import pyspark; print(pyspark.__version__)"
```

出たバージョンに **完全一致**させ、Scala サフィックスも `_2.13` にする。

```python
spark = (
    SparkSession.builder
    .master('local[*]')
    .config('spark.jars.packages',
            'org.apache.spark:spark-sql-kafka-0-10_2.13:4.1.1')  # ← pyspark と同一バージョン
    .getOrCreate()
)
```

`spark-submit` の場合:

```bash
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.1.1 kafka_data_producer.py
```

古い jar が Ivy キャッシュに残っていると解決順序次第で再発するので、切り替え時は掃除しておく。

```bash
rm -rf ~/.ivy2.5.2/cache/org.apache.spark/*kafka* ~/.ivy2.5.2/jars/*kafka*
```

### 教材どおり Spark 3.5 で揃える選択肢

本教材は 3.5 系を前提に書かれているため、環境側を落とすほうが結果的にトラブルが少ない場合がある。

```bash
pip install "pyspark==3.5.6"
```

Kafka に限らず Iceberg のランタイム jar なども Spark バージョンごとにビルドが分かれており、`iceberg-spark-runtime-3.5_2.12` のような命名になる。教材を最後まで通すなら 3.5 系で統一しておくと、バージョン差の切り分けに時間を取られずに済む。

### 教訓

**Spark 本体・Scala バイナリ版・コネクタのバージョンは常に三点セットで一致させる。** 3.5 系コネクタを 4.x で使う、`_2.12` を 2.13 ランタイムで使う、はいずれも不可。

---

## 2. `Failed to create new KafkaAdminClient` (bootstrap.servers の書式ミス)

### 症状

`dataset_reader_kafka.py` の `awaitTermination()` で以下が発生する。

```
pyspark.errors.exceptions.captured.StreamingQueryException: [STREAM_FAILED] Query [...]
terminated with exception: Failed to create new KafkaAdminClient SQLSTATE: XXKST
```

### 原因

**`bootstrap.servers` の区切り文字がコロンではなくピリオドになっていた。**

```python
.option('kafka.bootstrap.servers', 'localhost.9094')   # ✗ ピリオド
.option('kafka.bootstrap.servers', 'localhost:9094')   # ✓ コロン
```

`localhost.9094` は単一のホスト名としてパースされ、DNS で解決できずに `ConfigException: No resolvable bootstrap urls given in bootstrap.servers` が発生する。これが `KafkaAdminClient` のコンストラクタ内で起きるため、外側からは `Failed to create new KafkaAdminClient` としか見えない。

### 診断のコツ

`Failed to create new KafkaAdminClient` は**ラッパー例外であり、それ自体には情報がない**。真の原因は `Caused by:` にある。PySpark の例外変換で切り落とされるため、以下で JVM 側のスタックトレースを出す。

```python
spark = (
    SparkSession.builder
    .config('spark.sql.pyspark.jvmStacktrace.enabled', 'true')
    .getOrCreate()
)
```

### `Caused by` 別の切り分け表

| `Caused by` の内容 | 原因 |
|---|---|
| `No resolvable bootstrap urls given in bootstrap.servers` | ホスト名が解決できない。今回のタイポ、または Docker のサービス名（`kafka:9092`）をホスト側から指定している |
| `Invalid url in bootstrap.servers` | `http://` などのスキームを付けている、末尾にカンマが残っている、ポートを書き忘れている |
| `TimeoutException` / 接続はできるが応答がない | ブローカー側の `advertised.listeners` 設定漏れ |

### 関連する注意点

* Spark から Kafka クライアントに渡す設定は必ず **`kafka.` プレフィックス**を付ける。`.option('bootstrap.servers', ...)` では Spark 側のオプションとして無視される
* 本デモのブローカー外部リスナーは **9094**（README の `kafka-topics.sh --bootstrap-server localhost:9094` と一致）。9092 ではない
* 同じ文字列を他のスクリプトにコピペしていないか横断確認する

### Spark を挟まない切り分け

```bash
# ポートが開いているか
nc -zv localhost 9094

# トピック一覧が引けるか
docker exec -ti passthrough_replicator_kafka kafka-topics.sh --list --bootstrap-server localhost:9094
```

ここが通るのに Spark からだけ失敗するなら、原因はスクリプト側（書式ミスかプレフィックス忘れ）。CLI も失敗するならブローカー側。

---

## 3. `Unable to load native-hadoop library` (WARN / 対処不要)

```
WARN NativeCodeLoader: Unable to load native-hadoop library for your platform... using builtin-java classes where applicable
```

Hadoop のネイティブライブラリ（C 実装の圧縮コーデックや CRC 計算）が見つからないため Java 実装で代替する、という通知。**エラーではない。**

pip 版 PySpark にはそもそもネイティブライブラリが同梱されていないため、この環境では必ず出る。ローカル開発では実質無害で、対処は不要。

---

## 4. `Service 'SparkUI' could not bind on port 4040` (Spark プロセスの残留)

### 症状

```
WARN Utils: Service 'SparkUI' could not bind on port 4040. Attempting port 4041.
WARN Utils: Service 'SparkUI' could not bind on port 4041. Attempting port 4042.
WARN Utils: Service 'SparkUI' could not bind on port 4042. Attempting port 4043.
```

### 意味

これも WARN であり処理は継続するが、**Spark プロセスが 3 つ以上生き残っている**サインである。4040 から順に空きポートを探し、4043 まで到達している。

主な原因は、`awaitTermination()` がストリーミングクエリを永続的にブロックすること。`dataset_reader_kafka.py` を別ターミナルで動かしたまま放置すると、そのセッションが 4040 を掴み続ける。加えて、途中で失敗した実行の JVM が残っている場合もある。

### 確認と掃除

```bash
# 生きている Spark の JVM を確認
jps -l | grep -i spark

# あるいはポート側から
ss -ltnp | grep -E '404[0-9]'

# 不要なものを落とす
kill <PID>
```

### 予防策

学習中の動作確認であれば、タイムアウトを付けると放置事故が減る。

```python
write_data_stream.start().awaitTermination(timeout=60)
```

本デモは Kafka のプロデューサ・レプリケータ・リーダーを**同時に複数走らせる**構成であり、いずれも無限にブロックする。プロセス数が増えてきたら Procfile 化して `overmind` で束ねるほうが管理しやすい。

---

## 5. その他の注意点

### ディレクトリ名のタイポ

セットアップ手順のパスは `/tmp/**dedp**/ch02/...` である。`depd` と打ち間違えるとレプリケータが入力を見つけられず、原因の分かりにくい「データが流れてこない」状態になる。作成後に確認しておく。

```bash
ls -d /tmp/dedp/ch02/replication/passthrough-replicator/input
```

### トピックの再作成

README の `kafka-topics.sh --delete` は、トピックが存在しない初回実行では以下のようなエラーを返す。これは想定内であり、続く `--create` が通れば問題ない。

```
Error while executing topic command : Topic 'events' does not exist as expected
```

### `startingOffsets` の表記

`'EARLIEST'` は大文字でも動作する（Spark 側で小文字化して判定される）が、慣例的には小文字 `'earliest'` が一般的。教材やドキュメントと表記を揃えておくと後で検索しやすい。

### 実行順序

Kafka レプリケーションのデモは、以下の順に立ち上げると挙動を追いやすい。

1. `dataset_replicator_kafka.py`（`events` → `events-replicated`）
2. `dataset_reader_kafka.py` / `dataset_reader_kafka_raw.py`（コンシューマ）
3. `kafka_data_producer.py`（プロデューサ、数回実行）

レプリケータとコンシューマを先に起動しておかないと、`startingOffsets` の設定次第では既存レコードを取りこぼす。