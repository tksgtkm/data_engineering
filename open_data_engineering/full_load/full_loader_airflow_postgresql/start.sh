#!/usr/bin/env bash
pkill -f "airflow api-server" 2>/dev/null
pkill -f "airflow scheduler" 2>/dev/null
pkill -f "airflow dag-processor" 2>/dev/null
sleep 2

export AIRFLOW__CORE__AUTH_MANAGER=airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager
export AIRFLOW__CORE__PLUGINS_FOLDER=./plugins
export AIRFLOW__CORE__DAGS_FOLDER=./dags
export AIRFLOW__CORE__LOAD_EXAMPLES=false

airflow db reset -y
airflow db migrate
airflow users create --username "dedp" --role "Admin" --password "dedp" --email "empty" --firstname "admin" --lastname "admin"

airflow connections delete fs_default 2>/dev/null
airflow connections add fs_default --conn-type fs --conn-extra '{"path": "/"}'
airflow connections delete docker_postgresql 2>/dev/null
airflow connections add --conn-host localhost --conn-type postgres --conn-login dedp_test --conn-password dedp_test --conn-port 5432 docker_postgresql

# airflow webserver & airflow scheduler
# 起動 (Airflow 3.x では dag-processor も必要)
airflow api-server &
airflow dag-processor &
airflow scheduler