# README修正項目

## 概要
下記で挙げた項目をもとにREADME.mdを修正してください。

## airflowでのインストール項目

pip install apache-airflow-providers-standard
pip install apache-airflow-providers-cncf-kubernetes

## 実行方法

step1
minikubeを立ち上げる
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

別のターミナルを立ち上げる
incremental_loaderディレクトリ内で行う
step2
minikubeのダッシュボードを立ち上げる
```bash
OCKER_IMAGE_ARCHIVE_NAME=depd_visits_loader.tar

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

step3rflow実行
ai
```bash
cd airflow/

chmod +x start.sh

./start.sh
```