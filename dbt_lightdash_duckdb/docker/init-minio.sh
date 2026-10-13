#!/bin/sh
# MinIO を起動し、Lightdash 用のバケットを作成する
# （lightdash/lightdash リポジトリの docker/init-minio.sh を簡略化したもの）
set -e

minio server /data --console-address ":9001" &

until mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
  sleep 1
done

IFS=','
for bucket in $MINIO_DEFAULT_BUCKETS; do
  [ -n "$bucket" ] || continue
  mc mb -p "local/$bucket" >/dev/null 2>&1 || echo "bucket '$bucket' already exists"
  # 結果ファイルは 1 日で自動削除
  mc ilm rule add --expire-days 1 "local/$bucket" >/dev/null 2>&1 || true
done

echo "MinIO ready"
wait
