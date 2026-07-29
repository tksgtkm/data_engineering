"""
Spark 3.5 + Delta Lake 3.3 + Apache Sedona 1.7 のセッションビルダ。

前提
----
  pip install "pyspark==3.5.*" delta-spark==3.3.0 apache-sedona==1.7.2 shapely
  Java 17

バージョンを動かすときの鉄則
--------------------------
  Sedona が律速。Sedona 1.7.x は Spark 3.3/3.4/3.5 までしか対応していないため、
  Spark 4.0 / Delta 4.0 には上げられない。Spark 3.5 で固定すること。

  pip 版 pyspark は Scala 2.12 / Hadoop 3.3.4 同梱。
  よって hadoop-aws も 3.3.4 でなければならない（混ぜると NoSuchMethodError）。
"""

from __future__ import annotations

import os

from pyspark.sql import SparkSession

# --------------------------------------------------------------------------
# バージョン固定
# --------------------------------------------------------------------------
SCALA = "2.12"                    # pip 版 pyspark は 2.12 ビルド
SPARK_MINOR = "3.5"

DELTA_VERSION = "3.3.0"           # Spark 3.5 系。4.0.0 は Spark 4.0 専用なので不可
SEDONA_VERSION = "1.7.2"
GEOTOOLS_WRAPPER = "1.7.2-28.5"   # ★Sedona とペアのバージョン文字列。docs で要確認
HADOOP_AWS_VERSION = "3.3.4"      # pyspark 3.5.x 同梱の Hadoop と完全一致させる
AWS_SDK_VERSION = "1.12.262"      # hadoop-aws 3.3.4 がビルドされた SDK バージョン

OVERTURE_BUCKET = "overturemaps-us-west-2"
OVERTURE_REGION = "us-west-2"

MAVEN_PACKAGES = [
    f"io.delta:delta-spark_{SCALA}:{DELTA_VERSION}",
    f"org.apache.sedona:sedona-spark-shaded-{SPARK_MINOR}_{SCALA}:{SEDONA_VERSION}",
    f"org.datasyslab:geotools-wrapper:{GEOTOOLS_WRAPPER}",
    f"org.apache.hadoop:hadoop-aws:{HADOOP_AWS_VERSION}",
    f"com.amazonaws:aws-java-sdk-bundle:{AWS_SDK_VERSION}",
]

# ★ここが典型的な事故ポイント：片方だけ書くともう片方が黙って無効になる
SQL_EXTENSIONS = [
    "io.delta.sql.DeltaSparkSessionExtension",
    "org.apache.sedona.sql.SedonaSqlExtensions",
]


