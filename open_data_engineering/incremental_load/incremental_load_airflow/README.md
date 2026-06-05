# ローカル Kubernetes 環境構築 手順メモ

**minikube / kubectl / Helm / Spark Operator のセットアップ**

作成日: 2026年6月5日

---

## 概要

このドキュメントは、ローカルマシン上で Kubernetes 環境を構築し、Spark Operator をデプロイするまでに行った一連の作業をまとめたものです。バイナリのインストール、minikube クラスタの起動、Docker イメージのロード、Helm によるリポジトリ追加までを含みます。

---

## 1. バイナリのインストール

各ツールは `curl` でダウンロードし、`sudo install` で `/usr/local/bin` に配置する共通パターンを用います。

### 1.1 minikube

```bash
cd ~
curl -LO https://github.com/kubernetes/minikube/releases/latest/download/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64
minikube version
```

**ポイント:** `curl -LO` はコマンドを実行したカレントディレクトリにファイルを保存します。後続の `install` は同じディレクトリで実行する必要があります。ダウンロードした場所とインストールを実行する場所が異なると「stat できません」エラーになります。

### 1.2 kubectl

```bash
cd ~
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl && rm kubectl
kubectl version --client
```

`$(curl -L -s https://dl.k8s.io/release/stable.txt)` の部分が最新の安定バージョン番号を自動取得します。

### 1.3 Helm

Helm は公式インストールスクリプトを使うのが簡単です。

```bash
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

### 1.4 Airflow プロバイダ

Airflow から標準オペレータおよび Kubernetes 連携を利用するため、以下のプロバイダをインストールします。

```bash
pip install apache-airflow-providers-standard
pip install apache-airflow-providers-cncf-kubernetes
```

---

## 2. minikube クラスタの操作

### 2.1 クラスタの起動

```bash
minikube start
```

### 2.2 ホストディレクトリのマウント

ホスト側のディレクトリを VM 内にマウントします。UID/GID は Spark イメージの実行ユーザ（185）に合わせています。

```bash
minikube mount "/tmp/dedp/incremental_loader:/data_for_demo" --uid 185 --gid 185
```

**重要:** このコマンドはフォアグラウンドで動き続けるプロセスです。「マウントにアクセスするにはこのプロセスが存続しなければなりません」と表示されたまま停止して見えますが、これは正常です。

- マウントを維持する間、このターミナルは閉じない（Ctrl+C すると解除される）。
- 続きの作業は別のターミナルを開いて行う。

### 2.3 Docker イメージのロード

ローカルでビルドしたイメージを tar に保存し、minikube 内にロードします。

```bash
# イメージをアーカイブに保存
docker save dedp_visits_loader:latest > $DOCKER_IMAGE_ARCHIVE_NAME

# minikube にロード
minikube image load $DOCKER_IMAGE_ARCHIVE_NAME
```

**注意:** 変数名は全コマンドで一致させること。`docker save` で使った変数と `image load` で使う変数が異なると、空の引数が渡され `MK_USAGE` エラーになります。

---

## 3. 環境変数を別ターミナルへ引き継ぐ

別のターミナルを開くと `export` した変数は引き継がれません。永続化するには `~/.bashrc` に追記します。

```bash
echo 'export DOCKER_IMAGE_ARCHIVE_NAME=/tmp/dedp/incremental_loader/dedp_visits_loader.tar' >> ~/.bashrc
source ~/.bashrc
```

`~/.bashrc` は新しいターミナルを開くたびに読み込まれます（`~/.bash_profile` はログイン時のみ）。

---

## 4. Spark Operator の Helm リポジトリ追加

Spark Operator のリポジトリは Kubeflow 配下へ移行しています。旧 URL（googlecloudplatform.github.io）は 404 になるため、新しい URL を使用します。

```bash
helm repo add spark-operator https://kubeflow.github.io/spark-operator
helm repo update
helm search repo spark-operator
```

---

## 5. 実行方法

セットアップ完了後、以下の手順でデモを実行します。複数のターミナルを使い分けます。

### step1: minikube の起動とデータ準備

データ生成コンテナを起動し、Spark イメージをビルドして minikube を立ち上げ、ホストディレクトリをマウントします。

```bash
cd dataset/

mkdir -p /tmp/dedp/incremental_loader/

docker compose down --volume; docker compose up

cd ../incremental-spask-job/

DOCKER_IMAGE_ARCHIVE_NAME=depd_visits_loader.tar

docker build -t dedp_visits_loader .

docker save dedp_visits_loader:latest > $DOCKER_IMAGE_ARCHIVE_NAME

minikube start

minikube mount "/tmp/dedp/incremental_loader:/data_for_demo" --uid 185 --gid 185
```

> `minikube mount` はフォアグラウンドで動き続けるため、このターミナルは閉じずに次の step は別ターミナルで行います。

### step2: イメージのロードと Spark Operator のデプロイ

別のターミナルを開き、`incremental-spask-job/` ディレクトリ内で実行します。イメージを minikube にロードし、namespace・ServiceAccount を作成して Spark Operator をインストールした後、ダッシュボードを起動します。

```bash
DOCKER_IMAGE_ARCHIVE_NAME=depd_visits_loader.tar

docker build -t dedp_visits_loader .

docker save dedp_visits_loader:latest > $DOCKER_IMAGE_ARCHIVE_NAME

minikube image load $DOCKER_IMAGE_ARCHIVE_NAME

minikube image ls

K8S_NAMESPACE=dedp-demo
kubectl create namespace $K8S_NAMESPACE
kubectl config set-context --current --namespace=$K8S_NAMESPACE
kubectl create serviceaccount spark-editor
kubectl create rolebinding spark-editor-role --clusterrole=edit --serviceaccount=$K8S_NAMESPACE:spark-editor

helm repo add spark-operator https://kubeflow.github.io/spark-operator
helm repo update
helm search repo spark-operator
helm install dedp-spark-operator spark-operator/spark-operator --namespace $K8S_NAMESPACE --create-namespace --set webhook.enable=true --set webhook.port=443

minikube dashboard
```

### step3: Airflow の実行

```bash
cd airflow/

chmod +x start.sh

./start.sh
```

---

## 6. 補足: PySpark / Spark のバージョン確認

PySpark のバージョンは Spark のバージョンと一致します。

```bash
# Python から
python3 -c "import pyspark; print(pyspark.__version__)"

# spark-submit から
spark-submit --version
```

Spark セッションからは次のように確認できます。

```python
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()
print(spark.version)
```

---

## 7. トラブルシューティング早見表

| 症状 / エラー | 原因と対処 |
|---|---|
| `install: stat できません` | ダウンロードしたディレクトリと install 実行ディレクトリが異なる。`cd` でファイルのある場所へ移動してから実行する。 |
| minikube mount が止まって見える | 正常動作。フォアグラウンドで存続するプロセス。別ターミナルで作業を続ける。 |
| `MK_USAGE` エラー（image load） | 変数が空、または別ターミナルへ未引き継ぎ。`echo` で中身を確認し、変数名の不一致がないか確認する。 |
| `helm repo add` で 404 Not Found | リポジトリ URL が古い。`kubeflow.github.io/spark-operator` を使用する。 |