# dataflow

Python / MySQL / PostgreSQL の開発環境を Docker で構築したプロジェクトです。

## 構成

```
dataflow/
├── .devcontainer/
│   └── devcontainer.json    # VS Code Dev Containers 設定
├── docker-compose.yml       # サービス定義
├── Dockerfile.python        # Python 3.11 環境
├── requirements.txt         # Python パッケージ
├── init/
│   ├── mysql/01_init.sql    # MySQL 初期スキーマ
│   └── postgres/01_init.sql # PostgreSQL 初期スキーマ
└── scripts/
    └── db_check.py          # 接続確認スクリプト
```

## 起動・停止

```bash
# 起動（初回はイメージのビルドも行う）
docker compose up -d --build

# 起動（2回目以降）
docker compose up -d

# 停止
docker compose down

# 停止してボリューム（データ）も削除
docker compose down -v
```

## 接続情報

| 項目 | MySQL | PostgreSQL |
|---|---|---|
| ホスト | localhost | localhost |
| ポート | 3306 | 5432 |
| DB名 | dataflow | dataflow |
| ユーザ | dataflow_user | dataflow_user |
| パスワード | dataflow_pass | dataflow_pass |

## Python スクリプトの実行

`scripts/` ディレクトリに置いたスクリプトをコンテナ内で実行できます。

```bash
docker exec -it dataflow_python python scripts/db_check.py
```

コンテナ内のシェルに入る場合：

```bash
docker exec -it dataflow_python bash
```

## DB シェルへの接続

```bash
# MySQL
docker exec -it dataflow_mysql mysql -u dataflow_user -pdataflow_pass dataflow

# PostgreSQL
docker exec -it dataflow_postgres psql -U dataflow_user -d dataflow

# DuckDB（dbt のビルド成果物 dataflow.duckdb に接続）
docker exec -it -w /app dataflow_python duckdb dataflow.duckdb
```

## dbt の実行

`dbt-core` / `dbt-duckdb` は `dataflow_python` コンテナにインストール済みです。
`profiles.yml` はプロジェクト直下にあるため、`--profiles-dir .` を付けて実行します。

```bash
# パッケージ取得（packages.yml）
docker exec -w /app dataflow_python dbt deps --profiles-dir .

# 接続確認
docker exec -w /app dataflow_python dbt debug --profiles-dir .

# seed → run → test を一括で実行
docker exec -w /app dataflow_python dbt build --profiles-dir .
```

ビルドに成功すると、プロジェクト直下に `dataflow.duckdb` が生成されます。

## DuckDB CLI の使い方

`dataflow_python` コンテナには DuckDB CLI（v1.5.2）が同梱されています。

```bash
# 対話シェル（.tables / .schema <table> / .quit などが使える）
docker exec -it -w /app dataflow_python duckdb dataflow.duckdb

# ワンライナーで SQL を実行
docker exec -w /app dataflow_python duckdb dataflow.duckdb \
    -c "SELECT * FROM user_metrics_final_report LIMIT 5;"

# 出力フォーマットを切り替える
docker exec -w /app dataflow_python duckdb dataflow.duckdb -markdown -c "..."
docker exec -w /app dataflow_python duckdb dataflow.duckdb -csv      -c "..."
docker exec -w /app dataflow_python duckdb dataflow.duckdb -json     -c "..."
```

ホスト側 `~/.bashrc` などにエイリアスを切っておくと短く呼べます。

```bash
alias duck='docker exec -it -w /app dataflow_python duckdb dataflow.duckdb'
# duck                          ... 対話シェル
# duck -c "SELECT 1;"           ... ワンライナー実行
```

## Python から DB に接続する

環境変数はコンテナ起動時に自動で設定されます。

```python
import os
import mysql.connector
import psycopg2

# MySQL
conn = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", 3306)),
    database=os.getenv("MYSQL_DB", "dataflow"),
    user=os.getenv("MYSQL_USER", "dataflow_user"),
    password=os.getenv("MYSQL_PASSWORD", "dataflow_pass"),
)

# PostgreSQL
conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", 5432)),
    dbname=os.getenv("POSTGRES_DB", "dataflow"),
    user=os.getenv("POSTGRES_USER", "dataflow_user"),
    password=os.getenv("POSTGRES_PASSWORD", "dataflow_pass"),
)
```

## Python パッケージの追加

1. `requirements.txt` にパッケージを追記する

```txt
pandas==2.2.0
```

2. イメージを再ビルドして再起動する

```bash
docker compose up -d --build
```

3. VS Code の Dev Containers で接続中の場合はコマンドパレットから以下を実行する

```
Dev Containers: Rebuild Container
```

## VS Code で開発する（Dev Containers）

### 前提

VS Code に [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) 拡張をインストールしておきます。

### 手順

1. Docker コンテナを起動する

```bash
docker compose up -d
```

2. VS Code でこのフォルダを開く

3. コマンドパレット（`Ctrl+Shift+P`）で以下を実行

```
Dev Containers: Reopen in Container
```

4. `dataflow_python` コンテナに接続され、Python インタープリタが自動で `/usr/local/bin/python` に設定される

### 接続先 Python

```
/usr/local/bin/python (Python 3.11, コンテナ内)
```

コンテナ内の環境変数（DB 接続情報）がそのまま使えるため、スクリプトをそのまま実行・デバッグできます。

## コンテナの状態確認

```bash
docker compose ps
docker compose logs mysql
docker compose logs postgres
docker compose logs python
```