def build_spark(
    app_name: str = "overture-estat",
    *,
    warehouse_dir: str | None = None,
    minio_endpoint: str | None = None,
    minio_access_key: str | None = None,
    minio_secret_key: str | None = None,
    driver_memory: str = "8g",
    shuffle_partitions: int = 32,
    local_cores: str = "*",
) -> SparkSession:
    """Delta + Sedona + 二系統 S3 を有効にした SparkSession を返す。

    MinIO の資格情報が渡されなければ S3A のデフォルトは設定せず、
    Overture の匿名アクセスだけを構成する（ローカル FS で完結する開発時向け）。
    """
    warehouse_dir = warehouse_dir or os.path.expanduser("~/develop/spark-warehouse")

    builder = (
        SparkSession.builder.appName(app_name)
        .master(f"local[{local_cores}]")
        .config("spark.jars.packages", ",".join(MAVEN_PACKAGES))
        .config("spark.sql.extensions", ",".join(SQL_EXTENSIONS))
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.sql.warehouse.dir", warehouse_dir)
        # --- Sedona のジオメトリ直列化 -----------------------------------
        # 落ちる場合はこの 2 行を外す（Sedona 側の UDT だけでも動作する）
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config(
            "spark.kryo.registrator",
            "org.apache.sedona.core.serde.SedonaKryoRegistrator",
        )
        # --- ローカル実行時のチューニング --------------------------------
        .config("spark.driver.memory", driver_memory)
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
        .config("spark.sql.parquet.filterPushdown", "true")
        .config("spark.sql.files.maxPartitionBytes", "134217728")  # 128MB
    )

    # ------------------------------------------------------------------
    # S3A: バケット単位のオーバーライドで Overture(匿名) と MinIO を共存させる
    #   fs.s3a.bucket.<BUCKET>.<KEY> は fs.s3a.<KEY> を上書きする
    # ------------------------------------------------------------------

    # 既定値 = MinIO（書き込み先）
    if minio_endpoint:
        builder = (
            builder.config("spark.hadoop.fs.s3a.endpoint", minio_endpoint)
            .config("spark.hadoop.fs.s3a.path.style.access", "true")
            .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
            .config(
                "spark.hadoop.fs.s3a.aws.credentials.provider",
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
            )
            .config("spark.hadoop.fs.s3a.access.key", minio_access_key or "")
            .config("spark.hadoop.fs.s3a.secret.key", minio_secret_key or "")
        )

    # Overture 専用オーバーライド = 本物の S3 に匿名アクセス
    b = f"spark.hadoop.fs.s3a.bucket.{OVERTURE_BUCKET}"
    builder = (
        builder.config(
            f"{b}.aws.credentials.provider",
            "org.apache.hadoop.fs.s3a.AnonymousAWSCredentialsProvider",
        )
        .config(f"{b}.endpoint", f"s3.{OVERTURE_REGION}.amazonaws.com")
        .config(f"{b}.endpoint.region", OVERTURE_REGION)
        .config(f"{b}.path.style.access", "false")
        .config(f"{b}.connection.ssl.enabled", "true")
        # 列指向読み出しでは random シークが圧倒的に速い（Hadoop 3.3 系のキー名）
        .config(f"{b}.experimental.input.fadvise", "random")
        .config(f"{b}.connection.maximum", "128")
        .config(f"{b}.threads.max", "64")
    )

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


# --------------------------------------------------------------------------
# Overture のパス組み立て
# --------------------------------------------------------------------------
def overture_path(release: str, theme: str, type_: str) -> str:
    """例: overture_path("2026-07-22.0", "places", "place")"""
    return (
        f"s3a://{OVERTURE_BUCKET}/release/{release}"
        f"/theme={theme}/type={type_}/"
    )


# 日本全域のバウンディングボックス（南西諸島・小笠原を含む）
JAPAN_BBOX = dict(xmin=122.0, xmax=154.0, ymin=20.0, ymax=46.0)
# 大阪府あたり（開発時の絞り込み用）
OSAKA_BBOX = dict(xmin=135.0, xmax=136.0, ymin=34.2, ymax=35.1)
# 京阪神 = 2府4県（大阪・京都・兵庫・奈良・滋賀・和歌山）を包含する矩形。
# 淡路島・紀伊半島南部・日本海側（丹後/但馬）まで入る。約 56,000 km²。
KEIHANSHIN_BBOX = dict(xmin=134.2, xmax=136.5, ymin=33.4, ymax=35.8)


def mesh1_tiles(bbox: dict) -> list[str]:
    """bbox が跨ぐ 1 次メッシュ(80km)のコード一覧。

    e-Stat のメッシュ統計・境界データは 1 次/2 次メッシュ単位の
    ZIP で配布されるため、「どれを落とせばよいか」の算出に使う。
    """
    p0, p1 = int(bbox["ymin"] * 60 // 40), int(bbox["ymax"] * 60 // 40)
    u0, u1 = int(bbox["xmin"] - 100), int(bbox["xmax"] - 100)
    return [f"{p}{u}" for p in range(p0, p1 + 1) for u in range(u0, u1 + 1)]


def bbox_filter(bbox: dict) -> str:
    """Parquet の row-group 統計が効く形の述語。

    ST_Intersects を先に書くと全件デシリアライズが走るので、
    まずこの数値比較で落とすこと。
    """
    return (
        f"bbox.xmin < {bbox['xmax']} AND bbox.xmax > {bbox['xmin']} AND "
        f"bbox.ymin < {bbox['ymax']} AND bbox.ymax > {bbox['ymin']}"
    )