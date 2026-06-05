#!/usr/bin/env bash
airflow db reset -y
airflow db migrate

export AIRFLOW__CORE__DAGS_FOLDER=./dags
export AIRFLOW__CORE__LOAD_EXAMPLES=false
export AIRFLOW__CORE__AUTH_MANAGER=airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager

airflow fab-db migrate

airflow users create \
  --username "dedp" --role "Admin" --password "dedp" \
  --email "admin@example.com" --firstname "admin" --lastname "admin"

airflow api-server &
airflow dag-processor &
airflow scheduler